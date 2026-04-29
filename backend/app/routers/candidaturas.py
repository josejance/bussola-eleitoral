"""Endpoints de candidaturas e bancadas históricas."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Candidatura,
    Eleicao,
    Partido,
    Pessoa,
    VotacaoPartidoEstado,
)
from app.services.deps import get_current_user

router = APIRouter(tags=["candidaturas"])


@router.get("/candidaturas")
def list_candidaturas(
    estado_id: str | None = Query(None),
    cargo: str | None = Query(None),
    eleicao_id: str | None = Query(None),
    ano: int | None = Query(None, description="Filtra por ano da eleição"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista candidaturas com pessoa e partido expandidos.

    Por padrão, retorna apenas eleição 2026 turno 1 se nenhum filtro for dado.
    """
    if not eleicao_id and not ano:
        eleicao = db.query(Eleicao).filter(Eleicao.ano == 2026, Eleicao.turno == 1).first()
        if eleicao:
            eleicao_id = eleicao.id
    elif ano and not eleicao_id:
        eleicao = db.query(Eleicao).filter(Eleicao.ano == ano, Eleicao.turno == 1).first()
        if eleicao:
            eleicao_id = eleicao.id

    q = db.query(Candidatura)
    if estado_id:
        q = q.filter(Candidatura.estado_id == estado_id)
    if cargo:
        q = q.filter(Candidatura.cargo == cargo)
    if eleicao_id:
        q = q.filter(Candidatura.eleicao_id == eleicao_id)

    candidaturas = q.all()

    # Hidrata pessoas e partidos em batch
    pessoa_ids = list({c.pessoa_id for c in candidaturas})
    partido_ids = list({c.partido_id for c in candidaturas})
    pessoas = {
        p.id: p for p in db.query(Pessoa).filter(Pessoa.id.in_(pessoa_ids)).all()
    } if pessoa_ids else {}
    partidos = {
        p.id: p for p in db.query(Partido).filter(Partido.id.in_(partido_ids)).all()
    } if partido_ids else {}

    return [
        {
            "id": c.id,
            "eleicao_id": c.eleicao_id,
            "estado_id": c.estado_id,
            "cargo": c.cargo,
            "status_registro": c.status_registro,
            "eh_titular": c.eh_titular,
            "numero_urna": c.numero_urna,
            "observacao": c.observacao,
            "pessoa": (
                {
                    "id": pessoas[c.pessoa_id].id,
                    "nome_completo": pessoas[c.pessoa_id].nome_completo,
                    "nome_urna": pessoas[c.pessoa_id].nome_urna,
                    "foto_url": pessoas[c.pessoa_id].foto_url,
                }
                if c.pessoa_id in pessoas
                else None
            ),
            "partido": (
                {
                    "id": partidos[c.partido_id].id,
                    "sigla": partidos[c.partido_id].sigla,
                    "nome_completo": partidos[c.partido_id].nome_completo,
                    "cor_hex": partidos[c.partido_id].cor_hex,
                    "espectro": partidos[c.partido_id].espectro,
                }
                if c.partido_id in partidos
                else None
            ),
        }
        for c in candidaturas
    ]


@router.get("/historico/votacao-partido-estado")
def historico_votacao_partido(
    estado_id: str = Query(...),
    partido_sigla: str = Query("PT"),
    cargo: str | None = Query(None, description="deputado_federal | deputado_estadual | qualquer"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Histórico de votação de um partido em um estado, por eleição e cargo."""
    partido = db.query(Partido).filter(Partido.sigla == partido_sigla.upper()).first()
    if not partido:
        return []

    q = (
        db.query(VotacaoPartidoEstado)
        .filter(
            VotacaoPartidoEstado.partido_id == partido.id,
            VotacaoPartidoEstado.estado_id == estado_id,
        )
    )
    if cargo:
        q = q.filter(VotacaoPartidoEstado.cargo == cargo)

    rows = q.all()

    # Hidrata eleições para retornar ano/turno
    eleicao_ids = list({r.eleicao_id for r in rows})
    eleicoes = {
        e.id: e for e in db.query(Eleicao).filter(Eleicao.id.in_(eleicao_ids)).all()
    }

    out = [
        {
            "eleicao_id": r.eleicao_id,
            "ano": eleicoes[r.eleicao_id].ano if r.eleicao_id in eleicoes else None,
            "turno": eleicoes[r.eleicao_id].turno if r.eleicao_id in eleicoes else None,
            "cargo": r.cargo,
            "votos_totais": r.votos_totais,
            "percentual_total": float(r.percentual_total) if r.percentual_total else None,
            "bancada_eleita": r.bancada_eleita,
        }
        for r in rows
    ]
    out.sort(key=lambda x: (x["cargo"] or "", x["ano"] or 0))
    return out
