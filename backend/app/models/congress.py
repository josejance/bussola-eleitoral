from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class VotacaoCongresso(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "votacoes_congresso"

    casa = Column(String(20), nullable=False)  # camara/senado/congresso
    data = Column(Date, nullable=False, index=True)
    ementa = Column(Text, nullable=False)
    descricao_completa = Column(Text)
    tipo_proposicao = Column(String(20))
    numero = Column(Integer)
    ano = Column(Integer)
    posicionamento_governo = Column(String(30), default="desconhecido")
    classificacao_ia_sugerida = Column(String(30))
    classificacao_ia_confianca = Column(Numeric(3, 2))
    classificacao_aprovada_por = Column(String(36))
    tema = Column(String(30))
    resultado = Column(String(20))
    votos_sim = Column(Integer)
    votos_nao = Column(Integer)
    votos_abstencao = Column(Integer)
    url_oficial = Column(Text)
    ids_externos_json = Column(Text)


class VotoParlamentar(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "voto_parlamentar"

    votacao_id = Column(String(36), ForeignKey("votacoes_congresso.id"), nullable=False, index=True)
    pessoa_id = Column(String(36), ForeignKey("pessoas.id"), nullable=False, index=True)
    partido_id_no_voto = Column(String(36), ForeignKey("partidos.id"))
    estado_id = Column(String(36), ForeignKey("estados.id"))
    voto = Column(String(20), nullable=False)


class OrientacaoPartido(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "orientacoes_partido"

    votacao_id = Column(String(36), ForeignKey("votacoes_congresso.id"), nullable=False)
    partido_id = Column(String(36), ForeignKey("partidos.id"), nullable=False)
    orientacao = Column(String(20))


class Proposicao(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "proposicoes"

    ids_externos_json = Column(Text)
    casa = Column(String(20))
    tipo = Column(String(10))
    numero = Column(Integer)
    ano = Column(Integer)
    ementa = Column(Text)
    situacao_atual = Column(String(100))
    data_apresentacao = Column(Date)
    autores_principais_json = Column(Text)
    tema = Column(String(30))
    url_oficial = Column(Text)
    palavras_chave_json = Column(Text)


__all__ = ["VotacaoCongresso", "VotoParlamentar", "OrientacaoPartido", "Proposicao"]
