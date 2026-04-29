from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import EventoTimeline
from app.schemas.common import EventoTimelineCreate, EventoTimelineOut
from app.services.deps import get_current_user, require_role

router = APIRouter(prefix="/eventos", tags=["eventos"])


@router.get("", response_model=list[EventoTimelineOut])
def list_eventos(
    estado_id: str | None = Query(None),
    pessoa_id: str | None = Query(None),
    tipo: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    q = db.query(EventoTimeline)
    if estado_id:
        q = q.filter(EventoTimeline.estado_id == estado_id)
    if pessoa_id:
        q = q.filter(EventoTimeline.pessoa_id == pessoa_id)
    if tipo:
        q = q.filter(EventoTimeline.tipo == tipo)
    return q.order_by(desc(EventoTimeline.data_evento)).limit(limit).all()


@router.post("", response_model=EventoTimelineOut, status_code=201)
def create_evento(
    payload: EventoTimelineCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    e = EventoTimeline(
        **payload.model_dump(),
        criado_por=user.id,
        automatico=False,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e
