"""Ingestão de votações da Câmara dos Deputados.

API endpoints:
- /votacoes — lista paginada (filtros por data)
- /votacoes/{id}/votos — voto individual de cada deputado
- /votacoes/{id}/orientacoes — orientação dos partidos

Cria/atualiza:
- VotacaoCongresso (uma por votação)
- VotoParlamentar (513 por votação)
- OrientacaoPartido (1 por partido por votação)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    OrientacaoPartido,
    Partido,
    Pessoa,
    VotacaoCongresso,
    VotoParlamentar,
)

logger = logging.getLogger("camara_votacoes")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

API_BASE = "https://dadosabertos.camara.leg.br/api/v2"
USER_AGENT = "BussolaEleitoralBot/0.1 (+localhost; pt-BR)"
TIMEOUT = 30


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=API_BASE,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


VOTO_MAP = {
    "Sim": "sim",
    "Não": "nao",
    "Abstenção": "abstencao",
    "Obstrução": "obstrucao",
    "Art. 17": "obstrucao",
}


def listar_votacoes(client: httpx.Client, dias_atras: int = 180) -> list[dict]:
    """Lista votações dos últimos N dias. Resiliente a falhas."""
    desde = (date.today() - timedelta(days=dias_atras)).isoformat()
    votacoes = []
    pagina = 1
    falhas_consecutivas = 0
    while True:
        try:
            r = client.get(
                "/votacoes",
                params={
                    "dataInicio": desde,
                    "ordem": "DESC",
                    "ordenarPor": "dataHoraRegistro",
                    "itens": 100,
                    "pagina": pagina,
                },
            )
            r.raise_for_status()
            items = r.json().get("dados", [])
            falhas_consecutivas = 0
        except httpx.HTTPError as e:
            falhas_consecutivas += 1
            logger.warning(f"  Pagina {pagina}: erro {e}. Retry {falhas_consecutivas}/3")
            if falhas_consecutivas >= 3:
                logger.warning(f"  Parando após 3 falhas consecutivas. Coletadas {len(votacoes)} votacoes.")
                break
            time.sleep(2 * falhas_consecutivas)
            continue

        if not items:
            break
        votacoes.extend(items)
        if len(items) < 100:
            break
        pagina += 1
        time.sleep(0.3)
        if pagina > 30:
            break
    return votacoes


def obter_votos(client: httpx.Client, votacao_id: str) -> list[dict]:
    """Voto individual de cada deputado."""
    try:
        r = client.get(f"/votacoes/{votacao_id}/votos", params={"itens": 600})
        r.raise_for_status()
        return r.json().get("dados", [])
    except httpx.HTTPError as e:
        logger.warning(f"Erro votos {votacao_id}: {e}")
        return []


def obter_orientacoes(client: httpx.Client, votacao_id: str) -> list[dict]:
    try:
        r = client.get(f"/votacoes/{votacao_id}/orientacoes")
        r.raise_for_status()
        return r.json().get("dados", [])
    except httpx.HTTPError:
        return []


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def _parse_proposicao(votacao_data: dict) -> tuple[str | None, int | None, int | None]:
    """Tenta extrair tipo/numero/ano da proposição associada."""
    obj_votado = votacao_data.get("descricao") or ""
    siglaUltimoStatus = votacao_data.get("siglaOrgao") or ""
    # Heurística: PEC 1234/2024
    import re
    m = re.search(r"\b([A-Z]{2,4})\s*(\d+)\s*[/\.](\d{4})\b", obj_votado)
    if m:
        return m.group(1), int(m.group(2)), int(m.group(3))
    return None, None, None


def sincronizar_votacao(
    db: Session,
    client: httpx.Client,
    votacao_resumo: dict,
    pessoas_por_camara_id: dict[int, str],
    partidos_por_sigla: dict[str, str],
) -> dict:
    """Cria VotacaoCongresso + votos + orientações para uma votação."""
    stats = {"criada": False, "ja_existia": False, "votos": 0, "orientacoes": 0}

    vot_id = votacao_resumo["id"]
    ids_externos = json.dumps({"camara": vot_id}, ensure_ascii=False)

    # Idempotência por id_camara
    existing = (
        db.query(VotacaoCongresso)
        .filter(VotacaoCongresso.ids_externos_json.like(f'%"camara": "{vot_id}"%'))
        .first()
    )
    if existing:
        stats["ja_existia"] = True
        return stats

    data = _parse_date(votacao_resumo.get("dataHoraRegistro") or votacao_resumo.get("data"))
    if not data:
        return stats

    descricao = votacao_resumo.get("descricao") or ""
    aprovacao = votacao_resumo.get("aprovacao")  # 1=aprovada, 0=rejeitada
    sigla_orgao = votacao_resumo.get("siglaOrgao") or ""
    tipo, numero, ano = _parse_proposicao(votacao_resumo)

    resultado = "aprovado" if aprovacao == 1 else "rejeitado" if aprovacao == 0 else "outros"

    votacao = VotacaoCongresso(
        casa="camara",
        data=data,
        ementa=descricao[:1000] if descricao else "Votação sem ementa",
        descricao_completa=descricao,
        tipo_proposicao=tipo,
        numero=numero,
        ano=ano,
        posicionamento_governo="desconhecido",
        resultado=resultado,
        ids_externos_json=ids_externos,
    )
    db.add(votacao)
    db.flush()
    stats["criada"] = True

    # Votos individuais
    votos = obter_votos(client, vot_id)
    votos_aceitos = 0
    for v in votos:
        dep = v.get("deputado_") or v.get("deputado", {})
        dep_id = dep.get("id") if isinstance(dep, dict) else None
        if not dep_id:
            continue
        pessoa_id = pessoas_por_camara_id.get(dep_id)
        if not pessoa_id:
            continue
        voto_str = v.get("tipoVoto") or v.get("voto") or ""
        voto = VOTO_MAP.get(voto_str.strip(), "ausente")
        sigla_partido = (dep.get("siglaPartido") or "").upper().strip() if isinstance(dep, dict) else ""
        partido_id = partidos_por_sigla.get(sigla_partido)
        sigla_uf = dep.get("siglaUf") if isinstance(dep, dict) else None

        db.add(
            VotoParlamentar(
                votacao_id=votacao.id,
                pessoa_id=pessoa_id,
                partido_id_no_voto=partido_id,
                voto=voto,
            )
        )
        votos_aceitos += 1
    stats["votos"] = votos_aceitos

    # Contadores rápidos
    from sqlalchemy import func
    contagem = dict(
        db.query(VotoParlamentar.voto, func.count(VotoParlamentar.id))
        .filter(VotoParlamentar.votacao_id == votacao.id)
        .group_by(VotoParlamentar.voto)
        .all()
    )
    votacao.votos_sim = contagem.get("sim", 0)
    votacao.votos_nao = contagem.get("nao", 0)
    votacao.votos_abstencao = contagem.get("abstencao", 0)

    # Orientações partidárias
    orientacoes = obter_orientacoes(client, vot_id)
    for o in orientacoes:
        sigla = (o.get("siglaPartidoBloco") or o.get("siglaBancada") or "").upper().strip()
        partido_id = partidos_por_sigla.get(sigla)
        if not partido_id:
            continue
        ori_str = o.get("orientacaoVoto") or ""
        ori_normal = {
            "Sim": "a_favor",
            "Não": "contra",
            "Liberado": "liberada",
            "Liberada": "liberada",
            "Obstrução": "contra",
        }.get(ori_str.strip(), "liberada")
        db.add(
            OrientacaoPartido(
                votacao_id=votacao.id,
                partido_id=partido_id,
                orientacao=ori_normal,
            )
        )
        stats["orientacoes"] += 1

    return stats


def sincronizar_votacoes(
    db: Session | None = None,
    dias_atras: int = 180,
    com_votos: bool = True,
    limit: int | None = None,
) -> dict:
    """Sincroniza votações da Câmara dos últimos N dias."""
    own_session = db is None
    if own_session:
        db = SessionLocal()

    inicio = time.time()
    sumario = {
        "total_listadas": 0,
        "criadas": 0,
        "ja_existiam": 0,
        "votos_total": 0,
        "orientacoes_total": 0,
        "erros": 0,
        "duracao_segundos": 0,
    }

    try:
        # Mapeia pessoas por id_camara
        pessoas_por_camara_id = {}
        for p in db.query(Pessoa).filter(Pessoa.deleted_at.is_(None), Pessoa.ids_externos_json.like('%camara%')).all():
            try:
                ids = json.loads(p.ids_externos_json or "{}")
                cid = ids.get("camara")
                if cid:
                    pessoas_por_camara_id[int(cid)] = p.id
            except (json.JSONDecodeError, ValueError):
                continue

        partidos_por_sigla = {p.sigla.upper(): p.id for p in db.query(Partido).all()}

        with _client() as client:
            logger.info(f"Listando votacoes dos ultimos {dias_atras} dias...")
            votacoes = listar_votacoes(client, dias_atras=dias_atras)
            sumario["total_listadas"] = len(votacoes)
            logger.info(f"  {len(votacoes)} votacoes encontradas")

            if limit:
                votacoes = votacoes[:limit]

            for i, vot in enumerate(votacoes):
                if i % 20 == 0:
                    logger.info(f"  Processando {i + 1}/{len(votacoes)}...")
                try:
                    stats = sincronizar_votacao(db, client, vot, pessoas_por_camara_id, partidos_por_sigla)
                    if stats["criada"]:
                        sumario["criadas"] += 1
                        sumario["votos_total"] += stats["votos"]
                        sumario["orientacoes_total"] += stats["orientacoes"]
                    elif stats["ja_existia"]:
                        sumario["ja_existiam"] += 1
                except Exception as e:
                    logger.warning(f"Erro {vot.get('id')}: {e}")
                    sumario["erros"] += 1

                if i % 10 == 9:
                    db.commit()
                if com_votos:
                    time.sleep(0.05)

            db.commit()

        sumario["duracao_segundos"] = round(time.time() - inicio, 1)
        logger.info(
            f"Concluido em {sumario['duracao_segundos']}s — "
            f"{sumario['criadas']} novas, {sumario['ja_existiam']} ja existiam, "
            f"{sumario['votos_total']} votos individuais"
        )
        return sumario

    finally:
        if own_session:
            db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dias", type=int, default=90)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    s = sincronizar_votacoes(dias_atras=args.dias, limit=args.limit)
    print("\n=== SUMARIO ===")
    for k, v in s.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
