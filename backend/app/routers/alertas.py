"""Endpoints de alertas e notificações."""
import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import Alerta, Notificacao
from app.services.deps import get_current_user, require_role

router = APIRouter(tags=["alertas"])


# ===== Alertas (regras configuradas) =====

@router.get("/alertas")
def list_alertas(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = (
        db.query(Alerta)
        .filter(Alerta.usuario_id == user.id)
        .order_by(desc(Alerta.created_at))
        .all()
    )
    return [
        {
            "id": a.id,
            "nome": a.nome,
            "tipo": a.tipo,
            "configuracao": json.loads(a.configuracao_json or "{}"),
            "canais": json.loads(a.canais_json or "[]"),
            "ativo": a.ativo,
            "frequencia_max": a.frequencia_max,
            "ultimo_disparo": a.ultimo_disparo.isoformat() if a.ultimo_disparo else None,
            "total_disparos": a.total_disparos or 0,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]


@router.post("/alertas")
def create_alerta(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    tipo = payload.get("tipo")
    if tipo not in ("pesquisa", "movimentacao_politica", "midia", "editorial", "fidelidade", "narrativa", "customizado"):
        raise HTTPException(400, "Tipo inválido")
    a = Alerta(
        usuario_id=user.id,
        nome=payload.get("nome") or f"Alerta {tipo}",
        tipo=tipo,
        configuracao_json=json.dumps(payload.get("configuracao") or {}, ensure_ascii=False),
        canais_json=json.dumps(payload.get("canais") or ["in_app"], ensure_ascii=False),
        ativo=payload.get("ativo", True),
        frequencia_max=payload.get("frequencia_max", "imediato"),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "criado": True}


@router.patch("/alertas/{alerta_id}")
def update_alerta(
    alerta_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    a = db.query(Alerta).filter(Alerta.id == alerta_id, Alerta.usuario_id == user.id).first()
    if not a:
        raise HTTPException(404, "Alerta não encontrado")
    if "ativo" in payload:
        a.ativo = bool(payload["ativo"])
    if "nome" in payload:
        a.nome = payload["nome"]
    if "configuracao" in payload:
        a.configuracao_json = json.dumps(payload["configuracao"], ensure_ascii=False)
    if "canais" in payload:
        a.canais_json = json.dumps(payload["canais"], ensure_ascii=False)
    if "frequencia_max" in payload:
        a.frequencia_max = payload["frequencia_max"]
    db.commit()
    return {"ok": True}


@router.delete("/alertas/{alerta_id}")
def delete_alerta(
    alerta_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    a = db.query(Alerta).filter(Alerta.id == alerta_id, Alerta.usuario_id == user.id).first()
    if not a:
        raise HTTPException(404, "Alerta não encontrado")
    db.delete(a)
    db.commit()
    return {"ok": True}


@router.post("/alertas/avaliar-agora")
def trigger_avaliacao(
    background_tasks: BackgroundTasks,
    sincrono: bool = Query(False),
    _user=Depends(require_role("admin", "editor_nacional")),
):
    """Executa avaliação manual de todos os alertas (admin)."""
    from app.services.alertas_engine import avaliar_todos_alertas

    def _run():
        db = SessionLocal()
        try:
            return avaliar_todos_alertas(db)
        finally:
            db.close()

    if sincrono:
        return _run()
    background_tasks.add_task(_run)
    return {"status": "iniciado em background"}


# ===== Notificações =====

@router.get("/notificacoes")
def list_notificacoes(
    nao_lidas: bool = Query(False),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    q = db.query(Notificacao).filter(Notificacao.usuario_id == user.id)
    if nao_lidas:
        q = q.filter(Notificacao.lida == False)  # noqa: E712
    rows = q.order_by(desc(Notificacao.created_at)).limit(limit).all()
    return [
        {
            "id": n.id,
            "titulo": n.titulo,
            "mensagem": n.mensagem,
            "entidade_tipo": n.entidade_tipo,
            "entidade_id": n.entidade_id,
            "prioridade": n.prioridade,
            "lida": n.lida,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.get("/notificacoes/contagem")
def contagem_nao_lidas(db: Session = Depends(get_db), user=Depends(get_current_user)):
    n = db.query(Notificacao).filter(Notificacao.usuario_id == user.id, Notificacao.lida == False).count()  # noqa: E712
    return {"nao_lidas": n}


@router.post("/notificacoes/{notif_id}/marcar-lida")
def marcar_lida(
    notif_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    n = db.query(Notificacao).filter(Notificacao.id == notif_id, Notificacao.usuario_id == user.id).first()
    if not n:
        raise HTTPException(404, "Notificação não encontrada")
    n.lida = True
    n.lida_em = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/notificacoes/marcar-todas-lidas")
def marcar_todas_lidas(db: Session = Depends(get_db), user=Depends(get_current_user)):
    db.query(Notificacao).filter(
        Notificacao.usuario_id == user.id, Notificacao.lida == False  # noqa: E712
    ).update({"lida": True, "lida_em": datetime.utcnow()})
    db.commit()
    return {"ok": True}
