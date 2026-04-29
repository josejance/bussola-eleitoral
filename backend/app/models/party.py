from sqlalchemy import Boolean, Column, Date, Integer, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class Partido(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "partidos"

    sigla = Column(String(20), unique=True, nullable=False, index=True)
    nome_completo = Column(String(200), nullable=False)
    numero_legenda = Column(Integer)
    fundacao = Column(Date)
    espectro = Column(String(30))  # extrema_esquerda/esquerda/centro_esquerda/centro/centro_direita/direita/extrema_direita
    espectro_economico = Column(String(30))
    espectro_social = Column(String(30))
    ativo = Column(Boolean, default=True)
    logo_url = Column(Text)
    cor_hex = Column(String(7))
    descricao = Column(Text)


class FederacaoPartidaria(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "federacoes_partidarias"

    nome = Column(String(200), nullable=False)
    sigla = Column(String(50))
    partidos_ids_json = Column(Text)  # JSON array de UUID
    inicio_vigencia = Column(Date)
    fim_vigencia = Column(Date)
    numero_legenda = Column(Integer)


__all__ = ["Partido", "FederacaoPartidaria"]
