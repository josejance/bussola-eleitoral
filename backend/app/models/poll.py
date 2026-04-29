from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text  # noqa

from app.models.base import Base, TimestampMixin, UUIDMixin


class InstitutoPesquisa(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "institutos_pesquisa"

    nome = Column(String(150), nullable=False, index=True)
    sigla = Column(String(30))
    site = Column(Text)
    cnpj_hash = Column(String(64))
    confiabilidade_score = Column(Integer, default=3)  # 1-5
    historico_acerto_json = Column(Text)
    vies_historico_json = Column(Text)
    ativo = Column(Boolean, default=True)
    descricao = Column(Text)


class Pesquisa(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pesquisas"

    instituto_id = Column(String(36), ForeignKey("institutos_pesquisa.id"), nullable=False, index=True)
    registro_tse = Column(String(50), index=True)
    eleicao_id = Column(String(36), ForeignKey("eleicoes.id"), nullable=False)
    estado_id = Column(String(36), ForeignKey("estados.id"), index=True)
    municipio_id = Column(String(36), ForeignKey("municipios.id"))
    abrangencia = Column(String(20), default="estadual")
    data_inicio_campo = Column(Date)
    data_fim_campo = Column(Date, index=True)
    data_divulgacao = Column(Date)
    amostra = Column(Integer)
    margem_erro = Column(Numeric(4, 2))
    nivel_confianca = Column(Numeric(4, 2))
    metodologia = Column(String(20))  # presencial/telefonica/online/mista/painel
    contratante = Column(String(200))
    custo_declarado = Column(Numeric(15, 2))
    url_relatorio = Column(Text)
    url_pdf_storage = Column(Text)
    tipo_cenario = Column(String(20), default="estimulado")
    turno_referencia = Column(Integer)
    origem_dado = Column(String(30), default="insercao_manual")
    status_revisao = Column(String(20), default="aprovada")
    observacao = Column(Text)
    anunciada_antes_do_registro = Column(Boolean, default=False)


class IntencaoVoto(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "intencoes_voto"

    pesquisa_id = Column(String(36), ForeignKey("pesquisas.id"), nullable=False, index=True)
    candidatura_id = Column(String(36), ForeignKey("candidaturas.id"))
    pessoa_id = Column(String(36), ForeignKey("pessoas.id"))
    nome_referencia = Column(String(150))
    partido_referencia_id = Column(String(36), ForeignKey("partidos.id"))
    percentual = Column(Numeric(5, 2), nullable=False)
    recorte_json = Column(Text)
    posicao_no_cenario = Column(Integer)


class AvaliacaoGoverno(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "avaliacao_governo"

    pesquisa_id = Column(String(36), ForeignKey("pesquisas.id"), nullable=False)
    nivel = Column(String(20), nullable=False)  # presidencial/estadual/municipal
    pessoa_avaliada_id = Column(String(36), ForeignKey("pessoas.id"))
    cargo_avaliado = Column(String(50))
    periodo_referencia = Column(Date)  # para séries históricas dentro da mesma pesquisa
    otimo_bom = Column(Numeric(5, 2))
    regular = Column(Numeric(5, 2))
    ruim_pessimo = Column(Numeric(5, 2))
    nao_sabe = Column(Numeric(5, 2))
    aprova = Column(Numeric(5, 2))
    desaprova = Column(Numeric(5, 2))
    confianca = Column(Numeric(5, 2))


class PesquisaDadosBrutos(Base, UUIDMixin, TimestampMixin):
    """Armazena o JSON original da pesquisa (importação Quaest, etc.) + análise IA."""

    __tablename__ = "pesquisas_dados_brutos"

    pesquisa_id = Column(String(36), ForeignKey("pesquisas.id"), unique=True, nullable=False, index=True)
    formato_origem = Column(String(50))  # "quaest_json", "outro_json", "pdf_extraido"
    dados_json = Column(Text, nullable=False)  # JSON completo serializado
    analise_ia_json = Column(Text)  # Resultado da análise via Claude
    importado_por = Column(String(36), ForeignKey("perfis_usuario.id"))
    importado_em = Column(DateTime)


class AgregadoPesquisa(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agregados_pesquisas"

    estado_id = Column(String(36), ForeignKey("estados.id"))
    eleicao_id = Column(String(36), ForeignKey("eleicoes.id"), nullable=False)
    cargo = Column(String(50), nullable=False)
    cenario = Column(String(20))
    candidato_id = Column(String(36), ForeignKey("candidaturas.id"))
    data_calculo = Column(DateTime)
    estimativa_atual = Column(Numeric(5, 2))
    banda_inferior_95 = Column(Numeric(5, 2))
    banda_superior_95 = Column(Numeric(5, 2))
    tendencia_30d = Column(Numeric(5, 2))
    pesquisas_consideradas = Column(Integer)
    peso_total = Column(Numeric(10, 2))


__all__ = [
    "InstitutoPesquisa",
    "Pesquisa",
    "IntencaoVoto",
    "AvaliacaoGoverno",
    "PesquisaDadosBrutos",
    "AgregadoPesquisa",
]
