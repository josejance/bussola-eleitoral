"""Cálculo de fidelidade ao governo.

Estratégia híbrida (votação individual quando disponível, orientação partidária como proxy):

Para cada parlamentar, considera as votações classificadas (posicionamento_governo a_favor/contra)
nos últimos N meses. Para cada votação:
- Se há voto individual: compara com posicionamento_governo
- Senão: usa orientação do partido como proxy

Retorna % alinhamento.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import (
    OrientacaoPartido,
    Partido,
    Pessoa,
    VotacaoCongresso,
    VotoParlamentar,
)


def calcular_fidelidade_parlamentares(
    db: Session,
    meses: int = 12,
    incluir_proxy_partido: bool = True,
) -> list[dict]:
    """Para cada parlamentar com mandato ativo, calcula fidelidade ao governo.

    Considera votações onde:
    - posicionamento_governo IN ('a_favor', 'contra')

    Retorna lista [{pessoa_id, nome, partido_sigla, total_votacoes, alinhados, fidelidade_pct}]
    """
    desde = date.today() - timedelta(days=meses * 30)

    # Pega votações relevantes
    votacoes_rel = (
        db.query(VotacaoCongresso.id, VotacaoCongresso.posicionamento_governo)
        .filter(VotacaoCongresso.data >= desde)
        .filter(VotacaoCongresso.posicionamento_governo.in_(["a_favor", "contra"]))
        .all()
    )
    votacao_ids = [v[0] for v in votacoes_rel]
    posicao_por_votacao = {v[0]: v[1] for v in votacoes_rel}

    if not votacao_ids:
        return []

    # 1) Votos individuais
    votos = (
        db.query(VotoParlamentar.pessoa_id, VotoParlamentar.votacao_id, VotoParlamentar.voto)
        .filter(VotoParlamentar.votacao_id.in_(votacao_ids))
        .filter(VotoParlamentar.voto.in_(["sim", "nao", "abstencao"]))
        .all()
    )
    votos_por_pessoa: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for pessoa_id, vot_id, voto in votos:
        votos_por_pessoa[pessoa_id].append((vot_id, voto))

    # 2) Orientações partidárias (proxy para quem não votou individualmente)
    orientacoes_por_partido_votacao: dict[tuple[str, str], str] = {}
    if incluir_proxy_partido:
        rows = (
            db.query(OrientacaoPartido.partido_id, OrientacaoPartido.votacao_id, OrientacaoPartido.orientacao)
            .filter(OrientacaoPartido.votacao_id.in_(votacao_ids))
            .all()
        )
        for partido_id, vot_id, ori in rows:
            orientacoes_por_partido_votacao[(partido_id, vot_id)] = ori

    # 3) Para cada pessoa, calcula alinhamento
    # Pega TODAS as pessoas com filiação ativa (proxy = bancada)
    from app.models import FiliacaoPartidaria, Mandato

    parlamentares = (
        db.query(Pessoa.id, Pessoa.nome_completo, Pessoa.nome_urna, FiliacaoPartidaria.partido_id, Partido.sigla, Partido.cor_hex)
        .join(FiliacaoPartidaria, FiliacaoPartidaria.pessoa_id == Pessoa.id)
        .join(Partido, Partido.id == FiliacaoPartidaria.partido_id)
        .join(Mandato, Mandato.pessoa_id == Pessoa.id)
        .filter(FiliacaoPartidaria.fim.is_(None))
        .filter(Mandato.cargo.in_(["deputado_federal", "senador"]))
        .filter(Mandato.fim >= date.today())
        .filter(Pessoa.deleted_at.is_(None))
        .distinct()
        .all()
    )

    resultados = []
    for pid, nome_c, nome_u, partido_id, partido_sigla, partido_cor in parlamentares:
        votos_pessoa = {v_id: v for v_id, v in votos_por_pessoa.get(pid, [])}

        total = 0
        alinhados = 0
        contra = 0
        ausente_proxy = 0
        proxy_used = 0

        for vot_id, posicao_gov in posicao_por_votacao.items():
            voto_individual = votos_pessoa.get(vot_id)

            if voto_individual is None:
                # Tenta proxy partido
                if not incluir_proxy_partido:
                    continue
                ori_partido = orientacoes_por_partido_votacao.get((partido_id, vot_id))
                if not ori_partido or ori_partido == "liberada":
                    continue
                # Mapeia orientação → voto presumido
                voto_presumido = "sim" if ori_partido == "a_favor" else "nao"
                voto_individual = voto_presumido
                proxy_used += 1

            if voto_individual == "abstencao":
                ausente_proxy += 1
                continue

            total += 1
            if (posicao_gov == "a_favor" and voto_individual == "sim") or (
                posicao_gov == "contra" and voto_individual == "nao"
            ):
                alinhados += 1
            else:
                contra += 1

        if total == 0:
            continue

        resultados.append({
            "pessoa_id": pid,
            "nome": nome_u or nome_c,
            "partido_sigla": partido_sigla,
            "partido_cor": partido_cor,
            "total_votacoes": total,
            "alinhados": alinhados,
            "contra": contra,
            "fidelidade_pct": round(100 * alinhados / total, 1),
            "votos_proxy_partido": proxy_used,
        })

    return resultados


def estatisticas_base_aliada(db: Session, meses: int = 12) -> dict:
    """Sumário do estado da base do governo Lula no Congresso."""
    fids = calcular_fidelidade_parlamentares(db, meses=meses)
    if not fids:
        return {
            "total_parlamentares_avaliados": 0,
            "votacoes_consideradas": 0,
            "fidelidade_media": 0,
            "alta_fidelidade": 0,
            "media_fidelidade": 0,
            "baixa_fidelidade": 0,
            "rebeldes_da_base": 0,
            "infieis": 0,
        }

    desde = date.today() - timedelta(days=meses * 30)
    n_votacoes = (
        db.query(VotacaoCongresso)
        .filter(VotacaoCongresso.data >= desde)
        .filter(VotacaoCongresso.posicionamento_governo.in_(["a_favor", "contra"]))
        .count()
    )

    BASE_LULA_PARTIDOS = {"PT", "PCdoB", "PV", "PSB", "PSOL", "REDE", "PDT", "MDB", "UNIAO", "SOLIDARIEDADE", "AVANTE", "PSD"}

    # Faixas
    alta = [f for f in fids if f["fidelidade_pct"] >= 70]
    media = [f for f in fids if 40 <= f["fidelidade_pct"] < 70]
    baixa = [f for f in fids if f["fidelidade_pct"] < 40]

    # Rebeldes da base: partido na base mas fidelidade < 50%
    rebeldes = [f for f in fids if f["partido_sigla"] in BASE_LULA_PARTIDOS and f["fidelidade_pct"] < 50]
    # Infiéis: alta fidelidade mas partido fora da base
    infieis = [f for f in fids if f["partido_sigla"] not in BASE_LULA_PARTIDOS and f["fidelidade_pct"] >= 70]

    media_geral = sum(f["fidelidade_pct"] for f in fids) / len(fids)

    return {
        "total_parlamentares_avaliados": len(fids),
        "votacoes_consideradas": n_votacoes,
        "fidelidade_media": round(media_geral, 1),
        "alta_fidelidade": len(alta),
        "media_fidelidade": len(media),
        "baixa_fidelidade": len(baixa),
        "rebeldes_da_base": len(rebeldes),
        "rebeldes_lista": [
            {"nome": f["nome"], "partido_sigla": f["partido_sigla"], "fidelidade": f["fidelidade_pct"]}
            for f in sorted(rebeldes, key=lambda x: x["fidelidade_pct"])[:10]
        ],
        "infieis_oposicao": len(infieis),
        "infieis_lista": [
            {"nome": f["nome"], "partido_sigla": f["partido_sigla"], "fidelidade": f["fidelidade_pct"]}
            for f in sorted(infieis, key=lambda x: -x["fidelidade_pct"])[:10]
        ],
    }
