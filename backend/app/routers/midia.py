from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FonteRSS, Materia, MateriaEstado
from app.schemas.common import MateriaOut
from app.services.deps import get_current_user

router = APIRouter(prefix="/midia", tags=["midia"])


@router.get("/materias", response_model=list[MateriaOut])
def list_materias(
    estado_id: str | None = Query(None),
    fonte_id: str | None = Query(None),
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    if estado_id:
        q = (
            db.query(Materia)
            .join(MateriaEstado, MateriaEstado.materia_id == Materia.id)
            .filter(MateriaEstado.estado_id == estado_id)
        )
    else:
        q = db.query(Materia)
    if fonte_id:
        q = q.filter(Materia.fonte_id == fonte_id)
    return q.order_by(desc(Materia.data_publicacao)).limit(limit).all()


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
