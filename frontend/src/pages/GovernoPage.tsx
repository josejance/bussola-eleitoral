import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, NavLink, useParams } from "react-router-dom";
import clsx from "clsx";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  AlertTriangle,
  CheckCircle2,
  Play,
  RefreshCw,
  Sparkles,
  Users2,
} from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { api } from "../lib/api";

interface SumarioBase {
  total_parlamentares_avaliados: number;
  votacoes_consideradas: number;
  fidelidade_media: number;
  alta_fidelidade: number;
  media_fidelidade: number;
  baixa_fidelidade: number;
  rebeldes_da_base: number;
  rebeldes_lista: { nome: string; partido_sigla: string; fidelidade: number }[];
  infieis_oposicao: number;
  infieis_lista: { nome: string; partido_sigla: string; fidelidade: number }[];
}

interface Fidelidade {
  pessoa_id: string;
  nome: string;
  partido_sigla: string;
  partido_cor: string | null;
  total_votacoes: number;
  alinhados: number;
  contra: number;
  fidelidade_pct: number;
  votos_proxy_partido: number;
}

interface VotacaoLista {
  id: string;
  casa: string;
  data: string;
  ementa: string;
  tipo: string | null;
  numero: number | null;
  ano: number | null;
  posicionamento_governo: string;
  classificacao_ia_sugerida: string | null;
  classificacao_ia_confianca: number | null;
  tema: string | null;
  resultado: string | null;
  votos_sim: number | null;
  votos_nao: number | null;
}

const TABS = [
  { key: "base-aliada", label: "Base Aliada" },
  { key: "votacoes", label: "Votações" },
];

export function GovernoPage() {
  const { tab = "base-aliada" } = useParams();

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900">
          Governo Lula no Congresso
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Análise de fidelidade da base aliada e curadoria de votações relevantes.
        </p>
      </header>

      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {TABS.map((t) => (
          <NavLink
            key={t.key}
            to={`/governo/${t.key}`}
            className={({ isActive }) =>
              clsx(
                "px-4 py-2 text-sm font-medium border-b-2 transition",
                isActive ? "border-info text-info" : "border-transparent text-gray-600 hover:text-gray-900"
              )
            }
          >
            {t.label}
          </NavLink>
        ))}
      </div>

      {tab === "base-aliada" && <BaseAliadaPanel />}
      {tab === "votacoes" && <VotacoesPanel />}
    </div>
  );
}

// ===== Base Aliada =====

