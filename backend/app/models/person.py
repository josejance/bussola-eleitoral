from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class Pessoa(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pessoas"

    nome_completo = Column(String(200), nullable=False, index=True)
    nome_urna = Column(String(100), index=True)
    cpf_hash = Column(String(64), unique=True)
    titulo_eleitor_hash = Column(String(64), unique=True)
    nascimento = Column(Date)
    genero = Column(String(20))
    raca_cor = Column(String(30))
    estado_natal_id = Column(String(36), ForeignKey("estados.id"))
    foto_url = Column(Text)
    biografia = Column(Text)
    email_publico = Column(String(150))
    telefones_json = Column(Text)
    redes_sociais_json = Column(Text)  # JSON: {twitter, instagram, etc}
    site_pessoal = Column(Text)
    ids_externos_json = Column(Text)  # JSON: {tse, camara, senado, wikidata}
    profissoes_json = Column(Text)
    escolaridade = Column(String(50))
    patrimonio_declarado = Column(Numeric(18, 2))
    deleted_at = Column(DateTime)


class FiliacaoPartidaria(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "filiacoes_partidarias"

    pessoa_id = Column(String(36), ForeignKey("pessoas.id"), nullable=False, index=True)
    partido_id = Column(String(36), ForeignKey("partidos.id"), nullable=False, index=True)
    inicio = Column(Date, nullable=False)
    fim = Column(Date)
    motivo_saida = Column(Text)
    tipo_saida = Column(String(30))
    cargo_partidario = Column(String(50))


class Mandato(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "mandatos"

    pessoa_id = Column(String(36), ForeignKey("pessoas.id"), nullable=False, index=True)
    cargo = Column(String(50), nullable=False)
    estado_id = Column(String(36), ForeignKey("estados.id"))
    municipio_id = Column(String(36), ForeignKey("municipios.id"))
    partido_id_no_mandato = Column(String(36), ForeignKey("partidos.id"))
    federacao_id_no_mandato = Column(String(36), ForeignKey("federacoes_partidarias.id"))
    inicio = Column(Date, nullable=False)
    fim = Column(Date, nullable=False)
    eh_suplente = Column(Boolean, default=False)
    eh_titular = Column(Boolean, default=True)
    assumiu_em = Column(Date)
    eleicao_origem_id = Column(String(36), ForeignKey("eleicoes.id"))
    observacao = Column(Text)


class SuplenteSenado(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "suplentes_senado"

    senador_pessoa_id = Column(String(36), ForeignKey("pessoas.id"), nullable=False)
    suplente_pessoa_id = Column(String(36), ForeignKey("pessoas.id"), nullable=False)
    ordem = Column(String(2))  # "1" ou "2"
    eleicao_id = Column(String(36), ForeignKey("eleicoes.id"))
    em_exercicio = Column(Boolean, default=False)
    inicio_exercicio = Column(Date)
    fim_exercicio = Column(Date)


__all__ = ["Pessoa", "FiliacaoPartidaria", "Mandato", "SuplenteSenado"]
