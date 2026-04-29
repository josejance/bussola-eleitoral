import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingUp } from "lucide-react";

import { api } from "../lib/api";
import { Estado } from "../lib/types";

interface VotacaoHistorica {
  ano: number;
  cargo: string;
  votos_totais: number;
  percentual_total: number | null;
  bancada_eleita: number;
}

const CORES = ["#DC2626", "#2563EB", "#16A34A", "#EA580C", "#7C3AED", "#0891B2", "#DB2777", "#65A30D", "#CA8A04"];

type Cargo = "deputado_federal" | "deputado_estadual";
type Metrica = "bancada_eleita" | "percentual_total" | "votos_totais";

export function HistoricoEleitoralPage() {
  const [cargo, setCargo] = useState<Cargo>("deputado_federal");
  const [metrica, setMetrica] = useState<Metrica>("bancada_eleita");
  const [estadosSelecionados, setEstadosSelecionados] = useState<string[]>([]);
  const [partidoSigla] = useState<string>("PT");

  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });

  // Carrega histórico para cada estado selecionado (ou todos se nenhum)
  const estadosParaCarregar = estadosSelecionados.length > 0
    ? estados.filter((e) => estadosSelecionados.includes(e.id))
    : estados;

  const { data: dadosPorEstado = {} } = useQuery({
    queryKey: ["historico-todos", partidoSigla, estadosSelecionados],
    queryFn: async () => {
      const result: Record<string, VotacaoHistorica[]> = {};
      for (const e of estadosParaCarregar) {
        const r = await api.get<VotacaoHistorica[]>(
          "/historico/votacao-partido-estado",
          { params: { estado_id: e.id, partido_sigla: partidoSigla } }
        );
        result[e.sigla] = r.data;
      }
      return result;
    },
    enabled: estados.length > 0,
  });

  // Reformata para gráfico: cada ponto é um ano, com coluna por estado
  const dataChart = useMemo(() => {
    const anos = new Set<number>();
    Object.values(dadosPorEstado).forEach((rows) =>
      rows.forEach((r) => {
        if (r.cargo === cargo) anos.add(r.ano);
      })
    );
    return Array.from(anos)
      .sort()
      .map((ano) => {
        const ponto: any = { ano };
        for (const sigla in dadosPorEstado) {
          const r = dadosPorEstado[sigla].find((x) => x.ano === ano && x.cargo === cargo);
          if (r) {
            const v = r[metrica];
            if (typeof v === "number") ponto[sigla] = v;
          }
        }
        return ponto;
      });
  }, [dadosPorEstado, cargo, metrica]);

  const estadosNoChart = useMemo(() => {
    const set = new Set<string>();
    dataChart.forEach((p) => {
      Object.keys(p).forEach((k) => k !== "ano" && set.add(k));
    });
    return Array.from(set).sort();
  }, [dataChart]);

  // Top 10 estados por última métrica
  const topEstados = useMemo(() => {
    const ranking = estadosNoChart
      .map((sigla) => {
        const rows = dadosPorEstado[sigla] || [];
        const ultimo = rows.filter((r) => r.cargo === cargo).sort((a, b) => b.ano - a.ano)[0];
        if (!ultimo) return null;
        return { sigla, valor: (ultimo[metrica] as number) || 0, ano: ultimo.ano };
      })
      .filter((x): x is { sigla: string; valor: number; ano: number } => !!x)
      .sort((a, b) => b.valor - a.valor)
      .slice(0, 10);
    return ranking;
  }, [estadosNoChart, dadosPorEstado, cargo, metrica]);

  // Por padrão: top 5 estados aparecem no gráfico se nenhum filtro
  const estadosVisiveis = estadosSelecionados.length > 0
    ? estadosNoChart
    : topEstados.slice(0, 5).map((t) => t.sigla);

  const labelMetrica = {
    bancada_eleita: "Cadeiras eleitas",
    percentual_total: "% dos votos válidos",
    votos_totais: "Votos absolutos",
  }[metrica];

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900 flex items-center gap-2">
          <TrendingUp className="h-6 w-6 text-info" /> Histórico Eleitoral PT
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Desempenho do Partido dos Trabalhadores nas eleições estaduais 2018 e 2022.
        </p>
      </header>

      {/* Controles */}
      <div className="card mb-4 !p-3">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="label !text-xs !mb-0.5">Cargo</label>
            <div className="inline-flex rounded-md shadow-sm">
              {([["deputado_federal", "Federal"], ["deputado_estadual", "Estadual"]] as [Cargo, string][]).map(
                ([key, label]) => (
                  <button
                    key={key}
                    onClick={() => setCargo(key)}
                    className={`px-3 py-1 text-sm font-medium border ${
                      cargo === key ? "bg-info text-white border-info" : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                    } first:rounded-l-md last:rounded-r-md -ml-px first:ml-0`}
                  >
                    {label}
                  </button>
                )
              )}
            </div>
          </div>
          <div>
            <label className="label !text-xs !mb-0.5">Métrica</label>
            <div className="inline-flex rounded-md shadow-sm">
              {([
                ["bancada_eleita", "Cadeiras"],
                ["percentual_total", "% Válidos"],
                ["votos_totais", "Votos absolutos"],
              ] as [Metrica, string][]).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setMetrica(key)}
                  className={`px-3 py-1 text-sm font-medium border ${
                    metrica === key ? "bg-info text-white border-info" : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                  } first:rounded-l-md last:rounded-r-md -ml-px first:ml-0`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="ml-auto text-xs text-gray-500">
            {estadosVisiveis.length} estados no gráfico
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Gráfico */}
        <div className="lg:col-span-2 card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
            {labelMetrica} por estado · 2018 → 2022
          </h2>
          {dataChart.length > 0 ? (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dataChart} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis dataKey="ano" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8 }}
                    formatter={(v: any) =>
                      metrica === "percentual_total"
                        ? [`${v}%`, ""]
                        : metrica === "votos_totais"
                          ? [v.toLocaleString("pt-BR"), ""]
                          : [v, ""]
                    }
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} iconType="line" />
                  {estadosVisiveis.map((sigla, i) => (
                    <Line
                      key={sigla}
                      type="monotone"
                      dataKey={sigla}
                      stroke={CORES[i % CORES.length]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-gray-500">Sem dados disponíveis. Rode <code>python -m app.seeds.runner_gte</code>.</p>
          )}
        </div>

        {/* Ranking */}
        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
            Top estados (último ano)
          </h2>
          <div className="space-y-1">
            {topEstados.map((t, idx) => (
              <button
                key={t.sigla}
                onClick={() => {
                  setEstadosSelecionados((s) =>
                    s.includes(estados.find((e) => e.sigla === t.sigla)?.id || "")
                      ? s.filter((x) => x !== estados.find((e) => e.sigla === t.sigla)?.id)
                      : [...s, estados.find((e) => e.sigla === t.sigla)?.id || ""].filter(Boolean)
                  );
                }}
                className="w-full flex items-center gap-2 text-sm hover:bg-gray-50 px-2 py-1 rounded"
              >
                <span className="font-mono text-xs text-gray-400 w-4">{idx + 1}</span>
                <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-gray-100 font-bold">
                  {t.sigla}
                </span>
                <span className="text-xs text-gray-500 flex-1 text-left">
                  {estados.find((e) => e.sigla === t.sigla)?.nome}
                </span>
                <span className="font-mono font-bold">
                  {metrica === "percentual_total"
                    ? `${t.valor.toFixed(1)}%`
                    : metrica === "votos_totais"
                      ? t.valor.toLocaleString("pt-BR")
                      : t.valor}
                </span>
              </button>
            ))}
          </div>
          {estadosSelecionados.length > 0 && (
            <button
              onClick={() => setEstadosSelecionados([])}
              className="mt-2 text-xs text-info hover:underline"
            >
              limpar filtro de estados
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
