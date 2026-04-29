from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text

from app.models.base import Base, TimestampMixin, UUIDMixin


class StatusPTEstado(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "status_pt_estado"

    estado_id = Column(String(36), ForeignKey("estados.id"), unique=True, nullable=False)
    eleicao_id = Column(String(36), ForeignKey("eleicoes.id"))
    cenario_governador = Column(String(30), default="indefinido")
    cenario_senado = Column(String(30), default="indefinido")
    cenario_governador_detalhe = Column(Text)
    cenario_senado_detalhe = Column(Text)
    nivel_consolidacao = Column(String(20), default="em_construcao")
    prioridade_estrategica = Column(Integer, default=3)  # 1-5
    meta_bancada_federal = Column(Integer)
    meta_bancada_estadual = Column(Integer)
    observacao_geral = Column(Text)
    atualizado_por = Column(String(36))


class NotaEditorial(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notas_editoriais"

    estado_id = Column(String(36), ForeignKey("estados.id"))
    pessoa_relacionada_id = Column(String(36), ForeignKey("pessoas.id"))
    partido_relacionado_id = Column(String(36), ForeignKey("partidos.id"))
    tema = Column(String(30), nullable=False)
    titulo = Column(String(200), nullable=False)
    conteudo = Column(Text, nullable=False)
    autor_id = Column(String(36), ForeignKey("perfis_usuario.id"), nullable=False)
    fonte_tipo = Column(String(30))
    fonte_referencia = Column(Text)
    fonte_url = Column(Text)
    data_evento = Column(Date)
    sensibilidade = Column(String(20), default="interno")  # publico/interno/restrito_direcao
    tags_json = Column(Text)
    acao_requerida = Column(Boolean, default=False)
    atribuida_a = Column(String(36), ForeignKey("perfis_usuario.id"))
    prazo_acao = Column(Date)
    versao = Column(Integer, default=1)
    nota_anterior_id = Column(String(36), ForeignKey("notas_editoriais.id"))
    publicada_como_evento = Column(Boolean, default=False)


class Tarefa(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tarefas"

    titulo = Column(String(200), nullable=False)
    descricao = Column(Text)
    criada_por = Column(String(36), ForeignKey("perfis_usuario.id"), nullable=False)
    atribuida_a = Column(String(36), ForeignKey("perfis_usuario.id"))
    estado_id = Column(String(36), ForeignKey("estados.id"))
    pessoa_relacionada_id = Column(String(36), ForeignKey("pessoas.id"))
    nota_origem_id = Column(String(36), ForeignKey("notas_editoriais.id"))
    evento_origem_id = Column(String(36), ForeignKey("eventos_timeline.id"))
    prioridade = Column(String(20), default="media")
    status = Column(String(20), default="pendente")
    prazo = Column(Date)
    concluida_em = Column(DateTime)


class Comentario(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "comentarios"

    entidade_tipo = Column(String(30), nullable=False)
    entidade_id = Column(String(36), nullable=False, index=True)
    autor_id = Column(String(36), ForeignKey("perfis_usuario.id"), nullable=False)
    conteudo = Column(Text, nullable=False)
    parent_id = Column(String(36), ForeignKey("comentarios.id"))
    editado_em = Column(DateTime)


__all__ = ["StatusPTEstado", "NotaEditorial", "Tarefa", "Comentario"]
