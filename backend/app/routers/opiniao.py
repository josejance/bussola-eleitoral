"""Endpoints de pesquisas temáticas (opinião sobre temas não-eleitorais)."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Estado, InstitutoPesquisa
from app.models.opiniao import (
    PesquisaTematica,
    PesquisaTematicaDadosBrutos,
    PesquisaTematicaQuestao,
)
from app.services.deps import get_current_user

router = APIRouter(prefix="/opiniao", tags=["opiniao"])


@router.get("/temas")
def list_temas(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Lista temas disponíveis com contagem."""
    rows = (
        db.query(PesquisaTematica.tema, func.count(PesquisaTematica.id).label("total"))
        .group_by(PesquisaTematica.tema)
        .order_by(desc("total"))
        .all()
    )
    return [{"tema": t, "total": n} for t, n in rows]


@router.get("/pesquisas")
def list_pesquisas_tematicas(
    tema: str | None = Query(None),
    estado_id: str | None = Query(None),
    abrangencia: str | None = Query(None),
    instituto_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Lista pesquisas temáticas com filtros."""
    q = db.query(PesquisaTematica)
    if tema:
        q = q.filter(PesquisaTematica.tema == tema)
    if estado_id:
        q = q.filter(PesquisaTematica.estado_id == estado_id)
    if abrangencia:
        q = q.filter(PesquisaTematica.abrangencia == abrangencia)
    if instituto_id:
        q = q.filter(PesquisaTematica.instituto_id == instituto_id)

    rows = q.order_by(desc(PesquisaTematica.data_fim_campo)).limit(limit).all()

    # Hidrata instituto e estado
    inst_ids = list({r.instituto_id for r in rows})
    estado_ids = list({r.estado_id for r in rows if r.estado_id})
    institutos = {
        i.id: i for i in db.query(InstitutoPesquisa).filter(InstitutoPesquisa.id.in_(inst_ids)).all()
    } if inst_ids else {}
    estados = {
        e.id: e for e in db.query(Estado).filter(Estado.id.in_(estado_ids)).all()
    } if estado_ids else {}

    # Conta questões
    questoes_count = dict(
        db.query(PesquisaTematicaQuestao.pesquisa_id, func.count(PesquisaTematicaQuestao.id))
        .filter(PesquisaTematicaQuestao.pesquisa_id.in_([r.id for r in rows]))
        .group_by(PesquisaTematicaQuestao.pesquisa_id)
        .all()
    ) if rows else {}

    return [
        {
            "id": p.id,
            "titulo": p.titulo,
            "subtitulo": p.subtitulo,
            "tema": p.tema,
            "abrangencia": p.abrangencia,
            "estado_sigla": estados[p.estado_id].sigla if p.estado_id and p.estado_id in estados else None,
            "data_inicio_campo": p.data_inicio_campo.isoformat() if p.data_inicio_campo else None,
            "data_fim_campo": p.data_fim_campo.isoformat() if p.data_fim_campo else None,
            "amostra": p.amostra,
            "margem_erro": float(p.margem_erro) if p.margem_erro else None,
            "metodologia": p.metodologia,
            "contratante": p.contratante,
            "instituto_nome": institutos[p.instituto_id].nome if p.instituto_id in institutos else "?",
            "instituto_sigla": institutos[p.instituto_id].sigla if p.instituto_id in institutos else None,
            "registro_eleitoral": p.registro_eleitoral,
            "publico_alvo": p.publico_alvo,
            "n_questoes": questoes_count.get(p.id, 0),
        }
        for p in rows
    ]


@router.get("/pesquisas/{pesquisa_id}")
def get_pesquisa_tematica(
    pesquisa_id: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    """Detalhe completo de uma pesquisa temática com todas as questões."""
    p = db.query(PesquisaTematica).filter(PesquisaTematica.id == pesquisa_id).first()
    if not p:
        raise HTTPException(404, "Pesquisa temática não encontrada")

    instituto = db.query(InstitutoPesquisa).filter(InstitutoPesquisa.id == p.instituto_id).first()
    estado = db.query(Estado).filter(Estado.id == p.estado_id).first() if p.estado_id else None

    questoes = (
        db.query(PesquisaTematicaQuestao)
        .filter(PesquisaTematicaQuestao.pesquisa_id == pesquisa_id)
        .order_by(PesquisaTematicaQuestao.numero)
        .all()
    )

    return {
        "id": p.id,
        "titulo": p.titulo,
        "subtitulo": p.subtitulo,
        "tema": p.tema,
        "abrangencia": p.abrangencia,
        "estado_sigla": estado.sigla if estado else None,
        "estado_nome": estado.nome if estado else None,
        "data_inicio_campo": p.data_inicio_campo.isoformat() if p.data_inicio_campo else None,
        "data_fim_campo": p.data_fim_campo.isoformat() if p.data_fim_campo else None,
        "amostra": p.amostra,
        "margem_erro": float(p.margem_erro) if p.margem_erro else None,
        "nivel_confianca": float(p.nivel_confianca) if p.nivel_confianca else None,
        "metodologia": p.metodologia,
        "contratante": p.contratante,
        "instituto": {
            "id": instituto.id if instituto else None,
            "nome": instituto.nome if instituto else "?",
            "sigla": instituto.sigla if instituto else None,
        },
        "publico_alvo": p.publico_alvo,
        "registro_eleitoral": p.registro_eleitoral,
        "observacao": p.observacao,
        "questoes": [
            {
                "id": q.id,
                "numero": q.numero,
                "titulo_questao": q.titulo_questao,
                "enunciado": q.enunciado,
                "tipo_resposta": q.tipo_resposta,
                "dados_gerais": json.loads(q.dados_gerais_json) if q.dados_gerais_json else None,
                "cruzamentos": json.loads(q.cruzamentos_json) if q.cruzamentos_json else None,
            }
            for q in questoes
        ],
    }


@router.get("/pesquisas/{pesquisa_id}/dados-brutos")
def get_dados_brutos_tematica(
    pesquisa_id: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    bruto = (
        db.query(PesquisaTematicaDadosBrutos)
        .filter(PesquisaTematicaDadosBrutos.pesquisa_id == pesquisa_id)
        .first()
    )
    if not bruto:
        raise HTTPException(404, "Dados brutos não encontrados")
    return {
        "pesquisa_id": pesquisa_id,
        "formato_origem": bruto.formato_origem,
        "arquivo_origem": bruto.arquivo_origem,
        "importado_em": bruto.importado_em.isoformat() if bruto.importado_em else None,
        "dados_json": json.loads(bruto.dados_json),
        "analise_ia": json.loads(bruto.analise_ia_json) if bruto.analise_ia_json else None,
    }


# Mapeamento de tema → label amigável + ícone
TEMA_META = {
    "apostas_esportivas": {"label": "Apostas Esportivas", "icone": "trophy", "cor": "#EA580C"},
    "copa_mundo": {"label": "Copa do Mundo", "icone": "trophy", "cor": "#16A34A"},
    "stf": {"label": "STF", "icone": "scale", "cor": "#7C3AED"},
    "etica_stf": {"label": "Ética no STF", "icone": "scale", "cor": "#7C3AED"},
    "imposto_renda": {"label": "Imposto de Renda", "icone": "file-text", "cor": "#0891B2"},
    "venezuela": {"label": "Venezuela", "icone": "globe", "cor": "#DC2626"},
    "urnas_eletronicas": {"label": "Urnas Eletrônicas", "icone": "vote", "cor": "#2563EB"},
    "imagem_lideres": {"label": "Imagem de Líderes", "icone": "users", "cor": "#DB2777"},
    "brasil_geral": {"label": "Brasil Geral", "icone": "flag", "cor": "#16A34A"},
    "outros": {"label": "Outros", "icone": "help-circle", "cor": "#6B7280"},
}


@router.get("/temas/metadata")
def get_temas_metadata(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    """Retorna metadados por tema (label, ícone, cor) + contagem."""
    rows = (
        db.query(PesquisaTematica.tema, func.count(PesquisaTematica.id).label("total"))
        .group_by(PesquisaTematica.tema)
        .all()
    )
    counts = {t: n for t, n in rows}
    return [
        {"tema": tema, "total": counts.get(tema, 0), **meta}
        for tema, meta in TEMA_META.items()
        if counts.get(tema, 0) > 0
    ]
