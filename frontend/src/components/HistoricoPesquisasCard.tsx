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
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { BarChart3, Info, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../lib/api";

interface Instituto {
  id: string;
  nome: string;
  sigla: string | null;
  confiabilidade_score: number;
  total_pesquisas: number;
}

interface SerieAvaliacao {
  pesquisa_id: string;
  data: string;
  data_pesquisa?: string;
  instituto: { id: string; nome: string; sigla: string | null; confiabilidade: number };
  pessoa_avaliada: { id: string; nome: string } | null;
  amostra: number | null;
  margem_erro: number | null;
  registro_tse: string | null;
  aprova: number | null;
  desaprova: number | null;
  otimo_bom: number | null;
  regular: number | null;
  ruim_pessimo: number | null;
}

type Metrica = "aprova" | "desaprova" | "otimo_bom" | "ruim_pessimo";

const METRICAS_LABEL: Record<Metrica, string> = {
  aprova: "Aprovação",
  desaprova: "Desaprovação",
  otimo_bom: "Ótimo + Bom",
  ruim_pessimo: "Ruim + Péssimo",
};

const CORES_INSTITUTO = [
  "#2563EB", // info blue
  "#DC2626", // alerta red
  "#16A34A", // sucesso green
  "#EA580C", // orange
  "#7C3AED", // purple
  "#0891B2", // cyan
  "#DB2777", // pink
  "#65A30D", // lime
];

interface Props {
  /** Se passado, filtra para um estado específico. Se omitido, mostra nacional. */
  estadoId?: string;
  /** Nivel a buscar — default 'estadual' se estadoId, 'presidencial' caso contrário */
  nivelDefault?: "estadual" | "presidencial";
  titulo?: string;
}

export function HistoricoPesquisasCard({ estadoId, nivelDefault, titulo }: Props) {
  const nivel = nivelDefault || (estadoId ? "estadual" : "presidencial");
  const [metrica, setMetrica] = useState<Metrica>("aprova");
  const [institutoFilter, setInstitutoFilter] = useState<string>("");

  const { data: institutos = [] } = useQuery({
    queryKey: ["institutos"],
    queryFn: async () => (await api.get<Instituto[]>("/pesquisas/institutos")).data,
  });

  const { data: series = [], isLoading } = useQuery({
    queryKey: ["historico-aval", nivel, estadoId, institutoFilter],
    queryFn: async () =>
      (
        await api.get<SerieAvaliacao[]>("/pesquisas/historico/avaliacao-governo", {
          params: {
            nivel,
            estado_id: estadoId,
            instituto_id: institutoFilter || undefined,
          },
        })
      ).data,
  });

  // Reorganiza dados para o gráfico: cada ponto é uma data, com colunas por instituto
  const { chartData, institutosPresentes } = useMemo(() => {
    const institutosSet = new Map<string, string>();
    const pontosPorData = new Map<string, any>();

    for (const s of series) {
      const valor = s[metrica];
      if (valor == null) continue;
      const dataEfetiva = s.data || s.data_pesquisa;
      if (!dataEfetiva) continue;
      institutosSet.set(s.instituto.id, s.instituto.sigla || s.instituto.nome);

      if (!pontosPorData.has(dataEfetiva)) {
        try {
          pontosPorData.set(dataEfetiva, {
            data: dataEfetiva,
            dataLabel: format(parseISO(dataEfetiva), "MMM/yy", { locale: ptBR }),
          });
        } catch {
          continue;
        }
      }
      const ponto = pontosPorData.get(dataEfetiva);
      // Se já existe, usa o último (sobrescreve duplicado da mesma data+instituto)
      ponto[s.instituto.id] = valor;
    }

    const sorted = Array.from(pontosPorData.values()).sort((a, b) => a.data.localeCompare(b.data));
    return {
      chartData: sorted,
      institutosPresentes: Array.from(institutosSet.entries()),
    };
  }, [series, metrica]);

  const ultimaPesquisa = series[series.length - 1];

  return (
    <div className="card">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h2 className="font-display font-semibold text-gray-900 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-info" />
            {titulo || (nivel === "presidencial" ? "Pesquisas Nacionais" : "Pesquisas do Estado")}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {series.length} {series.length === 1 ? "registro" : "registros"} de {institutosPresentes.length}{" "}
            {institutosPresentes.length === 1 ? "instituto" : "institutos"}
          </p>
        </div>
        <Link
          to="/pesquisas/importar"
          className="text-xs text-info hover:underline inline-flex items-center gap-1"
        >
          <Sparkles className="h-3 w-3" /> importar JSON
        </Link>
      </div>

      {/* Controles */}
      <div className="flex flex-wrap gap-2 mb-3">
        <div className="inline-flex rounded-md shadow-sm" role="group">
          {(["aprova", "desaprova", "otimo_bom", "ruim_pessimo"] as Metrica[]).map((m) => (
            <button
              key={m}
              onClick={() => setMetrica(m)}
              className={`px-2.5 py-1 text-xs font-medium border ${
                metrica === m
                  ? "bg-info text-white border-info"
                  : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
              } first:rounded-l-md last:rounded-r-md -ml-px first:ml-0`}
            >
              {METRICAS_LABEL[m]}
            </button>
          ))}
        </div>

        <select
          className="input !py-1 !text-xs max-w-[200px]"
          value={institutoFilter}
          onChange={(e) => setInstitutoFilter(e.target.value)}
        >
          <option value="">Todos os institutos</option>
          {institutos
            .filter((i) => i.total_pesquisas > 0)
            .map((i) => (
              <option key={i.id} value={i.id}>
                {i.nome} ({i.total_pesquisas})
              </option>
            ))}
        </select>
      </div>

      {/* Gráfico */}
      {isLoading ? (
        <div className="text-sm text-gray-400 py-12 text-center">Carregando…</div>
      ) : chartData.length === 0 ? (
        <EmptyState nivel={nivel} estadoId={estadoId} />
      ) : (
        <>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis
                  dataKey="dataLabel"
                  tick={{ fontSize: 10, fill: "#6B7280" }}
                  axisLine={{ stroke: "#D1D5DB" }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: "#6B7280" }}
                  axisLine={{ stroke: "#D1D5DB" }}
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  contentStyle={{
                    fontSize: 12,
                    borderRadius: 8,
                    border: "1px solid #E5E7EB",
                    boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
                  }}
                  formatter={(value: any) => [`${value}%`, ""]}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} iconType="line" />
                {institutosPresentes.map(([id, nome], idx) => (
                  <Line
                    key={id}
                    type="monotone"
                    dataKey={id}
                    name={nome}
                    stroke={CORES_INSTITUTO[idx % CORES_INSTITUTO.length]}
                    strokeWidth={2}
                    dot={{ r: 4, strokeWidth: 2, fill: "#fff" }}
                    activeDot={{ r: 6 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {ultimaPesquisa && (
            <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-600">
              <strong>Última:</strong> {ultimaPesquisa.instituto.nome} (
              {format(parseISO(ultimaPesquisa.data), "dd/MM/yyyy", { locale: ptBR })})
              {ultimaPesquisa.amostra && ` · amostra ${ultimaPesquisa.amostra}`}
              {ultimaPesquisa.margem_erro && ` · margem ±${ultimaPesquisa.margem_erro}pp`}
              {ultimaPesquisa.registro_tse && (
                <span className="ml-2 badge bg-blue-50 text-info text-xs font-mono">
                  {ultimaPesquisa.registro_tse}
                </span>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function EmptyState({ nivel, estadoId }: { nivel: string; estadoId?: string }) {
  return (
    <div className="bg-gray-50 border border-dashed border-gray-300 rounded p-6 text-center">
      <Info className="mx-auto h-8 w-8 text-gray-400 mb-2" />
      <p className="text-sm text-gray-600 mb-1">
        Nenhuma pesquisa {nivel === "presidencial" ? "nacional" : estadoId ? "deste estado" : ""} cadastrada.
      </p>
      <Link to="/pesquisas/importar" className="text-xs text-info hover:underline">
        Importar via JSON →
      </Link>
    </div>
  );
}
