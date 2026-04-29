from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Estado, StatusPTEstado
from app.schemas.common import EstadoOut, StatusEstadoOut, StatusEstadoUpdate
from app.services.deps import get_current_user, require_role

router = APIRouter(prefix="/estados", tags=["estados"])


@router.get("", response_model=list[EstadoOut])
def list_estados(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Estado).order_by(Estado.nome).all()


@router.get("/{uf}", response_model=EstadoOut)
def get_estado(uf: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    e = db.query(Estado).filter(Estado.sigla == uf.upper()).first()
    if not e:
        raise HTTPException(404, "Estado não encontrado")
    return e


@router.get("/status/all", response_model=list[StatusEstadoOut])
def list_status(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(StatusPTEstado).all()


@router.get("/{uf}/status", response_model=StatusEstadoOut)
def get_status(uf: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    e = db.query(Estado).filter(Estado.sigla == uf.upper()).first()
    if not e:
        raise HTTPException(404, "Estado não encontrado")
    s = db.query(StatusPTEstado).filter(StatusPTEstado.estado_id == e.id).first()
    if not s:
        raise HTTPException(404, "Status não definido para este estado")
    return s


@router.patch("/{uf}/status", response_model=StatusEstadoOut)
def update_status(
    uf: str,
    payload: StatusEstadoUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    e = db.query(Estado).filter(Estado.sigla == uf.upper()).first()
    if not e:
        raise HTTPException(404, "Estado não encontrado")
    if user.papel == "editor_estadual" and user.estado_referencia_id != e.id:
        raise HTTPException(403, "Editor estadual só pode editar seu próprio estado")

    s = db.query(StatusPTEstado).filter(StatusPTEstado.estado_id == e.id).first()
    if not s:
        s = StatusPTEstado(estado_id=e.id)
        db.add(s)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    s.atualizado_por = user.id

    db.commit()
    db.refresh(s)
    return s
