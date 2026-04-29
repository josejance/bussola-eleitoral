import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowLeftRight, X } from "lucide-react";

import { api } from "../lib/api";
import { Pesquisa } from "../lib/types";

interface PesquisaComparada {
  id: string;
  instituto: { id: string; nome: string; sigla: string | null };
  data_fim_campo: string | null;
  amostra: number | null;
  margem_erro: number | null;
  registro_tse: string | null;
  estado_id: string | null;
  abrangencia: string;
  tipo_cenario: string;
  intencoes: { nome: string; percentual: number; posicao: number | null }[];
}

const CORES = ["#DC2626", "#2563EB", "#16A34A", "#EA580C", "#7C3AED", "#0891B2", "#DB2777", "#65A30D"];

export function ComparadorPage() {
  const [search, setSearch] = useSearchParams();
  const idsFromUrl = (search.get("ids") || "").split(",").filter(Boolean);
  const [selecionados, setSelecionados] = useState<string[]>(idsFromUrl);

  // Lista todas pesquisas para selecionar
  const { data: todasPesquisas = [] } = useQuery({
    queryKey: ["pesquisas", "all"],
    queryFn: async () => (await api.get<Pesquisa[]>("/pesquisas", { params: { limit: 200 } })).data,
  });

  const { data: comparacao = [] } = useQuery({
    queryKey: ["comparador", selecionados],
    queryFn: async () =>
      (
        await api.get<PesquisaComparada[]>("/pesquisas/comparador", {
          params: { pesquisa_ids: selecionados.join(",") },
        })
      ).data,
    enabled: selecionados.length > 0,
  });

  // Sincroniza URL
  useEffect(() => {
    if (selecionados.length > 0) {
      setSearch({ ids: selecionados.join(",") });
    } else {
      setSearch({});
    }
  }, [selecionados]);

  function toggle(id: string) {
    setSelecionados((s) =>
      s.includes(id) ? s.filter((x) => x !== id) : s.length < 5 ? [...s, id] : s
    );
  }

  // Cores por candidato (estáveis pelo nome)
  const candidatosComuns = useMemo(() => {
    const set = new Set<string>();
    comparacao.forEach((p) => p.intencoes.forEach((i) => set.add(i.nome)));
    return Array.from(set).slice(0, 10);
  }, [comparacao]);

  const cores = useMemo(() => {
    const m: Record<string, string> = {};
    candidatosComuns.forEach((nome, i) => {
      m[nome] = CORES[i % CORES.length];
    });
    return m;
  }, [candidatosComuns]);

  // Formato para BarChart agrupado
  const dataChart = useMemo(() => {
    return candidatosComuns.map((nome) => {
      const ponto: any = { nome };
      comparacao.forEach((p) => {
        const i = p.intencoes.find((x) => x.nome === nome);
        const label = `${p.instituto.nome} ${p.data_fim_campo ? format(parseISO(p.data_fim_campo), "dd/MM", { locale: ptBR }) : ""}`;
        ponto[label] = i?.percentual || 0;
      });
      return ponto;
    });
  }, [comparacao, candidatosComuns]);

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900 flex items-center gap-2">
          <ArrowLeftRight className="h-6 w-6 text-info" /> Comparador de Pesquisas
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Selecione até 5 pesquisas para comparar resultados lado a lado.
        </p>
      </header>

      {/* Selecionados */}
      {selecionados.length > 0 && (
        <div className="card mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold">
              {selecionados.length} pesquisa{selecionados.length > 1 ? "s" : ""} selecionada
              {selecionados.length > 1 ? "s" : ""}
            </span>
            <button
              onClick={() => setSelecionados([])}
              className="text-xs text-alerta hover:underline"
            >
              limpar tudo
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {comparacao.map((p) => (
              <button
                key={p.id}
                onClick={() => toggle(p.id)}
                className="badge bg-blue-50 text-info text-xs flex items-center gap-1 hover:bg-blue-100"
              >
                {p.instituto.nome} ·{" "}
                {p.data_fim_campo && format(parseISO(p.data_fim_campo), "dd/MM/yy", { locale: ptBR })}
                <X className="h-3 w-3" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Comparação visual */}
      {comparacao.length >= 2 && candidatosComuns.length > 0 && (
        <div className="card mb-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
            Comparação visual
          </h2>
          <div className="h-96">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dataChart} margin={{ top: 5, right: 20, left: 80, bottom: 5 }} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                <YAxis type="category" dataKey="nome" tick={{ fontSize: 10 }} width={130} />
                <Tooltip contentStyle={{ fontSize: 11 }} formatter={(v: any) => [`${v}%`, ""]} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                {comparacao.map((p, i) => {
                  const label = `${p.instituto.nome} ${p.data_fim_campo ? format(parseISO(p.data_fim_campo), "dd/MM", { locale: ptBR }) : ""}`;
                  return (
                    <Bar
                      key={p.id}
                      dataKey={label}
                      fill={CORES[i % CORES.length]}
                      radius={[0, 3, 3, 0]}
                    />
                  );
                })}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Tabela detalhada */}
      {comparacao.length > 0 && (
        <div className="card !p-0 overflow-x-auto mb-4">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 text-xs uppercase text-gray-500">
              <tr>
                <th className="text-left px-3 py-2 sticky left-0 bg-gray-50">Candidato</th>
                {comparacao.map((p) => (
                  <th key={p.id} className="text-right px-3 py-2 min-w-[140px]">
                    <div className="font-semibold text-gray-700">{p.instituto.nome}</div>
                    <div className="text-[10px] font-normal">
                      {p.data_fim_campo &&
                        format(parseISO(p.data_fim_campo), "dd/MM/yyyy", { locale: ptBR })}
                    </div>
                    <div className="text-[10px] font-normal">
                      n={p.amostra} ±{p.margem_erro}pp
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {candidatosComuns.map((nome, idx) => (
                <tr key={nome} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-3 py-1.5 sticky left-0 bg-white font-medium">
                    <span
                      className="inline-block w-2 h-2 rounded-full mr-1.5"
                      style={{ backgroundColor: cores[nome] }}
                    />
                    {nome}
                  </td>
                  {comparacao.map((p) => {
                    const intencao = p.intencoes.find((i) => i.nome === nome);
                    return (
                      <td key={p.id} className="px-3 py-1.5 text-right font-mono">
                        {intencao ? `${intencao.percentual}%` : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Lista de pesquisas para selecionar */}
      <div className="card">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
          Pesquisas disponíveis ({todasPesquisas.length})
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 max-h-96 overflow-y-auto">
          {todasPesquisas.map((p) => {
            const sel = selecionados.includes(p.id);
            return (
              <button
                key={p.id}
                onClick={() => toggle(p.id)}
                disabled={!sel && selecionados.length >= 5}
                className={`text-left p-2 rounded border text-xs transition ${
                  sel
                    ? "bg-blue-50 border-info"
                    : "bg-white border-gray-200 hover:border-info disabled:opacity-50"
                }`}
              >
                <div className="font-medium">{p.contratante || "Pesquisa"}</div>
                <div className="text-gray-500">
                  {p.data_fim_campo && format(parseISO(p.data_fim_campo), "dd/MM/yyyy", { locale: ptBR })}{" "}
                  · n={p.amostra} · ±{p.margem_erro}pp
                </div>
                {p.registro_tse && (
                  <div className="text-info font-mono text-[10px] mt-0.5">{p.registro_tse}</div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