function BaseAliadaPanel() {
  const [meses, setMeses] = useState(12);
  const [partidoFiltro, setPartidoFiltro] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: sumario, isLoading: loadingSumario } = useQuery({
    queryKey: ["base-sumario", meses],
    queryFn: async () =>
      (await api.get<SumarioBase>("/governo/base-aliada/sumario", { params: { meses } })).data,
  });

  const { data: fidelidades = [], isLoading: loadingFid } = useQuery({
    queryKey: ["base-fidelidade", meses, partidoFiltro],
    queryFn: async () =>
      (
        await api.get<Fidelidade[]>("/governo/base-aliada/fidelidade", {
          params: { meses, partido_sigla: partidoFiltro || undefined, min_votacoes: 2 },
        })
      ).data,
  });

  const ingestaoMutation = useMutation({
    mutationFn: async (vars: { dias: number }) => {
      const params = new URLSearchParams({ dias: String(vars.dias), sincrono: "true" });
      return (await api.post(`/governo/ingestao/votacoes/run?${params}`)).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["base-sumario"] }),
  });

  const classMutation = useMutation({
    mutationFn: async () =>
      (await api.post("/governo/ingestao/votacoes/classificar?sincrono=true")).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["base-sumario"] }),
  });

  // Distribuição por partido
  const porPartido = fidelidades.reduce<Record<string, { total: number; soma: number; cor: string }>>((acc, f) => {
    if (!acc[f.partido_sigla]) acc[f.partido_sigla] = { total: 0, soma: 0, cor: f.partido_cor || "#6B7280" };
    acc[f.partido_sigla].total++;
    acc[f.partido_sigla].soma += f.fidelidade_pct;
    return acc;
  }, {});

  const partidosOrdenados = Object.entries(porPartido)
    .map(([sigla, v]) => ({ sigla, total: v.total, fidelidade_media: v.soma / v.total, cor: v.cor }))
    .sort((a, b) => b.total - a.total);

  return (
    <div className="space-y-4">
      {/* Cards principais */}
      {sumario && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="card !p-3">
            <div className="text-xs text-gray-500 uppercase">Parlamentares avaliados</div>
            <div className="text-3xl font-bold font-mono text-info">{sumario.total_parlamentares_avaliados}</div>
            <div className="text-xs text-gray-500">{sumario.votacoes_consideradas} votações</div>
          </div>
          <div className="card !p-3">
            <div className="text-xs text-gray-500 uppercase">Fidelidade média</div>
            <div className="text-3xl font-bold font-mono text-info">{sumario.fidelidade_media}%</div>
            <div className="text-xs text-gray-500">com governo</div>
          </div>
          <div className="card !p-3">
            <div className="text-xs text-gray-500 uppercase">Alta fidelidade (≥70%)</div>
            <div className="text-3xl font-bold font-mono text-sucesso">{sumario.alta_fidelidade}</div>
            <div className="text-xs text-gray-500">{sumario.media_fidelidade} média + {sumario.baixa_fidelidade} baixa</div>
          </div>
          <div className="card !p-3">
            <div className="text-xs text-gray-500 uppercase">Rebeldes da base</div>
            <div className="text-3xl font-bold font-mono text-alerta">{sumario.rebeldes_da_base}</div>
            <div className="text-xs text-gray-500">{sumario.infieis_oposicao} infiéis na oposição</div>
          </div>
        </div>
      )}

      {/* Sem dados */}
      {sumario && sumario.votacoes_consideradas === 0 && (
        <div className="card bg-yellow-50 border-yellow-200">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold mb-1">Sem dados de fidelidade</h3>
              <p className="text-sm text-gray-700 mb-3">
                Não há votações com posicionamento_governo classificado nos últimos {meses} meses.
                Para gerar dados, rode a ingestão e classificação:
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => ingestaoMutation.mutate({ dias: 90 })}
                  disabled={ingestaoMutation.isPending}
                  className="btn-primary text-sm"
                >
                  <Play className="h-4 w-4" /> 1. Ingerir últimas votações (90 dias)
                </button>
                <button
                  onClick={() => classMutation.mutate()}
                  disabled={classMutation.isPending}
                  className="btn-secondary text-sm"
                >
                  <Sparkles className="h-4 w-4" /> 2. Classificar via IA
                </button>
              </div>
              {(ingestaoMutation.data || classMutation.data) && (
                <pre className="mt-2 text-xs bg-white p-2 rounded border max-h-32 overflow-y-auto">
                  {JSON.stringify(ingestaoMutation.data || classMutation.data, null, 2)}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Donut por partido */}
        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
            Composição por partido
          </h2>
          {partidosOrdenados.length > 0 ? (
            <>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={partidosOrdenados}
                      dataKey="total"
                      nameKey="sigla"
                      cx="50%"
                      cy="50%"
                      innerRadius={40}
                      outerRadius={80}
                      paddingAngle={1}
                      label={(entry) => entry.sigla}
                      labelLine={false}
                    >
                      {partidosOrdenados.map((p) => (
                        <Cell key={p.sigla} fill={p.cor} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: any, n: any) => [`${v} parlamentares`, n]} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1 mt-2 max-h-40 overflow-y-auto">
                {partidosOrdenados.map((p) => (
                  <button
                    key={p.sigla}
                    onClick={() => setPartidoFiltro(partidoFiltro === p.sigla ? "" : p.sigla)}
                    className={`w-full flex items-center gap-2 text-xs px-1.5 py-1 rounded hover:bg-gray-50 ${
                      partidoFiltro === p.sigla ? "bg-blue-50" : ""
                    }`}
                  >
                    <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: p.cor }} />
                    <span className="font-mono font-bold w-12">{p.sigla}</span>
                    <span className="text-gray-500 flex-1 text-left">{p.total} parl.</span>
                    <span className="font-mono font-bold">{p.fidelidade_media.toFixed(0)}%</span>
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className="text-sm text-gray-400 py-8 text-center">Sem dados</div>
          )}
        </div>

        {/* Ranking */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700">
              Ranking de fidelidade {partidoFiltro && `· filtro: ${partidoFiltro}`}
            </h2>
            <select
              value={meses}
              onChange={(e) => setMeses(parseInt(e.target.value))}
              className="input !py-1 !text-xs max-w-[180px]"
            >
              <option value={3}>Últimos 3 meses</option>
              <option value={6}>Últimos 6 meses</option>
              <option value={12}>Últimos 12 meses</option>
              <option value={24}>Últimos 24 meses</option>
            </select>
          </div>
          {loadingFid ? (
            <div className="text-gray-400 text-sm">Calculando…</div>
          ) : fidelidades.length === 0 ? (
            <div className="text-sm text-gray-500 py-8 text-center">
              Sem parlamentares avaliados. Faça a ingestão de votações primeiro.
            </div>
          ) : (
            <div className="space-y-1 max-h-[500px] overflow-y-auto">
              {fidelidades.slice(0, 100).map((f, i) => (
                <Link
                  key={f.pessoa_id}
                  to={`/pessoas/${f.pessoa_id}`}
                  className="flex items-center gap-2 text-sm hover:bg-gray-50 px-2 py-1 rounded"
                >
                  <span className="font-mono text-xs text-gray-400 w-6">{i + 1}</span>
                  <span
                    className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                    style={{ backgroundColor: f.partido_cor || "#6B7280" }}
                  />
                  <span className="font-mono font-bold w-12 text-xs">{f.partido_sigla}</span>
                  <span className="font-medium flex-1 truncate">{f.nome}</span>
                  <span className="text-xs text-gray-400">
                    {f.total_votacoes} vot.
                  </span>
                  <FidelidadeBadge pct={f.fidelidade_pct} />
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Listas críticas */}
      {sumario && (sumario.rebeldes_lista.length > 0 || sumario.infieis_lista.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sumario.rebeldes_lista.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-alerta mb-2">
                ⚠ Rebeldes da base ({sumario.rebeldes_da_base})
              </h3>
              <p className="text-xs text-gray-500 mb-2">
                Parlamentares de partidos da base mas com fidelidade &lt; 50%
              </p>
              <ul className="space-y-1 text-sm">
                {sumario.rebeldes_lista.map((r, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="font-medium flex-1">{r.nome}</span>
                    <span className="font-mono text-xs">{r.partido_sigla}</span>
                    <FidelidadeBadge pct={r.fidelidade} />
                  </li>
                ))}
              </ul>
            </div>
          )}
          {sumario.infieis_lista.length > 0 && (
            <div className="card">
              <h3 className="text-sm font-semibold text-sucesso mb-2">
                ★ Aliados na oposição ({sumario.infieis_oposicao})
              </h3>
              <p className="text-xs text-gray-500 mb-2">
                Parlamentares de partidos fora da base com fidelidade ≥ 70%
              </p>
              <ul className="space-y-1 text-sm">
                {sumario.infieis_lista.map((r, i) => (
                  <li key={i} className="flex items-center gap-2">
                    <span className="font-medium flex-1">{r.nome}</span>
                    <span className="font-mono text-xs">{r.partido_sigla}</span>
                    <FidelidadeBadge pct={r.fidelidade} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function FidelidadeBadge({ pct }: { pct: number }) {
  const cor = pct >= 70 ? "text-sucesso bg-green-50" : pct >= 40 ? "text-atencao bg-yellow-50" : "text-alerta bg-red-50";
  return <span className={`badge ${cor} text-xs font-mono w-14 text-center`}>{pct.toFixed(0)}%</span>;
}

// ===== Votações =====

function VotacoesPanel() {
  const [posicionamento, setPosicionamento] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: votacoes = [], isLoading } = useQuery({
    queryKey: ["governo-votacoes", posicionamento],
    queryFn: async () =>
      (
        await api.get<VotacaoLista[]>("/governo/votacoes", {
          params: { posicionamento: posicionamento || undefined, limit: 100 },
        })
      ).data,
  });

  const classMutation = useMutation({
    mutationFn: async () =>
      (await api.post("/governo/ingestao/votacoes/classificar?sincrono=true&limit=50")).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["governo-votacoes"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3 flex-wrap">
        <div>
          <label className="label !text-xs">Filtrar por posicionamento</label>
          <select
            value={posicionamento}
            onChange={(e) => setPosicionamento(e.target.value)}
            className="input !py-1 !text-sm"
          >
            <option value="">Todos</option>
            <option value="a_favor">A favor</option>
            <option value="contra">Contra</option>
            <option value="liberada">Liberada</option>
            <option value="sem_orientacao">Sem orientação</option>
            <option value="desconhecido">Desconhecido (precisa classificar)</option>
          </select>
        </div>
        <button
          onClick={() => classMutation.mutate()}
          disabled={classMutation.isPending}
          className="btn-secondary text-sm"
        >
          <Sparkles className="h-4 w-4" /> Classificar pendentes via IA
        </button>
        <span className="ml-auto text-sm text-gray-500">{votacoes.length} votações</span>
      </div>

      {classMutation.data && (
        <div className="card !p-3 bg-green-50 border-green-200 text-sm">
          <CheckCircle2 className="inline h-4 w-4 text-sucesso mr-1" />
          {classMutation.data.classificadas} classificadas, {classMutation.data.auto_aprovadas} auto-aprovadas
        </div>
      )}

      {isLoading ? (
        <div className="text-gray-400">Carregando…</div>
      ) : votacoes.length === 0 ? (
        <div className="card text-center text-gray-500 py-8">Nenhuma votação encontrada.</div>
      ) : (
        <div className="card !p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2 text-left">Data</th>
                <th className="px-3 py-2 text-left">Tipo/Nº</th>
                <th className="px-3 py-2 text-left">Ementa</th>
                <th className="px-3 py-2 text-left">Posicionamento</th>
                <th className="px-3 py-2 text-left">Resultado</th>
                <th className="px-3 py-2 text-right">Sim/Não</th>
              </tr>
            </thead>
            <tbody>
              {votacoes.map((v) => (
                <tr key={v.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-3 py-1.5 text-xs font-mono text-gray-500">
                    {format(parseISO(v.data), "dd/MM/yy", { locale: ptBR })}
                  </td>
                  <td className="px-3 py-1.5 text-xs font-mono">
                    {v.tipo} {v.numero ? `${v.numero}/${v.ano}` : ""}
                  </td>
                  <td className="px-3 py-1.5 text-xs max-w-md truncate" title={v.ementa}>
                    {v.ementa}
                  </td>
                  <td className="px-3 py-1.5">
                    <PosicionamentoBadge posicao={v.posicionamento_governo} />
                    {v.classificacao_ia_sugerida && v.posicionamento_governo === "desconhecido" && (
                      <span className="text-xs text-gray-500 ml-1">
                        IA: {v.classificacao_ia_sugerida} ({((v.classificacao_ia_confianca || 0) * 100).toFixed(0)}%)
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-1.5 text-xs">
                    {v.resultado === "aprovado" ? (
                      <span className="text-sucesso">aprovado</span>
                    ) : v.resultado === "rejeitado" ? (
                      <span className="text-alerta">rejeitado</span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-1.5 text-right text-xs font-mono">
                    {v.votos_sim}/{v.votos_nao}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function PosicionamentoBadge({ posicao }: { posicao: string }) {
  const map: Record<string, { label: string; cor: string }> = {
    a_favor: { label: "A favor", cor: "bg-green-50 text-green-700" },
    contra: { label: "Contra", cor: "bg-red-50 text-red-700" },
    liberada: { label: "Liberada", cor: "bg-blue-50 text-blue-700" },
    sem_orientacao: { label: "Sem orientação", cor: "bg-gray-100 text-gray-700" },
    desconhecido: { label: "Pendente", cor: "bg-yellow-50 text-yellow-700" },
  };
  const m = map[posicao] || { label: posicao, cor: "bg-gray-100 text-gray-700" };
  return <span className={`badge ${m.cor} text-xs`}>{m.label}</span>;
}
