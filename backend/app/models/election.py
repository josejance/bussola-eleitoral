from sqlalchemy import BigInteger, Boolean, Column, Date, ForeignKey, Integer, Numeric, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class Eleicao(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "eleicoes"

    ano = Column(Integer, nullable=False, index=True)
    turno = Column(Integer, nullable=False)
    tipo = Column(String(30), nullable=False)  # municipal/estadual_geral/etc
    data = Column(Date)
    estado_id = Column(String(36), ForeignKey("estados.id"))
    municipio_id = Column(String(36), ForeignKey("municipios.id"))
    descricao = Column(String(200))


class Candidatura(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidaturas"

    eleicao_id = Column(String(36), ForeignKey("eleicoes.id"), nullable=False, index=True)
    pessoa_id = Column(String(36), ForeignKey("pessoas.id"), nullable=False, index=True)
    cargo = Column(String(50), nullable=False)
    partido_id = Column(String(36), ForeignKey("partidos.id"), nullable=False, index=True)
    federacao_id = Column(String(36), ForeignKey("federacoes_partidarias.id"))
    estado_id = Column(String(36), ForeignKey("estados.id"), index=True)
    municipio_id = Column(String(36), ForeignKey("municipios.id"))
    numero_urna = Column(Integer)
    status_registro = Column(String(30), default="pre_candidatura")
    eh_titular = Column(Boolean, default=True)
    titular_id = Column(String(36), ForeignKey("candidaturas.id"))
    ordem_chapa = Column(Integer)
    data_registro_tse = Column(Date)
    observacao = Column(Text)


class Coligacao(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "coligacoes"

    eleicao_id = Column(String(36), ForeignKey("eleicoes.id"), nullable=False)
    estado_id = Column(String(36), ForeignKey("estados.id"))
    cargo = Column(String(50), nullable=False)
    nome = Column(String(200))
    status = Column(String(30), default="em_negociacao")
    data_anuncio = Column(Date)
    observacao = Column(Text)


class ColigacaoPartido(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "coligacao_partidos"

    coligacao_id = Column(String(36), ForeignKey("coligacoes.id"), nullable=False)
    partido_id = Column(String(36), ForeignKey("partidos.id"), nullable=False)
    papel = Column(String(30))
    confirmacao = Column(String(30))
    data_status = Column(Date)
    observacao = Column(Text)


class ResultadoEleitoral(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resultados_eleitorais"

    eleicao_id = Column(String(36), ForeignKey("eleicoes.id"), nullable=False, index=True)
    candidatura_id = Column(String(36), ForeignKey("candidaturas.id"), nullable=False)
    estado_id = Column(String(36), ForeignKey("estados.id"), index=True)
    municipio_id = Column(String(36), ForeignKey("municipios.id"))
    zona_eleitoral = Column(Integer)
    votos = Column(BigInteger, default=0)
    percentual_validos = Column(Numeric(5, 2))
    eleito = Column(Boolean, default=False)
    suplente = Column(Boolean, default=False)
    posicao = Column(Integer)


class VotacaoPartidoEstado(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "votacao_partido_estado"

    eleicao_id = Column(String(36), ForeignKey("eleicoes.id"), nullable=False, index=True)
    partido_id = Column(String(36), ForeignKey("partidos.id"), nullable=False, index=True)
    federacao_id = Column(String(36), ForeignKey("federacoes_partidarias.id"))
    estado_id = Column(String(36), ForeignKey("estados.id"), nullable=False, index=True)
    cargo = Column(String(50), nullable=False)
    votos_totais = Column(BigInteger, default=0)
    percentual_total = Column(Numeric(5, 2))
    bancada_eleita = Column(Integer, default=0)
    votos_legenda = Column(BigInteger)
    votos_nominais = Column(BigInteger)


__all__ = [
    "Eleicao",
    "Candidatura",
    "Coligacao",
    "ColigacaoPartido",
    "ResultadoEleitoral",
    "VotacaoPartidoEstado",
]
