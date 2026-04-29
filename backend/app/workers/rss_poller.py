"""Worker de polling de feeds RSS.

Funcionalidades:
- Lê feeds ativos cuja janela de polling expirou
- Deduplicação por hash da URL
- Filtro pré-IA por palavras-chave políticas
- Vinculação automática a estado(s)
- Registro em ingestoes_log

Pode ser executado como CLI: `python -m app.workers.rss_poller`
ou via endpoint admin POST /api/v1/admin/ingestao/rss/run
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Iterable

import feedparser
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    FonteRSS,
    Materia,
    MateriaEstado,
    MateriaMetadata,
    MateriaPartido,
    MateriaPessoa,
    Estado,
)
from app.services.text_filter import filtrar_materia

logger = logging.getLogger("rss_poller")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

USER_AGENT = "BussolaEleitoralBot/0.1 (+localhost; pt-BR)"
TIMEOUT_SECONDS = 20
MAX_ENTRIES_PER_FEED = 50


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()[:32]


def _parse_date(entry) -> datetime:
    """Extrai data de publicação de uma entrada RSS, com fallback para now."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime(*val[:6])
            except (TypeError, ValueError):
                continue
    return datetime.utcnow()


def _clean_html(text: str | None) -> str:
    if not text:
        return ""
    try:
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return text


