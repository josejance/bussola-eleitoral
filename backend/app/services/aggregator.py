"""Agregador estatístico de pesquisas eleitorais.

Implementa média ponderada com decaimento exponencial inspirado em FiveThirtyEight:

  estimativa = SUM(percentual_i × peso_i) / SUM(peso_i)
  peso_i = peso_recencia × peso_amostra × peso_confiabilidade × peso_metodologia

Onde:
- peso_recencia = exp(-dias / meia_vida)
- peso_amostra = sqrt(amostra / amostra_referencia), capado em 1.5
- peso_confiabilidade = (score_instituto / 5) ^ 1.5
- peso_metodologia = mapa pré-definido por método

Banda de incerteza: 95% baseado em desvio ponderado + erro amostral médio.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import (
    InstitutoPesquisa,
    IntencaoVoto,
    Pesquisa,
)

# ===== Configuração =====

PESOS_METODOLOGIA: dict[str, float] = {
    "presencial": 1.0,
    "mista": 0.95,
    "telefonica": 0.85,
    "online": 0.75,
    "painel": 0.70,
}

MEIA_VIDA_DIAS_DEFAULT = 14
AMOSTRA_REFERENCIA = 1500
CAP_PESO_AMOSTRA = 1.5
FLOOR_PESO_AMOSTRA = 0.5
ERRO_METODOLOGICO_PP = 1.5


# ===== Estruturas =====

@dataclass
class PontoCandidato:
    """Um ponto de pesquisa para um candidato."""
    pesquisa_id: str
    data: date
    instituto_nome: str
    instituto_id: str
    confiabilidade: int
    amostra: int | None
    margem_erro: float | None
    metodologia: str
    percentual: float
    peso: float = 0


@dataclass
class AgregadoCandidato:
    """Estimativa agregada para um candidato."""
    nome: str
    estimativa: float
    banda_inferior: float
    banda_superior: float
    n_pesquisas: int
    peso_total: float
    ultima_data: date | None
    pontos: list[PontoCandidato]


# ===== Cálculo =====

def peso_recencia(data_pesquisa: date, data_referencia: date, meia_vida_dias: int = MEIA_VIDA_DIAS_DEFAULT) -> float:
    """Decaimento exponencial: peso = exp(-dias / meia_vida)."""
    dias = max((data_referencia - data_pesquisa).days, 0)
    return math.exp(-dias / meia_vida_dias)


def peso_amostra(amostra: int | None) -> float:
    if not amostra or amostra <= 0:
        return FLOOR_PESO_AMOSTRA
    p = math.sqrt(amostra / AMOSTRA_REFERENCIA)
    return max(FLOOR_PESO_AMOSTRA, min(p, CAP_PESO_AMOSTRA))


def peso_confiabilidade(score: int | None) -> float:
    if not score:
        return 0.5
    return (score / 5) ** 1.5


def peso_metodologia(metodo: str | None) -> float:
    if not metodo:
        return 0.85
    return PESOS_METODOLOGIA.get(metodo.lower(), 0.85)


def calcular_peso_total(
    data_pesquisa: date,
    data_referencia: date,
    amostra: int | None,
    score: int | None,
    metodo: str | None,
    meia_vida: int = MEIA_VIDA_DIAS_DEFAULT,
) -> float:
    return (
        peso_recencia(data_pesquisa, data_referencia, meia_vida)
        * peso_amostra(amostra)
        * peso_confiabilidade(score)
        * peso_metodologia(metodo)
    )


def agregar_candidato(pontos: list[PontoCandidato]) -> tuple[float, float]:
    """Retorna (estimativa, desvio_padrao_ponderado).

    Cada ponto deve já ter peso atribuído.
    """
    if not pontos:
        return (0.0, 0.0)
    total_peso = sum(p.peso for p in pontos)
    if total_peso == 0:
        return (0.0, 0.0)
    estimativa = sum(p.percentual * p.peso for p in pontos) / total_peso
    if len(pontos) == 1:
        return (estimativa, 0.0)
    var = sum(p.peso * (p.percentual - estimativa) ** 2 for p in pontos) / total_peso
    return (estimativa, math.sqrt(var))


def banda_95(desvio: float, margens_erro: list[float]) -> float:
    """Banda 95% combinando desvio dos pontos + erro amostral médio + erro metodológico."""
    erro_amostral = sum(margens_erro) / len(margens_erro) if margens_erro else 3.0
    erro_total = math.sqrt(desvio ** 2 + erro_amostral ** 2 + ERRO_METODOLOGICO_PP ** 2)
    return 1.96 * erro_total


# ===== Monte Carlo =====

def monte_carlo_simulacao(
    candidatos: list[dict],
    n_simulacoes: int = 10000,
) -> dict:
    """Simula N cenários com distribuição Normal(estimativa, desvio).

    Retorna probabilidades de vitória 1T, ida a 2T, e cenários prováveis de 2T.
    """
    import random

    if not candidatos or len(candidatos) < 2:
        return {"prob_1t": {}, "prob_2t": {}, "cenarios_2t": [], "n_simulacoes": 0}

    nomes = [c["nome"] for c in candidatos]
    medias = [c["estimativa"] for c in candidatos]
    desvios = [max((c["banda_superior"] - c["banda_inferior"]) / 3.92, 0.5) for c in candidatos]

    contagem_1t = {n: 0 for n in nomes}
    contagem_2t = {n: 0 for n in nomes}
    pares_2t: dict[tuple[str, str], dict] = {}

    for _ in range(n_simulacoes):
        sorteios = [(nomes[i], max(0, random.gauss(medias[i], desvios[i]))) for i in range(len(nomes))]
        total = sum(s[1] for s in sorteios)
        if total > 0:
            sorteios = [(n, p * 100 / total) for n, p in sorteios]
        sorteios.sort(key=lambda x: -x[1])

        primeiro = sorteios[0]
        if primeiro[1] > 50:
            contagem_1t[primeiro[0]] += 1
        else:
            top2 = (sorteios[0][0], sorteios[1][0])
            contagem_2t[top2[0]] += 1
            contagem_2t[top2[1]] += 1
            par = tuple(sorted(top2))
            if par not in pares_2t:
                pares_2t[par] = {par[0]: 0, par[1]: 0, "total": 0}
            pares_2t[par]["total"] += 1
            pares_2t[par][primeiro[0]] += 1

    return {
        "n_simulacoes": n_simulacoes,
        "prob_1t": {n: round(100 * c / n_simulacoes, 1) for n, c in contagem_1t.items() if c > 0},
        "prob_2t": {n: round(100 * c / n_simulacoes, 1) for n, c in contagem_2t.items() if c > 0},
        "cenarios_2t": sorted([
            {
                "candidato_a": par[0],
                "candidato_b": par[1],
                "probabilidade": round(100 * d["total"] / n_simulacoes, 1),
                "favorito": par[0] if d[par[0]] > d[par[1]] else par[1],
            }
            for par, d in pares_2t.items() if d["total"] > 0
        ], key=lambda x: -x["probabilidade"])[:5],
    }


# ===== Endpoint principal =====

def calcular_agregado(
    db: Session,
    estado_id: str | None = None,
    cargo: str | None = None,
    cenario: str = "estimulado",
    desde: date | None = None,
    ate: date | None = None,
    incluir_apenas_tse: bool = False,
    institutos_excluidos: Iterable[str] | None = None,
    meia_vida_dias: int = MEIA_VIDA_DIAS_DEFAULT,
) -> dict:
    """Calcula agregado para um cenário.

    Retorna dict com:
    - candidatos: list[AgregadoCandidato]
    - serie_temporal: list[dict] — média móvel diária para gráfico
    - meta: configurações usadas
    """
    # 1) Busca pesquisas + intenções relevantes
    q = (
        db.query(IntencaoVoto, Pesquisa, InstitutoPesquisa)
        .join(Pesquisa, Pesquisa.id == IntencaoVoto.pesquisa_id)
        .join(InstitutoPesquisa, InstitutoPesquisa.id == Pesquisa.instituto_id)
        .filter(Pesquisa.status_revisao == "aprovada")
    )
    if estado_id:
        q = q.filter(Pesquisa.estado_id == estado_id)
    else:
        q = q.filter(Pesquisa.estado_id.is_(None))  # pesquisas nacionais
    if cenario:
        q = q.filter(Pesquisa.tipo_cenario == cenario)
    if desde:
        q = q.filter(Pesquisa.data_fim_campo >= desde)
    if ate:
        q = q.filter(Pesquisa.data_fim_campo <= ate)
    if incluir_apenas_tse:
        q = q.filter(Pesquisa.registro_tse.isnot(None))
    if institutos_excluidos:
        q = q.filter(~Pesquisa.instituto_id.in_(list(institutos_excluidos)))

    rows = q.all()
    if not rows:
        return {
            "candidatos": [],
            "serie_temporal": [],
            "meta": {
                "n_pesquisas": 0,
                "n_institutos": 0,
                "estado_id": estado_id,
                "cargo": cargo,
                "cenario": cenario,
                "meia_vida_dias": meia_vida_dias,
            },
        }

    # 2) Data de referência = mais recente
    datas_validas = [p.data_fim_campo for _, p, _ in rows if p.data_fim_campo]
    data_ref = max(datas_validas) if datas_validas else date.today()

    # 3) Agrupa por candidato (nome_referencia)
    pontos_por_cand: dict[str, list[PontoCandidato]] = defaultdict(list)

    for iv, pesq, inst in rows:
        if not iv.nome_referencia or not iv.percentual or not pesq.data_fim_campo:
            continue
        nome = iv.nome_referencia.strip()
        peso = calcular_peso_total(
            pesq.data_fim_campo,
            data_ref,
            pesq.amostra,
            inst.confiabilidade_score,
            pesq.metodologia,
            meia_vida_dias,
        )
        pontos_por_cand[nome].append(
            PontoCandidato(
                pesquisa_id=pesq.id,
                data=pesq.data_fim_campo,
                instituto_nome=inst.nome,
                instituto_id=inst.id,
                confiabilidade=inst.confiabilidade_score or 3,
                amostra=pesq.amostra,
                margem_erro=float(pesq.margem_erro) if pesq.margem_erro else None,
                metodologia=pesq.metodologia or "presencial",
                percentual=float(iv.percentual),
                peso=peso,
            )
        )

    # 4) Calcula agregado por candidato
    agregados: list[AgregadoCandidato] = []
    for nome, pontos in pontos_por_cand.items():
        if len(pontos) < 1:
            continue
        estimativa, desvio = agregar_candidato(pontos)
        margens = [p.margem_erro for p in pontos if p.margem_erro]
        banda = banda_95(desvio, margens)
        ultima = max(p.data for p in pontos)
        agregados.append(
            AgregadoCandidato(
                nome=nome,
                estimativa=round(estimativa, 2),
                banda_inferior=round(max(estimativa - banda, 0), 2),
                banda_superior=round(min(estimativa + banda, 100), 2),
                n_pesquisas=len(pontos),
                peso_total=round(sum(p.peso for p in pontos), 3),
                ultima_data=ultima,
                pontos=pontos,
            )
        )

    # Ordena por estimativa decrescente (líder primeiro)
    agregados.sort(key=lambda a: -a.estimativa)

    # 5) Série temporal: para cada data única, recalcula tomando a data como referência
    datas_unicas = sorted({p.data for ag in agregados for p in ag.pontos})
    serie_temporal = []
    for data in datas_unicas:
        ponto_data = {"data": data.isoformat(), "data_label": data.strftime("%d/%m/%y")}
        for ag in agregados:
            # Considera apenas pontos até essa data
            pontos_ate = [p for p in ag.pontos if p.data <= data]
            if not pontos_ate:
                continue
            # Recalcula peso de recência usando 'data' como referência
            for p in pontos_ate:
                p.peso = calcular_peso_total(
                    p.data, data, p.amostra, p.confiabilidade, p.metodologia, meia_vida_dias
                )
            est, _ = agregar_candidato(pontos_ate)
            ponto_data[ag.nome] = round(est, 2)
        serie_temporal.append(ponto_data)

    # Restaura pesos em relação à data_ref
    for ag in agregados:
        for p in ag.pontos:
            p.peso = calcular_peso_total(
                p.data, data_ref, p.amostra, p.confiabilidade, p.metodologia, meia_vida_dias
            )

    institutos_set = {p.instituto_id for ag in agregados for p in ag.pontos}

    return {
        "candidatos": [
            {
                "nome": ag.nome,
                "estimativa": ag.estimativa,
                "banda_inferior": ag.banda_inferior,
                "banda_superior": ag.banda_superior,
                "n_pesquisas": ag.n_pesquisas,
                "peso_total": ag.peso_total,
                "ultima_data": ag.ultima_data.isoformat() if ag.ultima_data else None,
                "pontos": [
                    {
                        "pesquisa_id": p.pesquisa_id,
                        "data": p.data.isoformat(),
                        "instituto_id": p.instituto_id,
                        "instituto_nome": p.instituto_nome,
                        "amostra": p.amostra,
                        "margem_erro": p.margem_erro,
                        "metodologia": p.metodologia,
                        "percentual": p.percentual,
                        "peso": round(p.peso, 4),
                    }
                    for p in ag.pontos
                ],
            }
            for ag in agregados
        ],
        "serie_temporal": serie_temporal,
        "meta": {
            "n_pesquisas": len({p.pesquisa_id for ag in agregados for p in ag.pontos}),
            "n_institutos": len(institutos_set),
            "data_referencia": data_ref.isoformat(),
            "estado_id": estado_id,
            "cargo": cargo,
            "cenario": cenario,
            "meia_vida_dias": meia_vida_dias,
            "amostra_referencia": AMOSTRA_REFERENCIA,
        },
    }
