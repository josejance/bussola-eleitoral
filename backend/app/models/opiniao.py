"""Modelos para pesquisas de opinião sobre temas (não-eleitorais).

Ex: apostas esportivas, Copa do Mundo, ética no STF, imposto de renda,
Venezuela, urnas eletrônicas. Diferente de Pesquisa eleitoral, não está
vinculada a uma eleição/cargo, mas sim a um tema/tópico.
"""
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class PesquisaTematica(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pesquisas_tematicas"

    instituto_id = Column(String(36), ForeignKey("institutos_pesquisa.id"), nullable=False, index=True)
    titulo = Column(String(300), nullable=False)
    subtitulo = Column(String(300))
    tema = Column(String(50), nullable=False, index=True)  # apostas/copa/stf/imposto/venezuela/urnas/imagem/ etc.
    abrangencia = Column(String(20), default="nacional")  # nacional/regional/estadual
    estado_id = Column(String(36), ForeignKey("estados.id"))  # se estadual
    data_inicio_campo = Column(Date)
    data_fim_campo = Column(Date, index=True)
    data_divulgacao = Column(Date)
    amostra = Column(Integer)
    margem_erro = Column(Numeric(4, 2))
    nivel_confianca = Column(Numeric(4, 2))
    metodologia = Column(String(50))
    contratante = Column(String(200))
    registro_eleitoral = Column(String(50))  # opcional, alguns institutos registram mesmo sem ser eleitoral
    publico_alvo = Column(Text)
    observacao = Column(Text)
    palavras_chave_json = Column(Text)  # ['apostas', 'esportivas', 'jovens']


class PesquisaTematicaQuestao(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "pesquisa_tematica_questoes"

    pesquisa_id = Column(String(36), ForeignKey("pesquisas_tematicas.id"), nullable=False, index=True)
    numero = Column(Integer, nullable=False)  # ordem
    titulo_questao = Column(String(500))
    enunciado = Column(Text)
    tipo_resposta = Column(String(30))  # multipla_escolha/escala/binaria/aberta
    dados_gerais_json = Column(Text)  # [{opcao, percentual}, ...]
    cruzamentos_json = Column(Text)  # {por_sexo: [...], por_idade: [...]}


class PesquisaTematicaDadosBrutos(Base, UUIDMixin, TimestampMixin):
    """Backup do JSON original importado, para reprocessamento."""

    __tablename__ = "pesquisas_tematicas_dados_brutos"

    pesquisa_id = Column(String(36), ForeignKey("pesquisas_tematicas.id"), unique=True, nullable=False)
    formato_origem = Column(String(50))
    dados_json = Column(Text, nullable=False)
    arquivo_origem = Column(String(300))
    importado_por = Column(String(36), ForeignKey("perfis_usuario.id"))
    importado_em = Column(DateTime)
    analise_ia_json = Column(Text)


__all__ = ["PesquisaTematica", "PesquisaTematicaQuestao", "PesquisaTematicaDadosBrutos"]
