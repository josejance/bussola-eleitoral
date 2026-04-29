"""Motor de avaliação de alertas.

Para cada Alerta ativo, verifica se a condição configurada disparou
desde o último_disparo e cria Notificacao quando aplicável.

Tipos suportados (MVP):
- pesquisa: nova pesquisa em estado/cargo / mudança de liderança
- movimentacao_politica: nova candidatura, mudança de partido
- midia: nova matéria mencionando entidade
- editorial: nova nota editorial com tag X / acao_requerida

Roda periodicamente via APScheduler (a cada 5min).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Alerta,
    EventoTimeline,
    Materia,
    MateriaPessoa,
    MateriaPartido,
    MateriaEstado,
    Notificacao,
    Pesquisa,
)
from app.models.editorial import NotaEditorial

logger = logging.getLogger("alertas_engine")


def _criar_notificacao(
    db: Session,
    alerta: Alerta,
    titulo: str,
    mensagem: str,
    entidade_tipo: str,
    entidade_id: str,
    prioridade: str = "media",
):
    db.add(
        Notificacao(
            usuario_id=alerta.usuario_id,
            alerta_id=alerta.id,
            titulo=titulo,
            mensagem=mensagem,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            prioridade=prioridade,
        )
    )
    alerta.total_disparos = (alerta.total_disparos or 0) + 1


def _avaliar_alerta_pesquisa(db: Session, alerta: Alerta, ultimo_disparo: datetime, agora: datetime) -> int:
    """Pesquisa: nova pesquisa publicada em estado(s) configurados."""
    config = json.loads(alerta.configuracao_json or "{}")
    estados_ids = config.get("estados_ids") or []
    cargos = config.get("cargos") or []

    q = db.query(Pesquisa).filter(Pesquisa.created_at >= ultimo_disparo)
    if estados_ids:
        q = q.filter(Pesquisa.estado_id.in_(estados_ids))
    novas = q.all()

    n = 0
    for p in novas:
        from app.models import Estado, InstitutoPesquisa
        estado = db.query(Estado).filter(Estado.id == p.estado_id).first() if p.estado_id else None
        instituto = db.query(InstitutoPesquisa).filter(InstitutoPesquisa.id == p.instituto_id).first()
        local = estado.sigla if estado else "Brasil"
        _criar_notificacao(
            db,
            alerta,
            titulo=f"Nova pesquisa em {local}",
            mensagem=f"{instituto.nome if instituto else 'Pesquisa'} divulgou pesquisa em {local}",
            entidade_tipo="pesquisa",
            entidade_id=p.id,
            prioridade="alta",
        )
        n += 1
    return n


def _avaliar_alerta_movimentacao(db: Session, alerta: Alerta, ultimo_disparo: datetime, agora: datetime) -> int:
    """Movimentação política: novos eventos de filiação/candidatura."""
    config = json.loads(alerta.configuracao_json or "{}")
    tipos = config.get("tipos") or ["filiacao", "desfiliacao", "anuncio_candidatura", "registro_candidatura"]
    estados_ids = config.get("estados_ids") or []

    q = db.query(EventoTimeline).filter(
        EventoTimeline.created_at >= ultimo_disparo,
        EventoTimeline.tipo.in_(tipos),
    )
    if estados_ids:
        q = q.filter(EventoTimeline.estado_id.in_(estados_ids))

    eventos = q.all()
    for e in eventos:
        _criar_notificacao(
            db,
            alerta,
            titulo=e.titulo[:200],
            mensagem=e.descricao[:500] if e.descricao else "",
            entidade_tipo="evento",
            entidade_id=e.id,
            prioridade="alta" if e.relevancia >= 4 else "media",
        )
    return len(eventos)


def _avaliar_alerta_midia(db: Session, alerta: Alerta, ultimo_disparo: datetime, agora: datetime) -> int:
    """Mídia: nova matéria mencionando pessoa/partido/estado configurado."""
    config = json.loads(alerta.configuracao_json or "{}")
    pessoa_ids = config.get("pessoa_ids") or []
    partido_ids = config.get("partido_ids") or []
    estado_ids = config.get("estado_ids") or []
    relevancia_min = config.get("relevancia_min", 3)

    materias_ids: set[str] = set()
    if pessoa_ids:
        rows = (
            db.query(MateriaPessoa.materia_id)
            .filter(MateriaPessoa.pessoa_id.in_(pessoa_ids))
            .all()
        )
        materias_ids.update(r[0] for r in rows)
    if partido_ids:
        rows = (
            db.query(MateriaPartido.materia_id)
            .filter(MateriaPartido.partido_id.in_(partido_ids))
            .all()
        )
        materias_ids.update(r[0] for r in rows)
    if estado_ids:
        rows = (
            db.query(MateriaEstado.materia_id)
            .filter(MateriaEstado.estado_id.in_(estado_ids))
            .all()
        )
        materias_ids.update(r[0] for r in rows)

    if not materias_ids:
        return 0

    q = (
        db.query(Materia)
        .filter(Materia.id.in_(list(materias_ids)))
        .filter(Materia.data_captura >= ultimo_disparo)
        .filter(Materia.aproveitada == True)  # noqa: E712
        .limit(50)
    )
    materias = q.all()
    n = 0
    for m in materias:
        _criar_notificacao(
            db,
            alerta,
            titulo=m.titulo[:200],
            mensagem=(m.snippet or "")[:300],
            entidade_tipo="materia",
            entidade_id=m.id,
            prioridade="media",
        )
        n += 1
    return n


def _avaliar_alerta_editorial(db: Session, alerta: Alerta, ultimo_disparo: datetime, agora: datetime) -> int:
    """Editorial: nova nota com tag/sensibilidade específica."""
    config = json.loads(alerta.configuracao_json or "{}")
    sensibilidades = config.get("sensibilidades") or ["interno", "restrito_direcao"]
    apenas_acao_requerida = config.get("apenas_acao_requerida", False)

    q = db.query(NotaEditorial).filter(
        NotaEditorial.created_at >= ultimo_disparo,
        NotaEditorial.sensibilidade.in_(sensibilidades),
    )
    if apenas_acao_requerida:
        q = q.filter(NotaEditorial.acao_requerida == True)  # noqa: E712

    notas = q.all()
    for n in notas:
        _criar_notificacao(
            db,
            alerta,
            titulo=f"Nova nota: {n.titulo[:150]}",
            mensagem=f"Tema: {n.tema} · Sensibilidade: {n.sensibilidade}",
            entidade_tipo="nota",
            entidade_id=n.id,
            prioridade="alta" if n.acao_requerida else "media",
        )
    return len(notas)


AVALIADORES = {
    "pesquisa": _avaliar_alerta_pesquisa,
    "movimentacao_politica": _avaliar_alerta_movimentacao,
    "midia": _avaliar_alerta_midia,
    "editorial": _avaliar_alerta_editorial,
}


def avaliar_todos_alertas(db: Session) -> dict:
    """Roda avaliação de todos os alertas ativos."""
    agora = datetime.utcnow()
    alertas = db.query(Alerta).filter(Alerta.ativo == True).all()  # noqa: E712

    sumario = {"alertas_avaliados": len(alertas), "notificacoes_criadas": 0, "por_tipo": {}}

    for alerta in alertas:
        ultimo_disparo = alerta.ultimo_disparo or (agora - timedelta(hours=24))
        avaliador = AVALIADORES.get(alerta.tipo)
        if not avaliador:
            continue
        try:
            n = avaliador(db, alerta, ultimo_disparo, agora)
            if n > 0:
                alerta.ultimo_disparo = agora
                sumario["notificacoes_criadas"] += n
                sumario["por_tipo"][alerta.tipo] = sumario["por_tipo"].get(alerta.tipo, 0) + n
        except Exception as e:
            logger.warning(f"Erro avaliando alerta {alerta.id} ({alerta.tipo}): {e}")

    db.commit()
    return sumario
