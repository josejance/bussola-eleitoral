import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Sparkles, Sliders, TrendingUp } from "lucide-react";

import { api } from "../lib/api";
import { Estado } from "../lib/types";

interface Ponto {
  pesquisa_id: string;
  data: string;
  instituto_id: string;
  instituto_nome: string;
  amostra: number | null;
  margem_erro: number | null;
  metodologia: string;
  percentual: number;
  peso: number;
}

interface CandidatoAgregado {
  nome: string;
  estimativa: number;
  banda_inferior: number;
  banda_superior: number;
  n_pesquisas: number;
  peso_total: number;
  ultima_data: string | null;
  pontos: Ponto[];
}

interface Agregado {
  candidatos: CandidatoAgregado[];
  serie_temporal: any[];
  meta: {
    n_pesquisas: number;
    n_institutos: number;
    data_referencia: string;
    estado_id: string | null;
    cargo: string | null;
    cenario: string;
    meia_vida_dias: number;
  };
}

const CORES = ["#DC2626", "#2563EB", "#16A34A", "#EA580C", "#7C3AED", "#0891B2", "#DB2777", "#65A30D", "#CA8A04", "#0F172A"];

export function AgregadorPage() {
  const [estadoId, setEstadoId] = useState<string>("");
  const [cenario, setCenario] = useState<string>("estimulado");
  const [meiaVida, setMeiaVida] = useState<number>(14);
  const [apenasTSE, setApenasTSE] = useState(false);
  const [showConfig, setShowConfig] = useState(false);

  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });

  const { data: agregado, isLoading } = useQuery({
    queryKey: ["agregador", estadoId, cenario, meiaVida, apenasTSE],
    queryFn: async () =>
      (
        await api.get<Agregado>("/pesquisas/agregador", {
          params: {
            estado_id: estadoId || undefined,
            cenario,
            meia_vida_dias: meiaVida,
            incluir_apenas_tse: apenasTSE,
          },
        })
      ).data,
  });

  const candidatos = agregado?.candidatos || [];

  // Cores por candidato (estáveis pelo nome)
  const cores = useMemo(() => {
    const m: Record<string, string> = {};
    candidatos.forEach((c, i) => {
      m[c.nome] = CORES[i % CORES.length];
    });
    return m;
  }, [candidatos]);

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-display font-semibold text-gray-900 flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-info" /> Agregador de Pesquisas
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Média ponderada com decaimento exponencial. Considera recência, amostra, confiabilidade do instituto e metodologia.
          </p>
        </div>
        <button
          onClick={() => setShowConfig(!showConfig)}
          className="btn-secondary text-sm"
        >
          <Sliders className="h-4 w-4" /> {showConfig ? "Esconder" : "Configurar"}
        </button>
      </header>

      {/* Filtros */}
      <div className="card mb-4 !p-3">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label !text-xs !mb-0.5">Escopo</label>
            <select
              className="input !py-1 !text-sm"
              value={estadoId}
              onChange={(e) => setEstadoId(e.target.value)}
            >
              <option value="">🇧🇷 Brasil (presidencial)</option>
              {estados
                .sort((a, b) => a.nome.localeCompare(b.nome))
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.sigla} — {e.nome}
                  </option>
                ))}
            </select>
          </div>
          <div>
            <label className="label !text-xs !mb-0.5">Cenário</label>
            <select
              className="input !py-1 !text-sm"
              value={cenario}
              onChange={(e) => setCenario(e.target.value)}
            >
              <option value="estimulado">Estimulado</option>
              <option value="espontaneo">Espontâneo</option>
            </select>
          </div>
          {showConfig && (
            <>
              <div>
                <label className="label !text-xs !mb-0.5">
                  Meia-vida ({meiaVida} dias)
                </label>
                <input
                  type="range"
                  min={7}
                  max={45}
                  value={meiaVida}
                  onChange={(e) => setMeiaVida(parseInt(e.target.value))}
                  className="w-32"
                />
              </div>
              <label className="flex items-center gap-1.5 text-sm pb-1">
                <input
                  type="checkbox"
                  checked={apenasTSE}
                  onChange={(e) => setApenasTSE(e.target.checked)}
                />
                <span>Apenas TSE</span>
              </label>
            </>
          )}
          {agregado && (
            <div className="ml-auto text-xs text-gray-500 self-center">
              {agregado.meta.n_pesquisas} pesquisas · {agregado.meta.n_institutos} institutos · ref{" "}
              {format(parseISO(agregado.meta.data_referencia), "dd/MM/yyyy", { locale: ptBR })}
            </div>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="card text-center text-gray-400 py-12">Calculando…</div>
      ) : candidatos.length === 0 || !agregado ? (
        <div className="card text-center text-gray-500 py-12">
          Nenhuma pesquisa atende aos filtros. Tente ampliar o escopo ou desativar "Apenas TSE".
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Gráfico temporal — esquerda 2/3 */}
          <div className="lg:col-span-2 space-y-4">
            <div className="card">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
                Evolução temporal
              </h2>
              {agregado.serie_temporal.length > 0 ? (
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={agregado.serie_temporal} margin={{ top: 5, right: 20, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                      <XAxis dataKey="data_label" tick={{ fontSize: 10 }} />
                      <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                      <Tooltip
                        contentStyle={{ fontSize: 12, borderRadius: 8 }}
                        formatter={(v: any) => [`${v}%`, ""]}
                      />
                      <Legend wrapperStyle={{ fontSize: 11 }} iconType="line" />
                      {candidatos.slice(0, 6).map((c) => (
                        <Line
                          key={c.nome}
                          type="monotone"
                          dataKey={c.nome}
                          stroke={cores[c.nome]}
                          strokeWidth={2.5}
                          dot={{ r: 3 }}
                          connectNulls
                        />
                      ))}
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-gray-400">Sem série temporal disponível.</p>
              )}
            </div>

            {/* Pontos individuais */}
            <div className="card">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
                Pesquisas no agregado
              </h2>
              <div className="space-y-1 max-h-80 overflow-y-auto">
                {(() => {
                  const todosPontos = candidatos
                    .flatMap((c) => c.pontos.map((p) => ({ ...p, candidato: c.nome })))
                    .sort((a, b) => b.data.localeCompare(a.data));
                  return todosPontos.map((p, i) => (
                    <div
                      key={`${p.pesquisa_id}-${p.candidato}-${i}`}
                      className="flex items-center gap-2 text-xs py-1 border-b border-gray-50 last:border-0"
                    >
                      <span
                        className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: cores[p.candidato] }}
                      />
                      <span className="text-gray-500 font-mono">
                        {format(parseISO(p.data), "dd/MM/yy", { locale: ptBR })}
                      </span>
                      <span className="font-medium flex-1 truncate">{p.candidato}</span>
                      <span className="text-gray-600">{p.instituto_nome}</span>
                      <span className="font-mono font-bold w-12 text-right">{p.percentual}%</span>
                      <span className="text-gray-400 font-mono w-12 text-right">peso {p.peso.toFixed(2)}</span>
                    </div>
                  ));
                })()}
              </div>
            </div>
          </div>

          {/* Ranking — direita 1/3 */}
          <div className="space-y-4">
            <div className="card">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2 flex items-center gap-1">
                <TrendingUp className="h-4 w-4" /> Ranking agregado
              </h2>
              <div className="space-y-2">
                {candidatos.map((c, idx) => (
                  <div key={c.nome}>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-mono text-xs text-gray-400 w-4">{idx + 1}</span>
                      <span
                        className="inline-block w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: cores[c.nome] }}
                      />
                      <span className="font-medium flex-1 truncate" title={c.nome}>
                        {c.nome}
                      </span>
                      <span className="font-mono font-bold text-lg">{c.estimativa.toFixed(1)}%</span>
                    </div>
                    {/* Banda de incerteza */}
                    <div className="ml-9 mt-0.5">
                      <div className="relative h-1.5 bg-gray-100 rounded-full">
                        <div
                          className="absolute h-1.5 rounded-full opacity-30"
                          style={{
                            left: `${c.banda_inferior}%`,
                            width: `${c.banda_superior - c.banda_inferior}%`,
                            backgroundColor: cores[c.nome],
                          }}
                        />
                        <div
                          className="absolute w-1 h-3 rounded-sm -top-0.5"
                          style={{
                            left: `${c.estimativa}%`,
                            backgroundColor: cores[c.nome],
                          }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-gray-400 mt-0.5">
                        <span>{c.banda_inferior.toFixed(1)}%</span>
                        <span>
                          {c.n_pesquisas} pesq · peso {c.peso_total.toFixed(2)}
                        </span>
                        <span>{c.banda_superior.toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <MonteCarloCard estadoId={estadoId} cenario={cenario} />

            <div className="card !p-3 text-xs text-gray-600">
              <p className="font-semibold mb-1">📐 Como o agregador funciona</p>
              <ul className="space-y-0.5 list-disc list-inside">
                <li>Decaimento exponencial: meia-vida {meiaVida} dias</li>
                <li>Peso por amostra: √(n / 1500), capado em 1.5</li>
                <li>Peso por confiabilidade: (score/5)^1.5</li>
                <li>Peso por método: presencial 1.0, online 0.75</li>
                <li>Banda 95%: combina desvio + erro amostral + erro metodológico</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface MonteCarloResult {
  n_simulacoes: number;
  candidatos_considerados: string[];
  prob_1t: Record<string, number>;
  prob_2t: Record<string, number>;
  cenarios_2t: { candidato_a: string; candidato_b: string; probabilidade: number; favorito: string }[];
}

function MonteCarloCard({ estadoId, cenario }: { estadoId: string; cenario: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["monte-carlo", estadoId, cenario],
    queryFn: async () =>
      (
        await api.get<MonteCarloResult>("/pesquisas/agregador/monte-carlo", {
          params: { estado_id: estadoId || undefined, cenario, n_simulacoes: 10000 },
        })
      ).data,
  });

  if (isLoading) return <div className="card !p-3 text-xs text-gray-400">Simulando…</div>;
  if (!data || data.candidatos_considerados.length === 0) return null;

  const top1T = Object.entries(data.prob_1t).sort((a, b) => b[1] - a[1]).slice(0, 4);
  const top2T = Object.entries(data.prob_2t).sort((a, b) => b[1] - a[1]).slice(0, 6);

  return (
    <div className="card !p-3">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
        🎲 Monte Carlo ({data.n_simulacoes.toLocaleString("pt-BR")} simulações)
      </h3>
      {top1T.length > 0 && (
        <>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Probabilidade 1º turno (&gt;50%)</div>
          <div className="space-y-0.5 mb-2">
            {top1T.map(([nome, pct]) => (
              <div key={nome} className="flex items-center gap-2 text-xs">
                <span className="font-medium flex-1 truncate">{nome}</span>
                <span className="font-mono font-bold text-sucesso">{pct}%</span>
              </div>
            ))}
          </div>
        </>
      )}
      {top2T.length > 0 && (
        <>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1 mt-2">Probabilidade ir a 2º turno</div>
          <div className="space-y-0.5 mb-2">
            {top2T.map(([nome, pct]) => (
              <div key={nome} className="flex items-center gap-2 text-xs">
                <span className="font-medium flex-1 truncate">{nome}</span>
                <span className="font-mono font-bold text-info">{pct}%</span>
              </div>
            ))}
          </div>
        </>
      )}
      {data.cenarios_2t.length > 0 && (
        <>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1 mt-2">Top cenários de 2º turno</div>
          <div className="space-y-0.5">
            {data.cenarios_2t.slice(0, 4).map((c, i) => (
              <div key={i} className="text-xs border-l-2 border-gray-200 pl-2">
                <div className="font-medium">{c.candidato_a} × {c.candidato_b}</div>
                <div className="text-gray-500">
                  {c.probabilidade}% prob · favorito: {c.favorito}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
