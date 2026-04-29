"""Endpoints de pessoas (perfil completo)."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Candidatura,
    Estado,
    Eleicao,
    FiliacaoPartidaria,
    Mandato,
    Materia,
    MateriaPessoa,
    Partido,
    Pesquisa,
    Pessoa,
)
from app.models.editorial import NotaEditorial
from app.services.deps import get_current_user

router = APIRouter(prefix="/pessoas", tags=["pessoas"])


@router.get("/{pessoa_id}")
def get_pessoa_detalhe(
    pessoa_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Perfil completo da pessoa."""
    p = db.query(Pessoa).filter(Pessoa.id == pessoa_id, Pessoa.deleted_at.is_(None)).first()
    if not p:
        raise HTTPException(404, "Pessoa não encontrada")

    # Filiações com partido
    filiacoes_raw = (
        db.query(FiliacaoPartidaria, Partido)
        .join(Partido, Partido.id == FiliacaoPartidaria.partido_id)
        .filter(FiliacaoPartidaria.pessoa_id == pessoa_id)
        .order_by(desc(FiliacaoPartidaria.inicio))
        .all()
    )
    filiacoes = [
        {
            "id": f.id,
            "partido_sigla": part.sigla,
            "partido_nome": part.nome_completo,
            "partido_cor": part.cor_hex,
            "inicio": f.inicio.isoformat() if f.inicio else None,
            "fim": f.fim.isoformat() if f.fim else None,
            "tipo_saida": f.tipo_saida,
            "motivo_saida": f.motivo_saida,
        }
        for f, part in filiacoes_raw
    ]
    partido_atual = filiacoes[0] if filiacoes and not filiacoes[0]["fim"] else None

    # Mandatos
    mandatos_raw = (
        db.query(Mandato, Estado)
        .outerjoin(Estado, Estado.id == Mandato.estado_id)
        .filter(Mandato.pessoa_id == pessoa_id)
        .order_by(desc(Mandato.inicio))
        .all()
    )
    mandatos = [
        {
            "id": m.id,
            "cargo": m.cargo,
            "estado_sigla": e.sigla if e else None,
            "estado_nome": e.nome if e else None,
            "inicio": m.inicio.isoformat() if m.inicio else None,
            "fim": m.fim.isoformat() if m.fim else None,
            "eh_titular": m.eh_titular,
            "eh_suplente": m.eh_suplente,
            "observacao": m.observacao,
        }
        for m, e in mandatos_raw
    ]

    # Candidaturas
    candidaturas_raw = (
        db.query(Candidatura, Eleicao, Estado, Partido)
        .join(Eleicao, Eleicao.id == Candidatura.eleicao_id)
        .outerjoin(Estado, Estado.id == Candidatura.estado_id)
        .outerjoin(Partido, Partido.id == Candidatura.partido_id)
        .filter(Candidatura.pessoa_id == pessoa_id)
        .order_by(desc(Eleicao.ano))
        .all()
    )
    candidaturas = [
        {
            "id": c.id,
            "eleicao_ano": el.ano,
            "eleicao_turno": el.turno,
            "cargo": c.cargo,
            "estado_sigla": e.sigla if e else None,
            "partido_sigla": p_part.sigla if p_part else None,
            "partido_cor": p_part.cor_hex if p_part else None,
            "status_registro": c.status_registro,
            "eh_titular": c.eh_titular,
            "numero_urna": c.numero_urna,
            "observacao": c.observacao,
        }
        for c, el, e, p_part in candidaturas_raw
    ]

    # Matérias mencionando a pessoa
    materias_raw = (
        db.query(Materia)
        .join(MateriaPessoa, MateriaPessoa.materia_id == Materia.id)
        .filter(MateriaPessoa.pessoa_id == pessoa_id)
        .filter(Materia.aproveitada == True)  # noqa: E712
        .order_by(desc(Materia.data_publicacao))
        .limit(50)
        .all()
    )
    materias = [
        {
            "id": m.id,
            "titulo": m.titulo,
            "snippet": m.snippet,
            "url": m.url,
            "data_publicacao": m.data_publicacao.isoformat() if m.data_publicacao else None,
            "imagem_url": m.imagem_url,
        }
        for m in materias_raw
    ]

    # Pesquisas onde aparece
    from app.models import IntencaoVoto
    pesq_raw = (
        db.query(IntencaoVoto, Pesquisa)
        .join(Pesquisa, Pesquisa.id == IntencaoVoto.pesquisa_id)
        .filter(IntencaoVoto.pessoa_id == pessoa_id)
        .order_by(desc(Pesquisa.data_fim_campo))
        .limit(50)
        .all()
    )
    pesquisas = [
        {
            "pesquisa_id": pesq.id,
            "data": pesq.data_fim_campo.isoformat() if pesq.data_fim_campo else None,
            "amostra": pesq.amostra,
            "percentual": float(iv.percentual) if iv.percentual else None,
            "posicao": iv.posicao_no_cenario,
            "estado_id": pesq.estado_id,
            "abrangencia": pesq.abrangencia,
        }
        for iv, pesq in pesq_raw
    ]

    # Notas editoriais (filtradas por permissão)
    SENSIB_PERMITIDA = {
        "admin": ["publico", "interno", "restrito_direcao"],
        "editor_nacional": ["publico", "interno", "restrito_direcao"],
        "editor_estadual": ["publico", "interno", "restrito_direcao"],
        "leitor_pleno": ["publico", "interno"],
        "leitor_publico": ["publico"],
    }
    permitidas = SENSIB_PERMITIDA.get(user.papel, ["publico"])
    notas_raw = (
        db.query(NotaEditorial)
        .filter(NotaEditorial.pessoa_relacionada_id == pessoa_id)
        .filter(NotaEditorial.sensibilidade.in_(permitidas))
        .order_by(desc(NotaEditorial.created_at))
        .limit(20)
        .all()
    )
    notas = [
        {
            "id": n.id,
            "titulo": n.titulo,
            "tema": n.tema,
            "sensibilidade": n.sensibilidade,
            "created_at": n.created_at.isoformat(),
        }
        for n in notas_raw
    ]

    return {
        "id": p.id,
        "nome_completo": p.nome_completo,
        "nome_urna": p.nome_urna,
        "nascimento": p.nascimento.isoformat() if p.nascimento else None,
        "genero": p.genero,
        "raca_cor": p.raca_cor,
        "foto_url": p.foto_url,
        "biografia": p.biografia,
        "email_publico": p.email_publico,
        "redes_sociais": json.loads(p.redes_sociais_json) if p.redes_sociais_json else None,
        "site_pessoal": p.site_pessoal,
        "escolaridade": p.escolaridade,
        "patrimonio_declarado": float(p.patrimonio_declarado) if p.patrimonio_declarado else None,
        "partido_atual": partido_atual,
        "filiacoes": filiacoes,
        "mandatos": mandatos,
        "candidaturas": candidaturas,
        "materias": materias,
        "pesquisas": pesquisas,
        "notas": notas,
        "stats": {
            "total_filiacoes": len(filiacoes),
            "total_mandatos": len(mandatos),
            "total_candidaturas": len(candidaturas),
            "total_materias": len(materias),
            "total_pesquisas": len(pesquisas),
            "total_notas": len(notas),
        },
    }
