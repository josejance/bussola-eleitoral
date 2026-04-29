from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Partido
from app.schemas.common import PartidoOut
from app.services.deps import get_current_user

router = APIRouter(prefix="/partidos", tags=["partidos"])


@router.get("", response_model=list[PartidoOut])
def list_partidos(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Partido).filter(Partido.ativo == True).order_by(Partido.sigla).all()  # noqa: E712
