from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import NotaEditorial
from app.schemas.common import NotaCreate, NotaOut
from app.services.deps import get_current_user, require_role

router = APIRouter(prefix="/notas", tags=["notas"])

# Hierarquia de sensibilidade vs papel
SENSIB_PERMITIDA = {
    "admin": ["publico", "interno", "restrito_direcao"],
    "editor_nacional": ["publico", "interno", "restrito_direcao"],
    "editor_estadual": ["publico", "interno", "restrito_direcao"],  # mas restrita só do próprio estado
    "leitor_pleno": ["publico", "interno"],
    "leitor_publico": ["publico"],
}


@router.get("", response_model=list[NotaOut])
def list_notas(
    estado_id: str | None = Query(None),
    tema: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    permitidas = SENSIB_PERMITIDA.get(user.papel, ["publico"])
    q = db.query(NotaEditorial).filter(NotaEditorial.sensibilidade.in_(permitidas))

    # Editor estadual só vê restritas do próprio estado
    if user.papel == "editor_estadual" and user.estado_referencia_id:
        # restritas: só do próprio estado; outras: todas
        from sqlalchemy import and_, or_
        q = q.filter(
            or_(
                NotaEditorial.sensibilidade != "restrito_direcao",
                and_(
                    NotaEditorial.sensibilidade == "restrito_direcao",
                    NotaEditorial.estado_id == user.estado_referencia_id,
                ),
            )
        )

    if estado_id:
        q = q.filter(NotaEditorial.estado_id == estado_id)
    if tema:
        q = q.filter(NotaEditorial.tema == tema)
    return q.order_by(desc(NotaEditorial.created_at)).limit(limit).all()


@router.post("", response_model=NotaOut, status_code=201)
def create_nota(
    payload: NotaCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("admin", "editor_nacional", "editor_estadual")),
):
    if payload.sensibilidade == "restrito_direcao":
        if user.papel == "editor_estadual" and payload.estado_id != user.estado_referencia_id:
            raise HTTPException(403, "Editor estadual só pode criar nota restrita do próprio estado")

    nota = NotaEditorial(
        **payload.model_dump(),
        autor_id=user.id,
        versao=1,
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)
    return nota


@router.get("/{nota_id}", response_model=NotaOut)
def get_nota(nota_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    n = db.query(NotaEditorial).filter(NotaEditorial.id == nota_id).first()
    if not n:
        raise HTTPException(404, "Nota não encontrada")
    permitidas = SENSIB_PERMITIDA.get(user.papel, ["publico"])
    if n.sensibilidade not in permitidas:
        raise HTTPException(403, "Sem permissão para visualizar esta nota")
    if (
        n.sensibilidade == "restrito_direcao"
        and user.papel == "editor_estadual"
        and n.estado_id != user.estado_referencia_id
    ):
        raise HTTPException(403, "Sem permissão")
    return n
