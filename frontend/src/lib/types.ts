export type Papel =
  | "admin"
  | "editor_nacional"
  | "editor_estadual"
  | "leitor_pleno"
  | "leitor_publico";

export interface User {
  id: string;
  email: string;
  nome_completo: string;
  nome_exibicao?: string | null;
  papel: Papel;
  estado_referencia_id?: string | null;
  ativo: boolean;
}

export interface Estado {
  id: string;
  sigla: string;
  nome: string;
  regiao: string;
  populacao?: number | null;
  eleitorado_atual?: number | null;
  capital?: string | null;
  codigo_ibge?: number | null;
}

export type NivelConsolidacao = "consolidado" | "em_construcao" | "disputado" | "adverso";
export type CenarioGov =
  | "candidatura_propria"
  | "vice_aliado"
  | "apoio_sem_cargo"
  | "oposicao"
  | "indefinido";

export interface StatusEstado {
  estado_id: string;
  cenario_governador: CenarioGov;
  cenario_senado: CenarioGov;
  cenario_governador_detalhe?: string | null;
  cenario_senado_detalhe?: string | null;
  nivel_consolidacao: NivelConsolidacao;
  prioridade_estrategica: number;
  observacao_geral?: string | null;
  updated_at?: string | null;
}

export interface Partido {
  id: string;
  sigla: string;
  nome_completo: string;
  numero_legenda?: number | null;
  espectro?: string | null;
  cor_hex?: string | null;
  ativo: boolean;
}

export interface Pesquisa {
  id: string;
  instituto_id: string;
  registro_tse?: string | null;
  eleicao_id: string;
  estado_id?: string | null;
  abrangencia?: string | null;
  data_inicio_campo?: string | null;
  data_fim_campo?: string | null;
  data_divulgacao?: string | null;
  amostra?: number | null;
  margem_erro?: number | null;
  metodologia?: string | null;
  contratante?: string | null;
  tipo_cenario: string;
  turno_referencia?: number | null;
  status_revisao: string;
}

export interface Evento {
  id: string;
  estado_id?: string | null;
  pessoa_id?: string | null;
  partido_id?: string | null;
  tipo: string;
  titulo: string;
  descricao?: string | null;
  data_evento: string;
  fonte_url?: string | null;
  fonte_descricao?: string | null;
  automatico: boolean;
  relevancia: number;
}

export interface Nota {
  id: string;
  estado_id?: string | null;
  tema: string;
  titulo: string;
  conteudo: string;
  autor_id: string;
  sensibilidade: string;
  acao_requerida: boolean;
  versao: number;
  created_at: string;
}

export interface Materia {
  id: string;
  fonte_id: string;
  titulo: string;
  snippet?: string | null;
  autor?: string | null;
  data_publicacao: string;
  url: string;
  imagem_url?: string | null;
}
