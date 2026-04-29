import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
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
import { ArrowRight, BarChart3, TrendingDown, TrendingUp } from "lucide-react";

import { api } from "../lib/api";
import { Estado } from "../lib/types";

interface PontoAval {
  data: string;
  data_pesquisa?: string;
  pessoa_avaliada: { id: string; nome: string } | null;
  instituto: { nome: string };
  aprova: number | null;
  desaprova: number | null;
  otimo_bom: number | null;
  ruim_pessimo: number | null;
}

interface CandidatoCenario {
  nome: string;
  percentual: number;
  posicao: number | null;
  pessoa_id: string | null;
}

interface Cenario {
  label: string;
  candidatos: CandidatoCenario[];
}

export function PainelGovernador({ estado }: { estado: Estado }) {
  // Avaliação do governador atual
  const { data: avaliacoes = [] } = useQuery({
    queryKey: ["aval-gov-estado", estado.id],
    queryFn: async () =>
      (
        await api.get<PontoAval[]>("/pesquisas/historico/avaliacao-governo", {
          params: { nivel: "estadual", estado_id: estado.id },
        })
      ).data,
  });

  // Agregador estadual (intenção de voto)
  const { data: agregado } = useQuery({
    queryKey: ["agregador-estadual", estado.id],
    queryFn: async () =>
      (await api.get(`/pesquisas/agregador?estado_id=${estado.id}&cenario=estimulado`)).data,
  });

  // Identifica governador (1ª pessoa avaliada que aparecer)
  const governadorNome = avaliacoes.find((a) => a.pessoa_avaliada)?.pessoa_avaliada?.nome;

  // Série temporal consolidada por mês
  const serie = useMemo(() => {
    const mapa = new Map<string, any>();
    for (const a of avaliacoes) {
      const dt = a.data || a.data_pesquisa;
      if (!dt) continue;
      try {
        const chave = dt.slice(0, 7);
        if (!mapa.has(chave)) {
          mapa.set(chave, {
            chave,
            label: format(parseISO(dt), "MMM/yy", { locale: ptBR }),
            aprovaTotal: 0, aprovaN: 0,
            desaprovaTotal: 0, desaprovaN: 0,
            positivoTotal: 0, positivoN: 0,
            negativoTotal: 0, negativoN: 0,
          });
        }
        const ponto = mapa.get(chave);
        if (a.aprova != null) { ponto.aprovaTotal += a.aprova; ponto.aprovaN += 1; }
        if (a.desaprova != null) { ponto.desaprovaTotal += a.desaprova; ponto.desaprovaN += 1; }
        if (a.otimo_bom != null) { ponto.positivoTotal += a.otimo_bom; ponto.positivoN += 1; }
        if (a.ruim_pessimo != null) { ponto.negativoTotal += a.ruim_pessimo; ponto.negativoN += 1; }
      } catch { continue; }
    }
    return Array.from(mapa.values())
      .sort((a, b) => a.chave.localeCompare(b.chave))
      .map((p) => ({
        label: p.label,
        aprova: p.aprovaN ? Math.round((p.aprovaTotal / p.aprovaN) * 10) / 10 : null,
        desaprova: p.desaprovaN ? Math.round((p.desaprovaTotal / p.desaprovaN) * 10) / 10 : null,
        otimo_bom: p.positivoN ? Math.round((p.positivoTotal / p.positivoN) * 10) / 10 : null,
        ruim_pessimo: p.negativoN ? Math.round((p.negativoTotal / p.negativoN) * 10) / 10 : null,
      }));
  }, [avaliacoes]);

  const ultima = serie[serie.length - 1];
  const primeira = serie[0];
  const deltaAprov = ultima && primeira && ultima.aprova != null && primeira.aprova != null
    ? ultima.aprova - primeira.aprova
    : null;

  // Top candidatos governador (filtra ruído)
  const topCandidatos = (agregado?.candidatos || [])
    .filter((c: any) => !["branco", "nulo", "indeciso", "ns/nr", "outros"].some(x => c.nome.toLowerCase().includes(x)))
    .slice(0, 6);

  if (serie.length === 0 && topCandidatos.length === 0) {
    return (
      <div className="card text-center text-sm text-gray-500 py-6">
        Nenhuma pesquisa Quaest ou Real Time Big Data disponível para {estado.nome}.{" "}
        <Link to="/pesquisas/importar" className="text-info hover:underline">
          Importar JSON →
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Avaliação do governador atual */}
      {serie.length > 0 && (
        <div className="card">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 flex items-center gap-2">
                <BarChart3 className="h-4 w-4 text-info" />
                Avaliação do governo — {governadorNome || estado.nome}
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                Série histórica nas pesquisas Genial/Quaest do estado
              </p>
            </div>
            {ultima?.aprova != null && (
              <div className="text-right">
                <div className="flex items-baseline gap-2 justify-end">
                  <span className="text-3xl font-bold font-mono text-sucesso">{ultima.aprova}%</span>
                  {deltaAprov != null && (
                    <span className={`text-sm font-bold flex items-center ${deltaAprov >= 0 ? "text-sucesso" : "text-alerta"}`}>
                      {deltaAprov >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                      {Math.abs(deltaAprov).toFixed(1)}pp
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500">aprovação · variação na série</div>
              </div>
            )}
          </div>

          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={serie} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                <Tooltip formatter={(v: any) => [`${v}%`, ""]} contentStyle={{ fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} iconType="line" />
                <Line type="monotone" dataKey="aprova" stroke="#16A34A" strokeWidth={2.5} name="Aprova" connectNulls dot={{ r: 3 }} />
                <Line type="monotone" dataKey="desaprova" stroke="#DC2626" strokeWidth={2.5} name="Desaprova" connectNulls dot={{ r: 3 }} />
                <Line type="monotone" dataKey="otimo_bom" stroke="#2563EB" strokeWidth={2} name="Ótimo+Bom" connectNulls dot={{ r: 3 }} strokeDasharray="3 3" />
                <Line type="monotone" dataKey="ruim_pessimo" stroke="#EA580C" strokeWidth={2} name="Ruim+Péssimo" connectNulls dot={{ r: 3 }} strokeDasharray="3 3" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-2 pt-2 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
            <span>{serie.length} pontos · período: {primeira?.label} → {ultima?.label}</span>
            <span>{avaliacoes.length} registros</span>
          </div>
        </div>
      )}

      {/* Intenção de voto governador */}
      {topCandidatos.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-info" /> Intenção 1º turno — Governador {estado.sigla}
            </h2>
            {agregado?.meta && (
              <span className="text-xs text-gray-500">{agregado.meta.n_pesquisas} pesquisas no agregado</span>
            )}
          </div>

          <div className="space-y-2">
            {topCandidatos.map((c: any, i: number) => (
              <div key={c.nome} className="text-sm">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="font-medium text-gray-900 truncate flex-1">{c.nome}</span>
                  <span className="font-mono font-bold text-info ml-2">{c.estimativa}%</span>
                </div>
                <div className="relative h-2 bg-gray-100 rounded">
                  <div
                    className="absolute h-2 rounded transition-all"
                    style={{
                      width: `${Math.min(c.estimativa, 100)}%`,
                      backgroundColor: ["#DC2626", "#2563EB", "#16A34A", "#EA580C", "#7C3AED", "#0891B2"][i % 6],
                    }}
                  />
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">
                  {c.banda_inferior}-{c.banda_superior}% · {c.n_pesquisas} pesquisas
                </div>
              </div>
            ))}
          </div>

          <Link
            to={`/pesquisas/agregador?estado=${estado.id}`}
            className="text-xs text-info hover:underline mt-3 inline-flex items-center gap-1"
          >
            Ver agregador completo <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      )}
    </div>
  );
}
