"""Ingestão da API oficial da Câmara dos Deputados.

API: https://dadosabertos.camara.leg.br/api/v2 — REST, JSON, sem auth.

Sincroniza:
- 513 deputados em exercício (com foto, partido, UF, gabinete)
- Cria/atualiza Pessoa, FiliacaoPartidaria, Mandato
- Detecta mudança de partido → cria Evento na timeline
- Marca pessoa.ids_externos.camara para idempotência
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Estado,
    EventoTimeline,
    FiliacaoPartidaria,
    Mandato,
    Partido,
    Pessoa,
)

logger = logging.getLogger("camara")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

API_BASE = "https://dadosabertos.camara.leg.br/api/v2"
USER_AGENT = "BussolaEleitoralBot/0.1 (+localhost; pt-BR)"
TIMEOUT = 30


def _http_client() -> httpx.Client:
    return httpx.Client(
        base_url=API_BASE,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )


def _get_ids_externos(p: Pessoa) -> dict:
    if not p.ids_externos_json:
        return {}
    try:
        return json.loads(p.ids_externos_json) or {}
    except json.JSONDecodeError:
        return {}


def _set_ids_externos(p: Pessoa, ids: dict):
    p.ids_externos_json = json.dumps(ids, ensure_ascii=False)


def listar_deputados(client: httpx.Client) -> list[dict]:
    """Lista todos os deputados em exercício (paginado)."""
    deputados = []
    pagina = 1
    while True:
        r = client.get("/deputados", params={"itens": 100, "pagina": pagina, "ordem": "ASC", "ordenarPor": "nome"})
        r.raise_for_status()
        data = r.json()
        items = data.get("dados", [])
        if not items:
            break
        deputados.extend(items)
        if len(items) < 100:
            break
        pagina += 1
        time.sleep(0.2)  # rate limit
    return deputados


def obter_detalhe_deputado(client: httpx.Client, dep_id: int) -> dict | None:
    """Detalhe completo: biografia, foto, partido atual, gabinete."""
    try:
        r = client.get(f"/deputados/{dep_id}")
        r.raise_for_status()
        return r.json().get("dados")
    except httpx.HTTPError as e:
        logger.warning(f"Erro ao buscar detalhe {dep_id}: {e}")
        return None


def sincronizar_deputado(
    db: Session,
    dep_resumo: dict,
    detalhe: dict | None,
    estados_por_sigla: dict[str, str],
    partidos_por_sigla: dict[str, str],
) -> dict:
    """Cria/atualiza Pessoa, FiliacaoPartidaria, Mandato. Detecta mudança de partido."""
    stats = {"criada": False, "atualizada": False, "mudou_partido": False, "mudou_partido_de": None, "mudou_partido_para": None}

    dep_id = dep_resumo["id"]
    nome_resumo = dep_resumo.get("nome") or ""
    sigla_partido = (dep_resumo.get("siglaPartido") or "").upper().strip()
    sigla_uf = (dep_resumo.get("siglaUf") or "").upper().strip()
    foto_url = dep_resumo.get("urlFoto")
    email = dep_resumo.get("email")

    # Dados completos (se disponíveis)
    nome_civil = nome_resumo
    nome_eleitoral = dep_resumo.get("nome")
    data_nasc = None
    biografia = None
    if detalhe:
        ult_status = detalhe.get("ultimoStatus") or {}
        nome_civil = detalhe.get("nomeCivil") or nome_resumo
        nome_eleitoral = ult_status.get("nomeEleitoral") or nome_resumo
        biografia = (
            f"Deputado{'a' if (detalhe.get('sexo') == 'F') else ''} federal por "
            f"{sigla_uf} ({sigla_partido}). "
            + (f"Eleito em {ult_status.get('idLegislatura', 'legislatura atual')}. " if ult_status else "")
        )
        nasc_str = detalhe.get("dataNascimento")
        if nasc_str:
            try:
                data_nasc = date.fromisoformat(nasc_str)
            except ValueError:
                pass

    # Localiza ou cria pessoa por id_camara em ids_externos
    pessoa = (
        db.query(Pessoa)
        .filter(
            Pessoa.deleted_at.is_(None),
            Pessoa.ids_externos_json.like(f'%"camara": {dep_id}%')
            | Pessoa.ids_externos_json.like(f'%"camara":{dep_id}%'),
        )
        .first()
    )

    # Fallback: por nome_completo + UF
    if not pessoa:
        pessoa = (
            db.query(Pessoa)
            .filter(
                Pessoa.nome_completo == nome_civil,
                Pessoa.deleted_at.is_(None),
            )
            .first()
        )

    if not pessoa:
        pessoa = Pessoa(
            nome_completo=nome_civil,
            nome_urna=nome_eleitoral,
            foto_url=foto_url,
            biografia=biografia,
            nascimento=data_nasc,
            email_publico=email,
            estado_natal_id=estados_por_sigla.get(sigla_uf),
        )
        ids_ext = {"camara": dep_id}
        _set_ids_externos(pessoa, ids_ext)
        db.add(pessoa)
        db.flush()
        stats["criada"] = True
    else:
        # Atualiza
        if nome_eleitoral and pessoa.nome_urna != nome_eleitoral:
            pessoa.nome_urna = nome_eleitoral
        if foto_url and pessoa.foto_url != foto_url:
            pessoa.foto_url = foto_url
        if email and pessoa.email_publico != email:
            pessoa.email_publico = email
        if data_nasc and not pessoa.nascimento:
            pessoa.nascimento = data_nasc
        if biografia and not pessoa.biografia:
            pessoa.biografia = biografia
        ids_ext = _get_ids_externos(pessoa)
        if ids_ext.get("camara") != dep_id:
            ids_ext["camara"] = dep_id
            _set_ids_externos(pessoa, ids_ext)
        stats["atualizada"] = True

    # Filiação partidária
    partido_id = partidos_por_sigla.get(sigla_partido)
    if partido_id:
        # Filiação ativa atual?
        filiacao_ativa = (
            db.query(FiliacaoPartidaria)
            .filter(
                FiliacaoPartidaria.pessoa_id == pessoa.id,
                FiliacaoPartidaria.fim.is_(None),
            )
            .first()
        )

        if not filiacao_ativa:
            # Sem filiação ativa → cria
            db.add(
                FiliacaoPartidaria(
                    pessoa_id=pessoa.id,
                    partido_id=partido_id,
                    inicio=date.today(),
                )
            )
        elif filiacao_ativa.partido_id != partido_id:
            # MUDOU DE PARTIDO!
            partido_anterior = db.query(Partido).filter(Partido.id == filiacao_ativa.partido_id).first()
            partido_novo = db.query(Partido).filter(Partido.id == partido_id).first()
            sigla_anterior = partido_anterior.sigla if partido_anterior else "?"
            sigla_nova = partido_novo.sigla if partido_novo else sigla_partido

            # Fecha filiação anterior
            filiacao_ativa.fim = date.today()
            filiacao_ativa.tipo_saida = "transferencia"

            # Cria nova
            db.add(
                FiliacaoPartidaria(
                    pessoa_id=pessoa.id,
                    partido_id=partido_id,
                    inicio=date.today(),
                )
            )

            # Cria evento na timeline
            db.add(
                EventoTimeline(
                    pessoa_id=pessoa.id,
                    partido_id=partido_id,
                    estado_id=estados_por_sigla.get(sigla_uf),
                    tipo="filiacao",
                    titulo=f"{nome_civil} mudou de {sigla_anterior} para {sigla_nova}",
                    descricao=f"Detectado pela ingestão da API Câmara em {datetime.utcnow().isoformat()}",
                    data_evento=datetime.utcnow(),
                    fonte_descricao="API Câmara dos Deputados",
                    automatico=True,
                    origem_automatica="api_camara",
                    relevancia=4,
                )
            )
            stats["mudou_partido"] = True
            stats["mudou_partido_de"] = sigla_anterior
            stats["mudou_partido_para"] = sigla_nova
            logger.info(f"  [partido] {nome_civil}: {sigla_anterior} → {sigla_nova}")

    # Mandato atual
    mandato_atual = (
        db.query(Mandato)
        .filter(
            Mandato.pessoa_id == pessoa.id,
            Mandato.cargo == "deputado_federal",
            Mandato.fim >= date.today(),
        )
        .first()
    )
    if not mandato_atual and partido_id and sigla_uf:
        # Cria mandato 2023-2027
        db.add(
            Mandato(
                pessoa_id=pessoa.id,
                cargo="deputado_federal",
                estado_id=estados_por_sigla.get(sigla_uf),
                partido_id_no_mandato=partido_id,
                inicio=date(2023, 2, 1),
                fim=date(2027, 1, 31),
                eh_titular=True,
            )
        )

    return stats


def sincronizar_camara(db: Session | None = None, com_detalhes: bool = True) -> dict:
    """Sincroniza todos os deputados em exercício.

    Se com_detalhes=False: só usa lista resumida (mais rápido, ~1s).
    Se com_detalhes=True: busca cada deputado individualmente (513 reqs, ~3min).
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    inicio = time.time()
    sumario = {
        "total_listados": 0,
        "novas": 0,
        "atualizadas": 0,
        "mudancas_partido": 0,
        "erros": 0,
        "duracao_segundos": 0,
        "mudancas_detalhes": [],
    }

    try:
        estados_por_sigla = {e.sigla: e.id for e in db.query(Estado).all()}
        partidos_por_sigla = {p.sigla.upper(): p.id for p in db.query(Partido).all()}

        with _http_client() as client:
            logger.info("Listando deputados em exercicio...")
            deputados = listar_deputados(client)
            sumario["total_listados"] = len(deputados)
            logger.info(f"  {len(deputados)} deputados encontrados")

            for i, dep in enumerate(deputados):
                if i % 50 == 0:
                    logger.info(f"  Processando {i + 1}/{len(deputados)}...")

                detalhe = None
                if com_detalhes:
                    detalhe = obter_detalhe_deputado(client, dep["id"])
                    time.sleep(0.05)  # 20 req/s max

                try:
                    stats = sincronizar_deputado(db, dep, detalhe, estados_por_sigla, partidos_por_sigla)
                    if stats["criada"]:
                        sumario["novas"] += 1
                    elif stats["atualizada"]:
                        sumario["atualizadas"] += 1
                    if stats["mudou_partido"]:
                        sumario["mudancas_partido"] += 1
                        sumario["mudancas_detalhes"].append({
                            "nome": dep.get("nome"),
                            "de": stats["mudou_partido_de"],
                            "para": stats["mudou_partido_para"],
                        })
                except Exception as e:
                    logger.warning(f"Erro em {dep.get('nome')}: {e}")
                    sumario["erros"] += 1

                # Commit em batches
                if i % 50 == 49:
                    db.commit()

            db.commit()

        sumario["duracao_segundos"] = round(time.time() - inicio, 1)
        logger.info(
            f"Concluido em {sumario['duracao_segundos']}s — {sumario['novas']} novos, "
            f"{sumario['atualizadas']} atualizados, {sumario['mudancas_partido']} mudancas de partido, "
            f"{sumario['erros']} erros"
        )
        return sumario

    finally:
        if own_session:
            db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ingestão API Câmara dos Deputados")
    parser.add_argument("--rapido", action="store_true", help="Sem buscar detalhe individual (só lista resumida)")
    args = parser.parse_args()

    s = sincronizar_camara(com_detalhes=not args.rapido)
    print("\n=== SUMARIO ===")
    for k, v in s.items():
        if k == "mudancas_detalhes":
            if v:
                print(f"{k}:")
                for m in v[:10]:
                    print(f"  {m['nome']}: {m['de']} -> {m['para']}")
        else:
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
