from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class FonteRSS(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "fontes_rss"

    nome = Column(String(150), nullable=False)
    url_feed = Column(Text, nullable=False)
    url_site = Column(Text)
    tipo = Column(String(30))
    abrangencia = Column(String(20))  # nacional/regional/estadual
    estados_cobertos_json = Column(Text)
    espectro_editorial = Column(String(30))
    confiabilidade = Column(Integer, default=3)
    peso_editorial = Column(Integer, default=3)
    frequencia_polling_minutos = Column(Integer, default=15)
    ativo = Column(Boolean, default=True)
    ultimo_polling = Column(DateTime)
    ultimo_sucesso = Column(DateTime)
    total_materias_capturadas = Column(Integer, default=0)
    total_materias_aproveitadas = Column(Integer, default=0)
    observacao = Column(Text)


class Materia(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "materias"

    fonte_id = Column(String(36), ForeignKey("fontes_rss.id"), nullable=False, index=True)
    titulo = Column(String(500), nullable=False)
    snippet = Column(Text)
    conteudo_completo = Column(Text)
    autor = Column(String(150))
    data_publicacao = Column(DateTime, nullable=False, index=True)
    data_captura = Column(DateTime)
    url = Column(Text, unique=True, nullable=False)
    url_canonical = Column(Text)
    hash_url = Column(String(64), index=True)
    hash_conteudo = Column(String(64))
    imagem_url = Column(Text)
    categoria_origem = Column(String(100))
    processada_filtro = Column(Boolean, default=False)
    processada_ia = Column(Boolean, default=False)
    aproveitada = Column(Boolean, default=False)
    motivo_descarte = Column(Text)


class MateriaMetadata(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "materia_metadata"

    materia_id = Column(String(36), ForeignKey("materias.id"), unique=True, nullable=False)
    relevancia_estrategica = Column(Integer)
    resumo_ia = Column(Text)
    sentimento_geral_pt = Column(Integer)
    sentimento_geral_lula = Column(Integer)
    sentimento_geral_governo = Column(Integer)
    narrativas_detectadas_json = Column(Text)
    processado_em = Column(DateTime)
    modelo_usado = Column(String(50))
    tokens_consumidos = Column(Integer)
    custo_centavos = Column(Integer)


class MateriaEstado(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "materia_estados"

    materia_id = Column(String(36), ForeignKey("materias.id"), nullable=False, index=True)
    estado_id = Column(String(36), ForeignKey("estados.id"), nullable=False, index=True)
    relevancia_para_estado = Column(Integer)


class MateriaPessoa(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "materia_pessoas"

    materia_id = Column(String(36), ForeignKey("materias.id"), nullable=False, index=True)
    pessoa_id = Column(String(36), ForeignKey("pessoas.id"), nullable=False, index=True)
    contexto = Column(Text)
    sentimento = Column(Integer)
    eh_protagonista = Column(Boolean, default=False)


class MateriaPartido(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "materia_partidos"

    materia_id = Column(String(36), ForeignKey("materias.id"), nullable=False)
    partido_id = Column(String(36), ForeignKey("partidos.id"), nullable=False)
    contexto = Column(Text)
    sentimento = Column(Integer)
    eh_protagonista = Column(Boolean, default=False)


class NarrativaDetectada(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "narrativas_detectadas"

    titulo = Column(String(300), nullable=False)
    descricao = Column(Text)
    primeira_aparicao = Column(DateTime)
    ultima_aparicao = Column(DateTime)
    total_materias = Column(Integer, default=0)
    espectros_envolvidos_json = Column(Text)
    pessoas_centrais_json = Column(Text)
    partidos_centrais_json = Column(Text)
    estados_envolvidos_json = Column(Text)
    tendencia = Column(String(20))  # emergente/em_alta/estavel/em_queda/extinta
    score_amplificacao = Column(Numeric(8, 2))
    classificacao = Column(String(20))  # favoravel/neutra/adversa


__all__ = [
    "FonteRSS",
    "Materia",
    "MateriaMetadata",
    "MateriaEstado",
    "MateriaPessoa",
    "MateriaPartido",
    "NarrativaDetectada",
]
