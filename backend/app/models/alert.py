from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class Alerta(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alertas"

    usuario_id = Column(String(36), ForeignKey("perfis_usuario.id"), nullable=False, index=True)
    nome = Column(String(200), nullable=False)
    tipo = Column(String(30), nullable=False)
    configuracao_json = Column(Text, nullable=False)
    canais_json = Column(Text)  # ['in_app', 'email', 'push']
    ativo = Column(Boolean, default=True)
    frequencia_max = Column(String(20), default="imediato")
    ultimo_disparo = Column(DateTime)
    total_disparos = Column(Integer, default=0)


class Notificacao(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notificacoes"

    usuario_id = Column(String(36), ForeignKey("perfis_usuario.id"), nullable=False, index=True)
    alerta_id = Column(String(36), ForeignKey("alertas.id"))
    titulo = Column(String(300), nullable=False)
    mensagem = Column(Text)
    entidade_tipo = Column(String(50))
    entidade_id = Column(String(36))
    prioridade = Column(String(20), default="media")
    lida = Column(Boolean, default=False)
    lida_em = Column(DateTime)
    expira_em = Column(DateTime)


class AuditLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_log"

    tabela = Column(String(50), nullable=False)
    registro_id = Column(String(36), nullable=False)
    acao = Column(String(20), nullable=False)
    payload_anterior_json = Column(Text)
    payload_novo_json = Column(Text)
    usuario_id = Column(String(36), ForeignKey("perfis_usuario.id"))
    ip = Column(String(45))
    user_agent = Column(Text)
    justificativa = Column(Text)


__all__ = ["Alerta", "Notificacao", "AuditLog"]
