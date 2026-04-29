"""Endpoints de análise da base do governo Lula no Congresso."""
import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import (
    OrientacaoPartido,
    Partido,
    Pessoa,
    VotacaoCongresso,
    VotoParlamentar,
)
from app.services.deps import get_current_user, require_role
from app.services.fidelidade import calcular_fidelidade_parlamentares, estatisticas_base_aliada

router = APIRouter(prefix="/governo", tags=["governo"])


@router.get("/base-aliada/sumario")
def sumario_base_aliada(
    meses: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Estatísticas agregadas da base no Congresso."""
    return estatisticas_base_aliada(db, meses=meses)


@router.get("/base-aliada/fidelidade")
def fidelidade_parlamentares(
    meses: int = Query(12, ge=1, le=36),
    casa: str | None = Query(None, description="camara|senado"),
    partido_sigla: str | None = Query(None),
    min_votacoes: int = Query(1, description="Mínimo de votações consideradas"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista todos os parlamentares com seu % de fidelidade."""
    fids = calcular_fidelidade_parlamentares(db, meses=meses)
    if partido_sigla:
        fids = [f for f in fids if f["partido_sigla"] == partido_sigla.upper()]
    fids = [f for f in fids if f["total_votacoes"] >= min_votacoes]

    if casa:
        # Filtra por casa via mandato
        from app.models import Mandato
        cargo = "deputado_federal" if casa == "camara" else "senador"
        ids_casa = {
            m.pessoa_id
            for m in db.query(Mandato).filter(Mandato.cargo == cargo).all()
        }
        fids = [f for f in fids if f["pessoa_id"] in ids_casa]

    fids.sort(key=lambda f: -f["fidelidade_pct"])
    return fids


@router.get("/votacoes")
def list_votacoes(
    posicionamento: str | None = Query(None),
    tema: str | None = Query(None),
    casa: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista votações do Congresso."""
    q = db.query(VotacaoCongresso)
    if posicionamento:
        q = q.filter(VotacaoCongresso.posicionamento_governo == posicionamento)
    if tema:
        q = q.filter(VotacaoCongresso.tema == tema)
    if casa:
        q = q.filter(VotacaoCongresso.casa == casa)

    rows = q.order_by(desc(VotacaoCongresso.data)).limit(limit).all()

    return [
        {
            "id": v.id,
            "casa": v.casa,
            "data": v.data.isoformat() if v.data else None,
            "ementa": v.ementa,
            "tipo": v.tipo_proposicao,
            "numero": v.numero,
            "ano": v.ano,
            "posicionamento_governo": v.posicionamento_governo,
            "classificacao_ia_sugerida": v.classificacao_ia_sugerida,
            "classificacao_ia_confianca": float(v.classificacao_ia_confianca) if v.classificacao_ia_confianca else None,
            "tema": v.tema,
            "resultado": v.resultado,
            "votos_sim": v.votos_sim,
            "votos_nao": v.votos_nao,
            "votos_abstencao": v.votos_abstencao,
        }
        for v in rows
    ]


@router.get("/votacoes/{votacao_id}")
def get_votacao(
    votacao_id: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    v = db.query(VotacaoCongresso).filter(VotacaoCongresso.id == votacao_id).first()
    if not v:
        raise HTTPException(404, "Votação não encontrada")

    # Orientações partidárias
    orientacoes_raw = (
        db.query(OrientacaoPartido, Partido)
        .join(Partido, Partido.id == OrientacaoPartido.partido_id)
        .filter(OrientacaoPartido.votacao_id == votacao_id)
        .all()
    )

    # Votos individuais (top 50)
    votos_raw = (
        db.query(VotoParlamentar, Pessoa)
        .join(Pessoa, Pessoa.id == VotoParlamentar.pessoa_id)
        .filter(VotoParlamentar.votacao_id == votacao_id)
        .limit(600)
        .all()
    )

    return {
        "id": v.id,
        "casa": v.casa,
        "data": v.data.isoformat(),
        "ementa": v.ementa,
        "descricao_completa": v.descricao_completa,
        "tipo_proposicao": v.tipo_proposicao,
        "numero": v.numero,
        "ano": v.ano,
        "posicionamento_governo": v.posicionamento_governo,
        "classificacao_ia_sugerida": v.classificacao_ia_sugerida,
        "classificacao_ia_confianca": float(v.classificacao_ia_confianca) if v.classificacao_ia_confianca else None,
        "tema": v.tema,
        "resultado": v.resultado,
        "votos_sim": v.votos_sim,
        "votos_nao": v.votos_nao,
        "votos_abstencao": v.votos_abstencao,
        "orientacoes": [
            {"partido_sigla": p.sigla, "partido_cor": p.cor_hex, "orientacao": o.orientacao}
            for o, p in orientacoes_raw
        ],
        "votos_individuais": [
            {
                "pessoa_id": pessoa.id,
                "nome": pessoa.nome_urna or pessoa.nome_completo,
                "voto": vp.voto,
            }
            for vp, pessoa in votos_raw
        ],
    }


@router.post("/votacoes/{votacao_id}/classificar")
def classificar_manualmente(
    votacao_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Classifica posicionamento_governo manualmente."""
    v = db.query(VotacaoCongresso).filter(VotacaoCongresso.id == votacao_id).first()
    if not v:
        raise HTTPException(404, "Votação não encontrada")
    classe = payload.get("posicionamento_governo")
    if classe not in ("a_favor", "contra", "liberada", "sem_orientacao", "desconhecido"):
        raise HTTPException(400, "Classificação inválida")
    v.posicionamento_governo = classe
    if "tema" in payload:
        v.tema = payload["tema"]
    db.commit()
    return {"ok": True, "posicionamento_governo": classe}


# ===== Ingestão de votações + classificação IA =====

@router.post("/ingestao/votacoes/run")
def trigger_ingestao_votacoes(
    background_tasks: BackgroundTasks,
    dias: int = Query(60, ge=7, le=365),
    sincrono: bool = Query(False),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Dispara ingestão de votações Câmara dos últimos N dias."""
    from app.workers.camara_votacoes import sincronizar_votacoes

    def _run():
        db = SessionLocal()
        try:
            return sincronizar_votacoes(db=db, dias_atras=dias)
        finally:
            db.close()

    if sincrono:
        return _run()
    background_tasks.add_task(_run)
    return {"status": "iniciado em background", "dias": dias}


@router.post("/ingestao/votacoes/classificar")
def trigger_classificacao_ia(
    background_tasks: BackgroundTasks,
    limit: int = Query(30, le=100),
    sincrono: bool = Query(False),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Dispara classificação IA de votações pendentes."""
    from app.services.ai_votacao_classifier import classificar_lote

    def _run():
        db = SessionLocal()
        try:
            return classificar_lote(db, limit=limit)
        finally:
            db.close()

    if sincrono:
        return _run()
    background_tasks.add_task(_run)
    return {"status": "iniciado em background", "limit": limit}
