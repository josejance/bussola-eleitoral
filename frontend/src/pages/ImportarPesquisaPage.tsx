import { useState, ChangeEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  Bot,
  CheckCircle2,
  ExternalLink,
  FileJson,
  Sparkles,
  Upload,
} from "lucide-react";

import { api } from "../lib/api";

const EXEMPLO_JSON = `{
  "pesquisa": {
    "identificacao": {
      "titulo": "Pesquisa X",
      "local": "Bahia",
      "periodo": {
        "data_coleta_inicio": "2026-04-23",
        "data_coleta_fim": "2026-04-27"
      },
      "instituicoes": {
        "contratante": "Cliente",
        "executora": "Quaest"
      },
      "registro_eleitoral": {
        "numero": "BA-XXXXX/2026",
        "data_registro": "2026-04-23"
      }
    },
    "especificacoes_tecnicas": {
      "amostra": {
        "total_entrevistas": 1200,
        "margem_erro_maxima": 3,
        "nivel_confianca": 95
      },
      "metodo_coleta": "Entrevistas domiciliares face a face"
    },
    "resultados": {
      "aprovacao_governo_jeronimo_rodrigues": {
        "questao": "Aprova/desaprova ...?",
        "dados_gerais": [
          { "periodo": "Abril/2026", "aprova": 56, "desaprova": 33, "ns_nr": 11 }
        ]
      }
    }
  }
}`;

interface ImportResult {
  import: {
    status: string;
    pesquisa_id?: string;
    estado_sigla?: string;
    instituto_nome?: string;
    estatisticas?: {
      avaliacoes_criadas: number;
      intencoes_criadas: number;
      pessoas_vinculadas: number;
    };
    mensagens?: string[];
  };
  ia?: {
    status: string;
    mensagem?: string;
    analise?: any;
    custo_estimado_centavos?: number;
    input_tokens?: number;
    output_tokens?: number;
    modelo?: string;
  } | null;
  status_aplicado?: any;
}

