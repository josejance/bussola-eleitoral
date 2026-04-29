"""Simulador de cenários estratégicos.

Modelo heurístico (não-ML) que projeta resultado eleitoral por estado dado:
- Aprovação atual de Lula (slider 30-70%)
- Status PT por estado (atual ou ajustado)
- Coligação (atual ou simulada)
- Pesquisas atuais (agregado calculado)

Saída: para cada estado, probabilidade de vitória do candidato apoiado pelo PT,
projeção de bancada federal e composição agregada.
"""
from __future__ import annotations

import math
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Candidatura,
    Estado,
    Pessoa,
    Partido,
)
from app.models.editorial import StatusPTEstado
from app.services.aggregator import calcular_agregado


# Pesos do modelo
PESO_PESQUISA = 0.50
PESO_HISTORICO = 0.20
PESO_APROVACAO_LULA = 0.20
PESO_COLIGACAO = 0.10

# Aprovação Lula baseline (Quaest abr/2026 ~38-42%)
APROVACAO_BASELINE = 40.0


def projetar_estado(
    db: Session,
    estado_id: str,
    aprovacao_lula: float,
    cenario_governador: str | None = None,
    bonus_coligacao: float = 0,
) -> dict:
    """Projeta resultado para um estado.

    Args:
        aprovacao_lula: 0-100, atual ou simulada
        cenario_governador: força um cenário (candidatura_propria, vice_aliado, etc)
        bonus_coligacao: ajuste manual em pp (-10 a +10)

    Retorna: {prob_vitoria_apoiado, projecao_bancada_federal, fatores}
    """
    estado = db.query(Estado).filter(Estado.id == estado_id).first()
    if not estado:
        raise ValueError("Estado não encontrado")

    status = db.query(StatusPTEstado).filter(StatusPTEstado.estado_id == estado_id).first()
    cenario_atual = cenario_governador or (status.cenario_governador if status else "indefinido")

    # Componente 1: pesquisa atual (apenas pesquisas ELEITORAIS, não temáticas)
    agregado = calcular_agregado(db, estado_id=estado_id, cenario="estimulado")
    cand_apoiado_pct = 0
    pesquisa_disponivel = False
    if agregado["candidatos"]:
        # Heurística: candidato apoiado pelo PT é o do partido PT ou aliado
        from app.models import Pesquisa, IntencaoVoto
        pt_partidos = {"PT", "PCdoB", "PV", "PSB", "PSOL", "REDE", "PDT"}
        # Pega top 3 e checa se algum tem partido aliado
        for c in agregado["candidatos"][:5]:
            # Tenta extrair sigla do partido do nome (ex: "Lula (PT)")
            import re
            m = re.search(r"\(([A-Z]+)\)", c["nome"])
            sigla = m.group(1) if m else None
            if sigla in pt_partidos:
                cand_apoiado_pct = c["estimativa"]
                pesquisa_disponivel = True
                break

    # Componente 2: histórico (pega votação federal PT mais recente do estado)
    from app.models import VotacaoPartidoEstado
    vps_pt = (
        db.query(VotacaoPartidoEstado)
        .filter(VotacaoPartidoEstado.estado_id == estado_id)
        .filter(VotacaoPartidoEstado.cargo == "deputado_federal")
        .order_by(VotacaoPartidoEstado.eleicao_id.desc())
        .first()
    )
    historico_pct = float(vps_pt.percentual_total) if vps_pt and vps_pt.percentual_total else 10.0

    # Componente 3: aprovação Lula (impacto: +1pp aprovação = +0.3pp candidato)
    impacto_lula = (aprovacao_lula - APROVACAO_BASELINE) * 0.3

    # Componente 4: cenário/coligação
    bonus_cenario = {
        "candidatura_propria": 5,
        "vice_aliado": 2,
        "apoio_sem_cargo": -2,
        "oposicao": -10,
        "indefinido": 0,
    }.get(cenario_atual, 0)

    # Cálculo final: estimativa de % do candidato
    estimativa_apoiado = (
        cand_apoiado_pct * PESO_PESQUISA
        + historico_pct * PESO_HISTORICO
        + 35 * PESO_APROVACAO_LULA  # baseline 35% para aliado, ajustado por impacto_lula
        + impacto_lula
        + bonus_cenario
        + bonus_coligacao
    )
    estimativa_apoiado = max(5, min(70, estimativa_apoiado))

    # Probabilidade de vitória: sigmoidal centrada em 33% (cenário 3-4 candidatos)
    # Quanto mais perto de 50%, maior prob
    centro = 33
    sensibilidade = 0.15
    prob_vitoria = 1 / (1 + math.exp(-sensibilidade * (estimativa_apoiado - centro)))

    # Projeção bancada federal: histórico × (1 + variacao)
    bancada_atual = vps_pt.bancada_eleita if vps_pt else 0
    fator_crescimento = (estimativa_apoiado - historico_pct) / max(historico_pct, 5) * 0.5  # amortecido
    bancada_projetada = max(0, round(bancada_atual * (1 + fator_crescimento)))

    return {
        "estado_sigla": estado.sigla,
        "estado_nome": estado.nome,
        "cenario_governador": cenario_atual,
        "estimativa_candidato_apoiado_pct": round(estimativa_apoiado, 1),
        "prob_vitoria_apoiado": round(prob_vitoria * 100, 1),
        "bancada_federal_atual": bancada_atual,
        "bancada_federal_projetada": bancada_projetada,
        "fatores": {
            "pesquisa_atual_pct": cand_apoiado_pct if pesquisa_disponivel else None,
            "historico_pt_federal_pct": historico_pct,
            "impacto_aprovacao_lula_pp": round(impacto_lula, 1),
            "bonus_cenario_pp": bonus_cenario,
            "bonus_coligacao_pp": bonus_coligacao,
        },
    }


