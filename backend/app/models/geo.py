from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Estado(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "estados"

    sigla = Column(String(2), unique=True, nullable=False, index=True)
    nome = Column(String(100), nullable=False)
    regiao = Column(String(20), nullable=False)
    populacao = Column(Integer)
    eleitorado_atual = Column(Integer)
    capital = Column(String(100))
    codigo_ibge = Column(Integer, unique=True)

    municipios = relationship("Municipio", back_populates="estado", cascade="all, delete-orphan")


class Municipio(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "municipios"

    estado_id = Column(String(36), ForeignKey("estados.id"), nullable=False, index=True)
    nome = Column(String(150), nullable=False)
    codigo_ibge = Column(Integer, unique=True)
    eh_capital = Column(Boolean, default=False)
    populacao = Column(Integer)
    eleitorado = Column(Integer)

    estado = relationship("Estado", back_populates="municipios")


__all__ = ["Estado", "Municipio"]
