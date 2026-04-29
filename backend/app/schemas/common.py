from datetime import date, datetime

from pydantic import BaseModel


class EstadoOut(BaseModel):
    id: str
    sigla: str
    nome: str
    regiao: str
    populacao: int | None = None
    eleitorado_atual: int | None = None
    capital: str | None = None
    codigo_ibge: int | None = None

    class Config:
        from_attributes = True


class StatusEstadoOut(BaseModel):
    estado_id: str
    cenario_governador: str
    cenario_senado: str
    cenario_governador_detalhe: str | None = None
    cenario_senado_detalhe: str | None = None
    nivel_consolidacao: str
    prioridade_estrategica: int
    observacao_geral: str | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class StatusEstadoUpdate(BaseModel):
    cenario_governador: str | None = None
    cenario_senado: str | None = None
    cenario_governador_detalhe: str | None = None
    cenario_senado_detalhe: str | None = None
    nivel_consolidacao: str | None = None
    prioridade_estrategica: int | None = None
    observacao_geral: str | None = None


class PartidoOut(BaseModel):
    id: str
    sigla: str
    nome_completo: str
    numero_legenda: int | None = None
    espectro: str | None = None
    cor_hex: str | None = None
    ativo: bool

    class Config:
        from_attributes = True


class PessoaOut(BaseModel):
    id: str
    nome_completo: str
    nome_urna: str | None = None
    foto_url: str | None = None
    biografia: str | None = None

    class Config:
        from_attributes = True


class CandidaturaOut(BaseModel):
    id: str
    eleicao_id: str
    pessoa_id: str
    cargo: str
    partido_id: str
    estado_id: str | None = None
    numero_urna: int | None = None
    status_registro: str
    eh_titular: bool

    class Config:
        from_attributes = True


class PesquisaOut(BaseModel):
    id: str
    instituto_id: str
    registro_tse: str | None = None
    eleicao_id: str
    estado_id: str | None = None
    data_inicio_campo: date | None = None
    data_fim_campo: date | None = None
    data_divulgacao: date | None = None
    amostra: int | None = None
    margem_erro: float | None = None
    metodologia: str | None = None
    contratante: str | None = None
    tipo_cenario: str
    turno_referencia: int | None = None
    status_revisao: str

    class Config:
        from_attributes = True


class PesquisaCreate(BaseModel):
    instituto_id: str
    eleicao_id: str
    estado_id: str | None = None
    registro_tse: str | None = None
    data_inicio_campo: date | None = None
    data_fim_campo: date | None = None
    data_divulgacao: date | None = None
    amostra: int | None = None
    margem_erro: float | None = None
    nivel_confianca: float | None = None
    metodologia: str | None = None
    contratante: str | None = None
    tipo_cenario: str = "estimulado"
    turno_referencia: int | None = None
    observacao: str | None = None


class IntencaoVotoOut(BaseModel):
    id: str
    pesquisa_id: str
    nome_referencia: str | None = None
    percentual: float
    posicao_no_cenario: int | None = None

    class Config:
        from_attributes = True


class EventoTimelineOut(BaseModel):
    id: str
    estado_id: str | None = None
    pessoa_id: str | None = None
    partido_id: str | None = None
    tipo: str
    titulo: str
    descricao: str | None = None
    data_evento: datetime
    fonte_url: str | None = None
    fonte_descricao: str | None = None
    automatico: bool
    relevancia: int

    class Config:
        from_attributes = True


class EventoTimelineCreate(BaseModel):
    estado_id: str | None = None
    pessoa_id: str | None = None
    partido_id: str | None = None
    tipo: str
    titulo: str
    descricao: str | None = None
    data_evento: datetime
    fonte_url: str | None = None
    fonte_descricao: str | None = None
    relevancia: int = 3
    sensibilidade: str = "publico"


class NotaOut(BaseModel):
    id: str
    estado_id: str | None = None
    tema: str
    titulo: str
    conteudo: str
    autor_id: str
    sensibilidade: str
    acao_requerida: bool
    versao: int
    created_at: datetime

    class Config:
        from_attributes = True


class NotaCreate(BaseModel):
    estado_id: str | None = None
    pessoa_relacionada_id: str | None = None
    partido_relacionado_id: str | None = None
    tema: str
    titulo: str
    conteudo: str
    sensibilidade: str = "interno"
    fonte_tipo: str | None = None
    fonte_referencia: str | None = None
    fonte_url: str | None = None
    data_evento: date | None = None
    acao_requerida: bool = False


class MateriaOut(BaseModel):
    id: str
    fonte_id: str
    titulo: str
    snippet: str | None = None
    autor: str | None = None
    data_publicacao: datetime
    url: str
    imagem_url: str | None = None

    class Config:
        from_attributes = True
