import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  ArrowLeft,
  ArrowLeftRight,
  Calendar,
  ExternalLink,
  FileText,
  Newspaper,
  Sparkles,
  TrendingUp,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api } from "../lib/api";
import { Pesquisa } from "../lib/types";

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

const CORES = ["#DC2626", "#2563EB", "#16A34A", "#EA580C", "#7C3AED", "#0891B2", "#DB2777", "#65A30D", "#CA8A04", "#0F172A"];

export function PesquisaDetalhePage() {
  const { id } = useParams();
  const [cenarioSelecionado, setCenarioSelecionado] = useState<string | null>(null);

  const { data: pesquisa } = useQuery({
    queryKey: ["pesquisa", id],
    queryFn: async () => (await api.get<Pesquisa>(`/pesquisas/${id}`)).data,
    enabled: !!id,
  });

  const { data: cenariosData } = useQuery({
    queryKey: ["pesquisa-cenarios", id],
    queryFn: async () =>
      (await api.get<{ cenarios: Cenario[] }>(`/pesquisas/${id}/cenarios`)).data,
    enabled: !!id,
  });

  const { data: avaliacoes = [] } = useQuery({
    queryKey: ["pesquisa-aval-historico", id, pesquisa?.estado_id],
    queryFn: async () => {
      // Pega histórico de avaliações desta pesquisa específica (séries internas)
      const params: any = {};
      if (pesquisa?.estado_id) {
        params.estado_id = pesquisa.estado_id;
        params.nivel = "estadual";
      } else {
        params.nivel = "presidencial";
      }
      return (await api.get(`/pesquisas/historico/avaliacao-governo`, { params })).data;
    },
    enabled: !!pesquisa,
  });

  const { data: dadosBrutos } = useQuery({
    queryKey: ["pesquisa-brutos", id],
    queryFn: async () => {
      try {
        return (await api.get(`/admin/pesquisas/${id}/dados-brutos`)).data;
      } catch {
        return null;
      }
    },
    enabled: !!id,
    retry: false,
  });

  const cenarios = cenariosData?.cenarios || [];
  const cenarioAtual = useMemo(() => {
    if (!cenarios.length) return null;
    if (cenarioSelecionado) return cenarios.find((c) => c.label === cenarioSelecionado) || cenarios[0];
    return cenarios[0];
  }, [cenarios, cenarioSelecionado]);

  // Filtra avaliações desta pesquisa específica
  const avaliacoesDestaPesquisa = avaliacoes.filter((a: any) => a.pesquisa_id === id);

  if (!pesquisa) {
    return <div className="p-6 text-gray-400">Carregando…</div>;
  }

  return (
    <div className="p-6 max-w-7xl">
      <Link to="/pesquisas" className="text-xs text-gray-500 hover:text-info inline-flex items-center gap-1 mb-2">
        <ArrowLeft className="h-3 w-3" /> Voltar para Pesquisas
      </Link>

      <header className="mb-4">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          {pesquisa.registro_tse && (
            <span className="badge bg-purple-50 text-purple-700 font-mono text-xs">
              {pesquisa.registro_tse}
            </span>
          )}
          <span className="badge bg-blue-50 text-info capitalize">{pesquisa.tipo_cenario}</span>
          <span className="badge bg-gray-100 text-gray-700 capitalize">{pesquisa.metodologia}</span>
          {pesquisa.abrangencia && (
            <span className="badge bg-gray-100 text-gray-700 capitalize">{pesquisa.abrangencia}</span>
          )}
        </div>
        <h1 className="text-2xl font-display font-semibold text-gray-900">
          {pesquisa.contratante || "Pesquisa"} —{" "}
          {pesquisa.data_fim_campo &&
            format(parseISO(pesquisa.data_fim_campo), "dd MMM yyyy", { locale: ptBR })}
        </h1>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Coluna esquerda — meta */}
        <div className="space-y-3">
          {/* Especificações */}
          <div className="card !p-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-700 mb-2 flex items-center gap-1">
              <Calendar className="h-3 w-3" /> Especificações
            </h2>
            <dl className="space-y-1.5 text-xs">
              <Item label="Período">
                {pesquisa.data_inicio_campo &&
                  format(parseISO(pesquisa.data_inicio_campo), "dd/MM", { locale: ptBR })}
                {pesquisa.data_inicio_campo && pesquisa.data_fim_campo && " a "}
                {pesquisa.data_fim_campo &&
                  format(parseISO(pesquisa.data_fim_campo), "dd/MM/yyyy", { locale: ptBR })}
              </Item>
              <Item label="Amostra">{pesquisa.amostra?.toLocaleString("pt-BR") || "—"}</Item>
              <Item label="Margem">±{pesquisa.margem_erro}pp</Item>
              <Item label="Turno">{pesquisa.turno_referencia || "—"}</Item>
              <Item label="Status">{pesquisa.status_revisao}</Item>
            </dl>
          </div>

          {/* Cenários disponíveis */}
          {cenarios.length > 0 && (
            <div className="card !p-3">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-700 mb-2">
                Cenários ({cenarios.length})
              </h2>
              <div className="space-y-1">
                {cenarios.map((c) => (
                  <button
                    key={c.label}
                    onClick={() => setCenarioSelecionado(c.label)}
                    className={`w-full text-left text-xs px-2 py-1 rounded ${
                      (cenarioAtual?.label || cenarios[0].label) === c.label
                        ? "bg-info text-white"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <div className="font-medium">{c.label}</div>
                    <div className="text-[10px] opacity-75">{c.candidatos.length} candidatos</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Análise IA */}
          {dadosBrutos?.analise_ia && (
            <div className="card !p-3">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-700 mb-2 flex items-center gap-1">
                <Sparkles className="h-3 w-3" /> Análise IA
              </h2>
              <p className="text-xs text-gray-700">{dadosBrutos.analise_ia.resumo_executivo}</p>
            </div>
          )}

          {/* Ações */}
          <div className="card !p-3 space-y-2 text-sm">
            <Link to={`/pesquisas/comparador?ids=${pesquisa.id}`} className="text-info hover:underline flex items-center gap-1">
              <ArrowLeftRight className="h-3 w-3" /> Comparar com outras
            </Link>
            <Link to={`/pesquisas/agregador${pesquisa.estado_id ? `?estado=${pesquisa.estado_id}` : ""}`} className="text-info hover:underline flex items-center gap-1">
              <TrendingUp className="h-3 w-3" /> Ver no agregador
            </Link>
          </div>
        </div>

        {/* Coluna central — gráfico do cenário atual */}
        <div className="lg:col-span-3 space-y-4">
          {cenarioAtual && cenarioAtual.candidatos.length > 0 && (
            <div className="card">
              <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Users className="h-4 w-4 text-info" /> {cenarioAtual.label}
              </h2>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={cenarioAtual.candidatos}
                    layout="vertical"
                    margin={{ left: 130, right: 30 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                    <YAxis type="category" dataKey="nome" tick={{ fontSize: 10, fill: "#374151" }} width={170} />
                    <Tooltip formatter={(v: any) => [`${v}%`, ""]} />
                    <Bar dataKey="percentual" radius={[0, 4, 4, 0]}>
                      {cenarioAtual.candidatos.map((_, i) => (
                        <Cell key={i} fill={CORES[i % CORES.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Tabela */}
              <table className="w-full text-sm mt-4">
                <thead className="border-b border-gray-200 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="text-left py-2">#</th>
                    <th className="text-left py-2">Candidato</th>
                    <th className="text-right py-2">%</th>
                  </tr>
                </thead>
                <tbody>
                  {cenarioAtual.candidatos.map((c, i) => (
                    <tr key={i} className="border-b border-gray-100">
                      <td className="py-1.5 font-mono text-gray-500 w-8">{c.posicao || i + 1}</td>
                      <td className="py-1.5 font-medium">
                        {c.pessoa_id ? (
                          <Link to={`/pessoas/${c.pessoa_id}`} className="text-info hover:underline">
                            {c.nome}
                          </Link>
                        ) : (
                          c.nome
                        )}
                      </td>
                      <td className="py-1.5 text-right font-mono font-bold">{c.percentual}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Comparação visual entre todos cenários (top 5 candidatos) */}
          {cenarios.length > 1 && (
            <div className="card">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                Comparação entre cenários ({cenarios.filter(c => c.label.startsWith("1T")).length} cenários de 1º turno)
              </h2>
              <ComparacaoCenariosChart cenarios={cenarios.filter(c => c.label.startsWith("1T"))} />
            </div>
          )}

          {/* Avaliação de governo (se tiver série temporal nesta pesquisa) */}
          {avaliacoesDestaPesquisa.length > 0 && (
            <div className="card">
              <h2 className="text-sm font-semibold text-gray-700 mb-3">
                Avaliação de governo nesta pesquisa ({avaliacoesDestaPesquisa.length} pontos da série)
              </h2>
              <SerieAvaliacaoChart avaliacoes={avaliacoesDestaPesquisa} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Item({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <dt className="text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="font-medium text-gray-900">{children}</dd>
    </div>
  );
}

function ComparacaoCenariosChart({ cenarios }: { cenarios: Cenario[] }) {
  // Pega top 5 candidatos da soma total
  const totaisPorNome = new Map<string, number>();
  cenarios.forEach((c) =>
    c.candidatos.forEach((cand) => {
      totaisPorNome.set(cand.nome, (totaisPorNome.get(cand.nome) || 0) + cand.percentual);
    })
  );
  const topCandidatos = Array.from(totaisPorNome.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([nome]) => nome);

  // Filtra ruído
  const candidatosLimpos = topCandidatos.filter(
    (n) => !["Branco/Nulo/Não vai votar", "Indecisos", "Outros"].some((x) => n.includes(x))
  ).slice(0, 5);

  const data = cenarios.map((c) => {
    const ponto: any = { cenario: c.label.replace("1T - ", "") };
    candidatosLimpos.forEach((nome) => {
      const cand = c.candidatos.find((x) => x.nome === nome);
      if (cand) ponto[nome] = cand.percentual;
    });
    return ponto;
  });

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 20, left: -10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="cenario" tick={{ fontSize: 10 }} angle={-15} textAnchor="end" height={60} />
          <YAxis tick={{ fontSize: 10 }} domain={[0, 50]} tickFormatter={(v) => `${v}%`} />
          <Tooltip formatter={(v: any) => [`${v}%`, ""]} contentStyle={{ fontSize: 11 }} />
          {candidatosLimpos.map((nome, i) => (
            <Line
              key={nome}
              type="monotone"
              dataKey={nome}
              stroke={CORES[i % CORES.length]}
              strokeWidth={2}
              dot={{ r: 4 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SerieAvaliacaoChart({ avaliacoes }: { avaliacoes: any[] }) {
  // Agrupa por data — uma linha aprovação outra desaprovação outra ótimo+bom
  const dataMap = new Map<string, any>();
  avaliacoes.forEach((a) => {
    const k = a.data;
    if (!dataMap.has(k)) {
      dataMap.set(k, { data: k, dataLabel: format(parseISO(k), "MMM/yy", { locale: ptBR }) });
    }
    const ponto = dataMap.get(k);
    if (a.aprova !== null) ponto.aprova = a.aprova;
    if (a.desaprova !== null) ponto.desaprova = a.desaprova;
    if (a.otimo_bom !== null) ponto.otimo_bom = a.otimo_bom;
  });
  const dataArr = Array.from(dataMap.values()).sort((a, b) => a.data.localeCompare(b.data));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={dataArr} margin={{ top: 10, right: 20, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="dataLabel" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
          <Tooltip formatter={(v: any) => [`${v}%`, ""]} contentStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="aprova" stroke="#16A34A" strokeWidth={2.5} name="Aprova" connectNulls />
          <Line type="monotone" dataKey="desaprova" stroke="#DC2626" strokeWidth={2.5} name="Desaprova" connectNulls />
          <Line type="monotone" dataKey="otimo_bom" stroke="#2563EB" strokeWidth={2.5} name="Ótimo+Bom" connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