def simular_cenario(
    db: Session,
    aprovacao_lula: float = 40.0,
    ajustes_estados: dict[str, dict] | None = None,
    bonus_coligacao_geral: float = 0,
) -> dict:
    """Simula cenário para todos os 27 estados.

    ajustes_estados: {estado_sigla: {cenario_governador?, bonus_coligacao?}}
    """
    ajustes_estados = ajustes_estados or {}

    # Mapeia ajustes por estado_id
    estados_map = {e.sigla: e for e in db.query(Estado).all()}
    ajustes_por_id = {}
    for sigla, aj in ajustes_estados.items():
        e = estados_map.get(sigla.upper())
        if e:
            ajustes_por_id[e.id] = aj

    projecoes = []
    for sigla, e in estados_map.items():
        aj = ajustes_por_id.get(e.id, {})
        try:
            p = projetar_estado(
                db,
                e.id,
                aprovacao_lula=aprovacao_lula,
                cenario_governador=aj.get("cenario_governador"),
                bonus_coligacao=aj.get("bonus_coligacao", bonus_coligacao_geral),
            )
            projecoes.append(p)
        except Exception:
            continue

    # Agregados nacionais
    total_estados = len(projecoes)
    estados_propria = [p for p in projecoes if p["cenario_governador"] == "candidatura_propria"]
    estados_chapa_maj = [p for p in projecoes if p["cenario_governador"] in ("candidatura_propria", "vice_aliado")]
    bancada_federal_atual = sum(p["bancada_federal_atual"] for p in projecoes)
    bancada_federal_projetada = sum(p["bancada_federal_projetada"] for p in projecoes)

    # Estados com prob > 50%
    vitorias_provaveis = [p for p in projecoes if p["prob_vitoria_apoiado"] > 50]

    return {
        "parametros": {
            "aprovacao_lula": aprovacao_lula,
            "bonus_coligacao_geral": bonus_coligacao_geral,
            "n_estados_ajustados": len(ajustes_estados),
        },
        "agregados": {
            "total_estados": total_estados,
            "estados_candidatura_propria": len(estados_propria),
            "estados_chapa_majoritaria": len(estados_chapa_maj),
            "bancada_federal_atual": bancada_federal_atual,
            "bancada_federal_projetada": bancada_federal_projetada,
            "delta_bancada": bancada_federal_projetada - bancada_federal_atual,
            "vitorias_provaveis_governador": len(vitorias_provaveis),
            "media_prob_vitoria": round(sum(p["prob_vitoria_apoiado"] for p in projecoes) / total_estados, 1) if total_estados else 0,
        },
        "projecoes_por_estado": sorted(projecoes, key=lambda x: -x["prob_vitoria_apoiado"]),
    }
