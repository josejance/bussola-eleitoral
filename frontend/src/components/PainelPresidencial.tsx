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
import { ArrowRight, BarChart3, Sparkles, TrendingDown, TrendingUp } from "lucide-react";

import { api } from "../lib/api";

interface PontoAval {
  data: string;
  data_pesquisa?: string;
  pessoa_avaliada: { nome: string } | null;
  instituto: { nome: string };
  aprova: number | null;
  desaprova: number | null;
  otimo_bom: number | null;
}

export function PainelPresidencial() {
  // Aprovação Lula nacional
  const { data: aprovLula = [] } = useQuery({
    queryKey: ["aprov-lula"],
    queryFn: async () =>
      (
        await api.get<PontoAval[]>("/pesquisas/historico/avaliacao-governo", {
          params: { nivel: "presidencial" },
        })
      ).data,
  });

  // Agregador nacional (presidencial)
  const { data: agregado } = useQuery({
    queryKey: ["agregador-nacional"],
    queryFn: async () => (await api.get("/pesquisas/agregador?cenario=estimulado")).data,
  });

  // Monte Carlo
  const { data: monteCarlo } = useQuery({
    queryKey: ["monte-carlo-nacional"],
    queryFn: async () => (await api.get("/pesquisas/agregador/monte-carlo?n_simulacoes=5000")).data,
  });

  // Série da aprovação consolidada por mês (Lula apenas)
  const serieAprov = useMemo(() => {
    const mapa = new Map<string, any>();
    for (const a of aprovLula) {
      // Filtra apenas Lula
      if (a.pessoa_avaliada && !a.pessoa_avaliada.nome.toLowerCase().includes("lula")) continue;
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
          });
        }
        const ponto = mapa.get(chave);
        if (a.aprova != null) { ponto.aprovaTotal += a.aprova; ponto.aprovaN += 1; }
        if (a.desaprova != null) { ponto.desaprovaTotal += a.desaprova; ponto.desaprovaN += 1; }
        if (a.otimo_bom != null) { ponto.positivoTotal += a.otimo_bom; ponto.positivoN += 1; }
      } catch { continue; }
    }
    return Array.from(mapa.values())
      .sort((a, b) => a.chave.localeCompare(b.chave))
      .map((p) => ({
        label: p.label,
        aprova: p.aprovaN ? Math.round((p.aprovaTotal / p.aprovaN) * 10) / 10 : null,
        desaprova: p.desaprovaN ? Math.round((p.desaprovaTotal / p.desaprovaN) * 10) / 10 : null,
        otimo_bom: p.positivoN ? Math.round((p.positivoTotal / p.positivoN) * 10) / 10 : null,
      }));
  }, [aprovLula]);

  // Última e variação
  const ultimaAprov = serieAprov[serieAprov.length - 1];
  const penultimaAprov = serieAprov[serieAprov.length - 2];
  const deltaAprov = ultimaAprov && penultimaAprov && ultimaAprov.aprova != null && penultimaAprov.aprova != null
    ? ultimaAprov.aprova - penultimaAprov.aprova
    : null;

  // Top 5 candidatos do agregado (filtrando ruído)
  const topCandidatos = (agregado?.candidatos || [])
    .filter((c: any) => !["branco", "nulo", "indeciso", "ns/nr", "não vai", "outros"].some(x => c.nome.toLowerCase().includes(x)))
    .slice(0, 6);

  // Cenários de 2T mais prováveis
  const cenarios2T = (monteCarlo?.cenarios_2t || []).slice(0, 4);

  if (serieAprov.length === 0 && topCandidatos.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Linha 1: Aprovação Lula (peça principal) */}
      <div className="card">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-info" />
              Aprovação do Governo Federal — Presidente Lula
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              Série mensal Genial/Quaest · pesquisas registradas no TSE
            </p>
          </div>
          {ultimaAprov?.aprova != null && (
            <div className="text-right">
              <div className="flex items-baseline gap-2 justify-end">
                <span className="text-4xl font-bold font-mono text-sucesso">{ultimaAprov.aprova}%</span>
                {deltaAprov != null && (
                  <span className={`text-sm font-bold flex items-center ${deltaAprov >= 0 ? "text-sucesso" : "text-alerta"}`}>
                    {deltaAprov >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                    {Math.abs(deltaAprov).toFixed(1)}pp
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-500">aprovação · último mês</div>
              {ultimaAprov.desaprova != null && (
                <div className="text-xs text-alerta mt-1">
                  {ultimaAprov.desaprova}% desaprova
                </div>
              )}
            </div>
          )}
        </div>

        {serieAprov.length > 0 ? (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={serieAprov} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
                <Tooltip formatter={(v: any) => [`${v}%`, ""]} contentStyle={{ fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} iconType="line" />
                <Line type="monotone" dataKey="aprova" stroke="#16A34A" strokeWidth={3} name="Aprova" connectNulls dot={{ r: 4 }} />
                <Line type="monotone" dataKey="desaprova" stroke="#DC2626" strokeWidth={3} name="Desaprova" connectNulls dot={{ r: 4 }} />
                <Line type="monotone" dataKey="otimo_bom" stroke="#2563EB" strokeWidth={2} name="Ótimo+Bom" connectNulls dot={{ r: 3 }} strokeDasharray="3 3" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-8">
            Sem dados de aprovação federal. Importe pesquisas Quaest em <Link to="/pesquisas/importar" className="text-info hover:underline">/pesquisas/importar</Link>.
          </p>
        )}

        {ultimaAprov && (
          <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
            <span>{serieAprov.length} pontos · {aprovLula.length > 0 ? aprovLula[0].instituto.nome : "Quaest"}</span>
            <Link to="/pesquisas" className="text-info hover:underline inline-flex items-center gap-1">
              Ver todas as pesquisas <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        )}
      </div>

      {/* Linha 2: 2 cards lado a lado — intenção 1T e cenários 2T */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Intenção de voto presidencial — agregado 1T */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-info" /> Intenção 1º turno (agregado)
            </h2>
            {agregado?.meta && (
              <span className="text-xs text-gray-500">{agregado.meta.n_pesquisas} pesquisas</span>
            )}
          </div>

          {topCandidatos.length === 0 ? (
            <p className="text-sm text-gray-400">Sem dados disponíveis.</p>
          ) : (
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
                    intervalo: {c.banda_inferior}-{c.banda_superior}% · {c.n_pesquisas} pesquisas
                  </div>
                </div>
              ))}
            </div>
          )}

          <Link to="/pesquisas/agregador" className="text-xs text-info hover:underline mt-3 inline-flex items-center gap-1">
            Ver agregador completo <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {/* Cenários de 2º turno — Monte Carlo */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-info" /> Cenários 2º turno (Monte Carlo)
            </h2>
            {monteCarlo?.n_simulacoes && (
              <span className="text-xs text-gray-500">{monteCarlo.n_simulacoes.toLocaleString("pt-BR")} sim.</span>
            )}
          </div>

          {cenarios2T.length === 0 ? (
            <p className="text-sm text-gray-400">Sem dados suficientes para simulação.</p>
          ) : (
            <div className="space-y-3">
              {cenarios2T.map((c: any, i: number) => (
                <div key={i} className="border-l-2 border-info pl-3">
                  <div className="flex items-center justify-between text-sm mb-1">
                    <div>
                      <span className="font-medium">{c.candidato_a}</span>
                      <span className="text-gray-400 mx-1">×</span>
                      <span className="font-medium">{c.candidato_b}</span>
                    </div>
                    <span className="font-mono font-bold text-info text-base">{c.probabilidade}%</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    favorito: <span className="font-medium text-sucesso">{c.favorito}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <Link to="/pesquisas/agregador" className="text-xs text-info hover:underline mt-3 inline-flex items-center gap-1">
            Ver simulação completa <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </div>
    </div>
  );
}
