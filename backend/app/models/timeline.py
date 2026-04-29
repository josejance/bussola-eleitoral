from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class EventoTimeline(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "eventos_timeline"

    estado_id = Column(String(36), ForeignKey("estados.id"), index=True)
    pessoa_id = Column(String(36), ForeignKey("pessoas.id"), index=True)
    partido_id = Column(String(36), ForeignKey("partidos.id"))
    candidatura_id = Column(String(36), ForeignKey("candidaturas.id"))
    pesquisa_id = Column(String(36), ForeignKey("pesquisas.id"))
    materia_id = Column(String(36), ForeignKey("materias.id"))
    tipo = Column(String(40), nullable=False, index=True)
    titulo = Column(String(300), nullable=False)
    descricao = Column(Text)
    data_evento = Column(DateTime, nullable=False, index=True)
    fonte_url = Column(Text)
    fonte_descricao = Column(String(300))
    criado_por = Column(String(36), ForeignKey("perfis_usuario.id"))
    automatico = Column(Boolean, default=False)
    origem_automatica = Column(String(50))
    sensibilidade = Column(String(20), default="publico")
    relevancia = Column(Integer, default=3)


__all__ = ["EventoTimeline"]
