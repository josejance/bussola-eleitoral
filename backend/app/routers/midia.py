from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FonteRSS, Materia, MateriaEstado, MateriaPessoa, Pessoa
from app.schemas.common import MateriaOut, PessoaOut
from app.services.deps import get_current_user

router = APIRouter(prefix="/midia", tags=["midia"])


@router.get("/materias", response_model=list[MateriaOut])
def list_materias(
    estado_id: str | None = Query(None),
    fonte_id: str | None = Query(None),
    pessoa_id: str | None = Query(None),
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    q = db.query(Materia)
    if estado_id:
        q = q.join(MateriaEstado, MateriaEstado.materia_id == Materia.id).filter(
            MateriaEstado.estado_id == estado_id
        )
    if pessoa_id:
        q = q.join(MateriaPessoa, MateriaPessoa.materia_id == Materia.id).filter(
            MateriaPessoa.pessoa_id == pessoa_id
        )
    if fonte_id:
        q = q.filter(Materia.fonte_id == fonte_id)
    return q.order_by(desc(Materia.data_publicacao)).distinct().limit(limit).all()


@router.get("/materias/stats")
def stats_materias_pessoa(
    pessoa_id: str = Query(...),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    base = (
        db.query(Materia)
        .join(MateriaPessoa, MateriaPessoa.materia_id == Materia.id)
        .filter(MateriaPessoa.pessoa_id == pessoa_id)
    )
    total = base.count()
    sete_dias_atras = datetime.now(timezone.utc) - timedelta(days=7)
    ultimos_7d = base.filter(Materia.data_publicacao >= sete_dias_atras).count()
    fontes_distintas = base.with_entities(Materia.fonte_id).distinct().count()
    estados_distintos = (
        db.query(MateriaEstado.estado_id)
        .join(MateriaPessoa, MateriaPessoa.materia_id == MateriaEstado.materia_id)
        .filter(MateriaPessoa.pessoa_id == pessoa_id)
        .distinct()
        .count()
    )
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (
        base.filter(Materia.data_publicacao >= cutoff_30d)
        .with_entities(
            func.date(Materia.data_publicacao).label("dia"),
            func.count(Materia.id).label("n"),
        )
        .group_by("dia")
        .order_by("dia")
        .all()
    )
    timeline = [{"data": str(r.dia), "n": r.n} for r in rows]
    return {
        "total": total,
        "ultimos_7d": ultimos_7d,
        "fontes_distintas": fontes_distintas,
        "estados_distintos": estados_distintos,
        "timeline": timeline,
    }


@router.get("/materias/{materia_id}/pessoas", response_model=list[PessoaOut])
def list_pessoas_da_materia(
    materia_id: str,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    if not db.query(Materia.id).filter(Materia.id == materia_id).first():
        raise HTTPException(404, "Matéria não encontrada")
    return (
        db.query(Pessoa)
        .join(MateriaPessoa, MateriaPessoa.pessoa_id == Pessoa.id)
        .filter(MateriaPessoa.materia_id == materia_id)
        .all()
    )


@router.get("/fontes")
def list_fontes(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return [
        {
            "id": f.id,
            "nome": f.nome,
            "url_site": f.url_site,
            "tipo": f.tipo,
            "espectro_editorial": f.espectro_editorial,
            "ativo": f.ativo,
        }
        for f in db.query(FonteRSS).order_by(FonteRSS.nome).all()
    ]