def _extract_image(entry) -> str | None:
    # 1) media:content
    media = entry.get("media_content") or []
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    # 2) media:thumbnail
    thumbs = entry.get("media_thumbnail") or []
    if thumbs and isinstance(thumbs, list) and thumbs[0].get("url"):
        return thumbs[0]["url"]
    # 3) enclosures
    encl = entry.get("enclosures") or []
    if encl:
        for e in encl:
            if e.get("type", "").startswith("image"):
                return e.get("href") or e.get("url")
    # 4) regex em description
    summary = entry.get("summary") or ""
    if summary:
        soup = BeautifulSoup(summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    return None


def _ja_existe(db: Session, url_hash: str) -> bool:
    return (
        db.query(Materia.id)
        .filter(Materia.hash_url == url_hash)
        .first()
        is not None
    )


def poll_fonte(db: Session, fonte: FonteRSS, estados_por_sigla: dict[str, str]) -> dict:
    """Executa polling de uma fonte. Retorna estatísticas."""
    stats = {
        "fonte": fonte.nome,
        "novas": 0,
        "duplicadas": 0,
        "aproveitadas": 0,
        "descartadas": 0,
        "erro": None,
    }

    try:
        # feedparser usa urllib internamente; passamos User-Agent
        feed = feedparser.parse(
            fonte.url_feed,
            agent=USER_AGENT,
            request_headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"},
        )

        if feed.bozo and not feed.entries:
            raise RuntimeError(
                f"Feed inválido ou inacessível: {feed.bozo_exception}"
            )

        # Estados padrão da fonte (estaduais têm 1 estado em estados_cobertos_json)
        estados_da_fonte: list[str] = []
        if fonte.estados_cobertos_json:
            try:
                estados_da_fonte = json.loads(fonte.estados_cobertos_json) or []
            except json.JSONDecodeError:
                estados_da_fonte = []

        for entry in feed.entries[:MAX_ENTRIES_PER_FEED]:
            url = entry.get("link") or entry.get("id")
            if not url:
                continue

            url_hash = _hash_url(url)
            if _ja_existe(db, url_hash):
                stats["duplicadas"] += 1
                continue

            titulo = (entry.get("title") or "").strip()
            snippet_raw = entry.get("summary") or entry.get("description") or ""
            snippet = _clean_html(snippet_raw)
            data_pub = _parse_date(entry)
            autor = entry.get("author") or entry.get("dc_creator")
            imagem = _extract_image(entry)

            # Filtro inteligente (usa entidades cadastradas)
            filtro = filtrar_materia(titulo, snippet, db=db, fonte_eh_estadual=(fonte.abrangencia == "estadual"))

            materia = Materia(
                fonte_id=fonte.id,
                titulo=titulo[:500],
                snippet=snippet[:1500] if snippet else None,
                conteudo_completo=None,
                autor=autor[:150] if autor else None,
                data_publicacao=data_pub,
                data_captura=datetime.utcnow(),
                url=url[:1000],
                hash_url=url_hash,
                imagem_url=imagem[:1000] if imagem else None,
                processada_filtro=True,
                processada_ia=False,
                aproveitada=filtro.aproveitada,
                motivo_descarte=filtro.motivo_descarte,
            )
            db.add(materia)
            db.flush()

            stats["novas"] += 1

            if filtro.aproveitada:
                stats["aproveitadas"] += 1

                # Estados
                estados_a_vincular: set[str] = set()
                for sigla in filtro.estados_detectados:
                    eid = estados_por_sigla.get(sigla)
                    if eid:
                        estados_a_vincular.add(eid)
                if not estados_a_vincular and estados_da_fonte:
                    estados_a_vincular.update(estados_da_fonte)

                for eid in estados_a_vincular:
                    db.add(
                        MateriaEstado(
                            materia_id=materia.id,
                            estado_id=eid,
                            relevancia_para_estado=filtro.score_relevancia,
                        )
                    )

                # Pessoas (auto-link)
                for pessoa_id in filtro.pessoas_mencionadas_ids:
                    db.add(MateriaPessoa(materia_id=materia.id, pessoa_id=pessoa_id))

                # Partidos (auto-link)
                for partido_id in filtro.partidos_mencionados_ids:
                    db.add(MateriaPartido(materia_id=materia.id, partido_id=partido_id))

                # Metadata
                db.add(
                    MateriaMetadata(
                        materia_id=materia.id,
                        relevancia_estrategica=filtro.score_relevancia,
                        processado_em=datetime.utcnow(),
                        modelo_usado="filtro_entidades",
                        tokens_consumidos=0,
                        custo_centavos=0,
                    )
                )
            else:
                stats["descartadas"] += 1

        # Atualiza fonte
        agora = datetime.utcnow()
        fonte.ultimo_polling = agora
        fonte.ultimo_sucesso = agora
        fonte.total_materias_capturadas = (fonte.total_materias_capturadas or 0) + stats["novas"]
        fonte.total_materias_aproveitadas = (
            fonte.total_materias_aproveitadas or 0
        ) + stats["aproveitadas"]
        db.commit()

    except Exception as e:
        db.rollback()
        stats["erro"] = str(e)[:500]
        # registra polling mesmo com erro
        try:
            fonte.ultimo_polling = datetime.utcnow()
            db.commit()
        except Exception:
            db.rollback()
        logger.warning(f"Erro em {fonte.nome}: {e}")

    return stats


def _devido_polling(fonte: FonteRSS) -> bool:
    """True se a janela de polling expirou."""
    if not fonte.ultimo_polling:
        return True
    janela = timedelta(minutes=fonte.frequencia_polling_minutos or 30)
    return datetime.utcnow() - fonte.ultimo_polling >= janela


def run_polling(
    db: Session | None = None,
    apenas_devidas: bool = True,
    fontes_ids: list[str] | None = None,
) -> dict:
    """Executa polling em todas as fontes ativas (ou nas devidas/seletas).

    Retorna dict com sumário:
    {
        "fontes_processadas": int,
        "novas": int, "aproveitadas": int, "descartadas": int, "duplicadas": int,
        "erros": int,
        "duracao_segundos": float,
        "por_fonte": [stats...]
    }
    """
    inicio = time.time()
    own_session = db is None
    if own_session:
        db = SessionLocal()

    try:
        # carrega mapeamento sigla -> id
        estados = db.query(Estado).all()
        estados_por_sigla = {e.sigla: e.id for e in estados}

        # seleciona fontes
        q = db.query(FonteRSS).filter(FonteRSS.ativo == True)  # noqa: E712
        if fontes_ids:
            q = q.filter(FonteRSS.id.in_(fontes_ids))
        fontes = q.all()

        if apenas_devidas and not fontes_ids:
            fontes = [f for f in fontes if _devido_polling(f)]

        sumario = {
            "fontes_consideradas": len(fontes),
            "fontes_processadas": 0,
            "novas": 0,
            "aproveitadas": 0,
            "descartadas": 0,
            "duplicadas": 0,
            "erros": 0,
            "por_fonte": [],
        }

        logger.info(f"Iniciando polling em {len(fontes)} fontes")

        for fonte in fontes:
            stats = poll_fonte(db, fonte, estados_por_sigla)
            sumario["por_fonte"].append(stats)
            sumario["fontes_processadas"] += 1
            sumario["novas"] += stats["novas"]
            sumario["aproveitadas"] += stats["aproveitadas"]
            sumario["descartadas"] += stats["descartadas"]
            sumario["duplicadas"] += stats["duplicadas"]
            if stats["erro"]:
                sumario["erros"] += 1
            logger.info(
                f"[{fonte.nome}] novas={stats['novas']} aproveitadas={stats['aproveitadas']} "
                f"duplicadas={stats['duplicadas']} erro={stats['erro']}"
            )

        sumario["duracao_segundos"] = round(time.time() - inicio, 2)
        logger.info(
            f"Polling concluido em {sumario['duracao_segundos']}s — "
            f"{sumario['novas']} novas, {sumario['aproveitadas']} aproveitadas, "
            f"{sumario['erros']} erros"
        )
        return sumario

    finally:
        if own_session:
            db.close()


# ---------- CLI ----------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Polling de feeds RSS")
    parser.add_argument("--all", action="store_true", help="Ignora janela de polling, processa todas as fontes ativas")
    parser.add_argument("--fonte", action="append", help="ID(s) de fontes específicas")
    args = parser.parse_args()

    sumario = run_polling(apenas_devidas=not args.all, fontes_ids=args.fonte)

    print("\n=== Sumario ===")
    print(f"Fontes consideradas:  {sumario['fontes_consideradas']}")
    print(f"Fontes processadas:   {sumario['fontes_processadas']}")
    print(f"Materias novas:       {sumario['novas']}")
    print(f"  Aproveitadas:       {sumario['aproveitadas']}")
    print(f"  Descartadas:        {sumario['descartadas']}")
    print(f"Duplicadas (skip):    {sumario['duplicadas']}")
    print(f"Erros de fonte:       {sumario['erros']}")
    print(f"Duracao:              {sumario['duracao_segundos']}s")


if __name__ == "__main__":
    main()