export function ImportarPesquisaPage() {
  const [jsonText, setJsonText] = useState("");
  const [rodarIA, setRodarIA] = useState(true);
  const [aplicarSugestoes, setAplicarSugestoes] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const mutation = useMutation<ImportResult>({
    mutationFn: async () => {
      let payload: any;
      try {
        payload = JSON.parse(jsonText);
      } catch {
        throw new Error("JSON inválido — verifique a sintaxe");
      }
      const r = await api.post(
        `/admin/pesquisas/importar-json?rodar_ia=${rodarIA}&aplicar_sugestoes=${aplicarSugestoes}`,
        payload
      );
      return r.data;
    },
    onError: (err: any) => {
      setErro(err?.response?.data?.detail || err.message);
    },
    onSuccess: () => {
      setErro(null);
    },
  });

  function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const txt = ev.target?.result;
      if (typeof txt === "string") setJsonText(txt);
    };
    reader.readAsText(f, "utf-8");
  }

  const result = mutation.data;
  const analise = result?.ia?.analise;

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900">
          Importar Pesquisa via JSON
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Cole ou carregue um JSON estruturado (formato Quaest e similares). O sistema cria a pesquisa,
          extrai avaliações de governo e intenções de voto, e (opcionalmente) gera análise via Claude.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Coluna esquerda — entrada */}
        <div className="space-y-3">
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display font-semibold flex items-center gap-2">
                <FileJson className="h-5 w-5 text-info" /> JSON da Pesquisa
              </h2>
              <label className="btn-secondary text-sm cursor-pointer">
                <Upload className="h-4 w-4" /> Carregar arquivo
                <input type="file" accept=".json,application/json" onChange={handleFile} className="hidden" />
              </label>
            </div>
            <textarea
              className="input font-mono text-xs"
              rows={20}
              placeholder={EXEMPLO_JSON}
              value={jsonText}
              onChange={(e) => setJsonText(e.target.value)}
            />
            <div className="text-xs text-gray-500 mt-1">
              {jsonText.length.toLocaleString("pt-BR")} caracteres
            </div>
          </div>

          <div className="card !p-3">
            <h3 className="text-sm font-semibold mb-2">Opções</h3>
            <label className="flex items-start gap-2 text-sm mb-2">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={rodarIA}
                onChange={(e) => setRodarIA(e.target.checked)}
              />
              <div>
                <span className="font-medium flex items-center gap-1">
                  <Bot className="h-3.5 w-3.5" /> Rodar análise via Claude (Haiku 4.5)
                </span>
                <span className="text-xs text-gray-500 block">
                  Identifica candidatos, gera insights e sugere atualização de status. Requer{" "}
                  <code>ANTHROPIC_API_KEY</code> em <code>backend/.env</code>.
                </span>
              </div>
            </label>
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-0.5"
                checked={aplicarSugestoes}
                onChange={(e) => setAplicarSugestoes(e.target.checked)}
                disabled={!rodarIA}
              />
              <div>
                <span className="font-medium">Aplicar sugestões da IA ao status do estado</span>
                <span className="text-xs text-gray-500 block">
                  Quando confiança ≥ 0.7, atualiza <code>nivel_consolidacao</code> e adiciona observação.
                </span>
              </div>
            </label>
          </div>

          <button
            className="btn-primary w-full"
            disabled={!jsonText.trim() || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? (
              "Processando…"
            ) : (
              <>
                <Sparkles className="h-4 w-4" /> Importar pesquisa
              </>
            )}
          </button>

          {erro && (
            <div className="card !p-3 bg-red-50 border-red-200 text-sm text-red-900 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <strong>Erro:</strong> {erro}
              </div>
            </div>
          )}
        </div>

        {/* Coluna direita — resultado */}
        <div className="space-y-3">
          {!result && !mutation.isPending && (
            <div className="card text-center text-gray-400 py-12">
              <FileJson className="mx-auto h-12 w-12 mb-2" />
              <p>Importe um JSON para ver o resultado aqui</p>
            </div>
          )}

          {result?.import && (
            <div className="card">
              <h2 className="font-display font-semibold mb-3 flex items-center gap-2">
                {result.import.status === "criada" ? (
                  <CheckCircle2 className="h-5 w-5 text-sucesso" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-atencao" />
                )}
                Importação:{" "}
                <span className={result.import.status === "criada" ? "text-sucesso" : "text-atencao"}>
                  {result.import.status}
                </span>
              </h2>

              {result.import.estado_sigla && (
                <div className="text-sm space-y-1 mb-3">
                  <Item label="Estado">
                    <Link to={`/estados/${result.import.estado_sigla}/pesquisas`} className="text-info hover:underline inline-flex items-center gap-1">
                      {result.import.estado_sigla} <ExternalLink className="h-3 w-3" />
                    </Link>
                  </Item>
                  <Item label="Instituto">{result.import.instituto_nome}</Item>
                  <Item label="ID Pesquisa">
                    <code className="text-xs">{result.import.pesquisa_id}</code>
                  </Item>
                </div>
              )}

              {result.import.estatisticas && (
                <div className="grid grid-cols-3 gap-2 mb-3">
                  <Stat label="Avaliações" value={result.import.estatisticas.avaliacoes_criadas} />
                  <Stat label="Intenções" value={result.import.estatisticas.intencoes_criadas} />
                  <Stat label="Pessoas" value={result.import.estatisticas.pessoas_vinculadas} />
                </div>
              )}

              {result.import.mensagens && (
                <ul className="text-xs text-gray-600 space-y-1 border-t border-gray-100 pt-2">
                  {result.import.mensagens.map((m, i) => (
                    <li key={i}>· {m}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {result?.ia && (
            <div className="card">
              <h2 className="font-display font-semibold mb-2 flex items-center gap-2">
                <Bot className="h-5 w-5 text-info" /> Análise IA
                {result.ia.status === "ok" && (
                  <span className="badge bg-green-50 text-green-700 text-xs">{result.ia.modelo}</span>
                )}
              </h2>

              {result.ia.status === "skip" && (
                <div className="text-sm text-gray-600 bg-yellow-50 border border-yellow-200 rounded p-2">
                  {result.ia.mensagem}
                </div>
              )}

              {result.ia.status === "ok" && analise && (
                <div className="space-y-3 text-sm">
                  {analise.resumo_executivo && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                        Resumo executivo
                      </div>
                      <p className="text-gray-800">{analise.resumo_executivo}</p>
                    </div>
                  )}

                  {analise.implicacoes_pt && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                        Implicações para o PT
                      </div>
                      <p className="text-gray-800">{analise.implicacoes_pt}</p>
                    </div>
                  )}

                  {analise.candidatos_identificados?.length > 0 && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                        Candidatos identificados ({analise.candidatos_identificados.length})
                      </div>
                      <div className="space-y-1">
                        {analise.candidatos_identificados.map((c: any, i: number) => (
                          <div key={i} className="text-xs border-l-2 border-info pl-2">
                            <span className="font-medium">{c.nome}</span>
                            <span className="text-gray-500"> · {c.cargo_provavel}</span>
                            {c.match_existente ? (
                              <span className="ml-2 badge bg-green-50 text-green-700 text-xs">
                                ↔ {c.match_existente}
                              </span>
                            ) : (
                              <span className="ml-2 badge bg-yellow-50 text-yellow-700 text-xs">
                                novo
                              </span>
                            )}
                            {c.destaque_numerico && (
                              <span className="ml-2 text-gray-600">{c.destaque_numerico}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {analise.tendencias_observadas?.length > 0 && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                        Tendências
                      </div>
                      <div className="space-y-1">
                        {analise.tendencias_observadas.map((t: any, i: number) => (
                          <div key={i} className="text-xs">
                            <span
                              className={
                                t.direcao === "subindo"
                                  ? "text-sucesso"
                                  : t.direcao === "caindo"
                                    ? "text-alerta"
                                    : "text-gray-500"
                              }
                            >
                              {t.direcao === "subindo" ? "↗" : t.direcao === "caindo" ? "↘" : "→"}
                            </span>{" "}
                            <strong>{t.metrica}</strong>: {t.magnitude} — {t.implicacao}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {analise.alertas?.length > 0 && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                        Alertas
                      </div>
                      {analise.alertas.map((a: any, i: number) => (
                        <div
                          key={i}
                          className={`text-xs px-2 py-1 rounded mb-1 ${
                            a.tipo === "risco"
                              ? "bg-red-50 text-red-900"
                              : a.tipo === "oportunidade"
                                ? "bg-green-50 text-green-900"
                                : "bg-yellow-50 text-yellow-900"
                          }`}
                        >
                          [{a.tipo}] {a.descricao}
                        </div>
                      ))}
                    </div>
                  )}

                  {analise.sugestao_status_estado?.nivel_consolidacao_sugerido && (
                    <div>
                      <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                        Sugestão para status do estado
                      </div>
                      <div className="text-xs">
                        <span className="badge bg-blue-50 text-info">
                          {analise.sugestao_status_estado.nivel_consolidacao_sugerido}
                        </span>{" "}
                        confiança {(analise.sugestao_status_estado.confianca * 100).toFixed(0)}%
                        {analise.sugestao_status_estado.justificativa && (
                          <p className="mt-1 text-gray-700">
                            {analise.sugestao_status_estado.justificativa}
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="text-xs text-gray-400 border-t border-gray-100 pt-2">
                    {result.ia.input_tokens} tok in · {result.ia.output_tokens} tok out · custo estimado{" "}
                    R$ {((result.ia.custo_estimado_centavos || 0) / 100).toFixed(4)}
                  </div>
                </div>
              )}

              {result.ia.status === "erro" && (
                <div className="text-sm text-alerta bg-red-50 border border-red-200 rounded p-2">
                  {result.ia.mensagem}
                </div>
              )}
            </div>
          )}

          {result?.status_aplicado?.aplicado && (
            <div className="card !p-3 bg-green-50 border-green-200 text-sm">
              <CheckCircle2 className="inline h-4 w-4 text-sucesso mr-1" />
              Status do estado atualizado: {result.status_aplicado.nivel_anterior} →{" "}
              <strong>{result.status_aplicado.nivel_novo}</strong>
            </div>
          )}

          {result?.import?.pesquisa_id && (
            <Link
              to={`/estados/${result.import.estado_sigla}/pesquisas`}
              className="btn-primary w-full"
            >
              Ver pesquisa na ficha do estado <ArrowRight className="h-4 w-4" />
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-xs text-gray-500 uppercase tracking-wide w-20">{label}</span>
      <span className="font-medium">{children}</span>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-gray-50 rounded p-2 text-center">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-lg font-bold font-mono">{value}</div>
    </div>
  );
}
