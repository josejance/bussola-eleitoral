import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Database,
  FileBarChart,
  MessageSquare,
  Newspaper,
  Play,
  RefreshCw,
  Users2,
  X,
} from "lucide-react";

import { api } from "../lib/api";

interface FonteStatus {
  id: string;
  nome: string;
  url_feed: string;
  url_site: string | null;
  tipo: string;
  abrangencia: string;
  espectro_editorial: string | null;
  confiabilidade: number;
  peso_editorial: number;
  frequencia_polling_minutos: number;
  ativo: boolean;
  ultimo_polling: string | null;
  ultimo_sucesso: string | null;
  total_materias_capturadas: number;
  total_materias_aproveitadas: number;
  esta_em_falha: boolean;
}

interface VisaoGeral {
  rss: { fontes_ativas: number; materias_total: number; materias_aproveitadas: number; ultimo_polling: string | null };
  camara: { deputados_cadastrados: number; deputados_ativos: number };
  senado: { senadores_cadastrados: number; senadores_ativos: number };
  tse: { candidaturas_total: number; pessoas_total: number; por_eleicao: { ano: number; total: number }[] };
  pesquisas: { eleitorais: number; tematicas: number };
}

const TABS = [
  { key: "visao", label: "Visão Geral", icon: Database },
  { key: "rss", label: "RSS / Mídia", icon: Newspaper },
  { key: "camara", label: "Câmara", icon: Users2 },
  { key: "senado", label: "Senado", icon: Building2 },
  { key: "tse", label: "TSE Histórico", icon: FileBarChart },
  { key: "pesquisas", label: "Pesquisas (JSON)", icon: MessageSquare },
];

export function AdminIngestaoPage() {
  const [tab, setTab] = useState("visao");

  return (
    <div className="p-6">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900">Ingestão de Dados</h1>
        <p className="text-sm text-gray-500 mt-1">
          Workers automáticos e disparo manual para todas as fontes de dados
        </p>
      </header>

      <div className="flex gap-1 mb-4 border-b border-gray-200 overflow-x-auto">
        {TABS.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition whitespace-nowrap flex items-center gap-1.5 ${
                tab === t.key ? "border-info text-info" : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              <Icon className="h-4 w-4" /> {t.label}
            </button>
          );
        })}
      </div>

      {tab === "visao" && <VisaoGeralPanel />}
      {tab === "rss" && <RSSPanel />}
      {tab === "camara" && <CamaraPanel />}
      {tab === "senado" && <SenadoPanel />}
      {tab === "tse" && <TSEPanel />}
      {tab === "pesquisas" && <PesquisasPanel />}
    </div>
  );
}

// ===== Visão Geral =====

function VisaoGeralPanel() {
  const { data, refetch } = useQuery({
    queryKey: ["ingestao-visao"],
    queryFn: async () => (await api.get<VisaoGeral>("/admin/ingestao/visao-geral")).data,
    refetchInterval: 15_000,
  });

  if (!data) return <div className="text-gray-400">Carregando…</div>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <CardStats
          icon={Newspaper}
          titulo="RSS / Mídia"
          principal={data.rss.fontes_ativas}
          principal_label="fontes ativas"
          secundarios={[
            { label: "matérias capturadas", valor: data.rss.materias_total.toLocaleString("pt-BR") },
            { label: "aproveitadas (filtro)", valor: data.rss.materias_aproveitadas.toLocaleString("pt-BR") },
          ]}
          rodape={data.rss.ultimo_polling ? `Último polling: ${data.rss.ultimo_polling}` : "Nunca rodou"}
          cor="#2563EB"
        />
        <CardStats
          icon={Users2}
          titulo="Câmara dos Deputados"
          principal={data.camara.deputados_ativos}
          principal_label="deputados em exercício"
          secundarios={[
            { label: "objetivo (Câmara)", valor: "513" },
            { label: "cobertura", valor: `${Math.round((data.camara.deputados_ativos / 513) * 100)}%` },
          ]}
          rodape="API: dadosabertos.camara.leg.br"
          cor="#16A34A"
        />
        <CardStats
          icon={Building2}
          titulo="Senado Federal"
          principal={data.senado.senadores_ativos}
          principal_label="senadores em exercício"
          secundarios={[
            { label: "objetivo (Senado)", valor: "81" },
            { label: "cobertura", valor: `${Math.round((data.senado.senadores_ativos / 81) * 100)}%` },
          ]}
          rodape="API: legis.senado.leg.br/dadosabertos"
          cor="#7C3AED"
        />
        <CardStats
          icon={FileBarChart}
          titulo="TSE Dados Abertos"
          principal={data.tse.candidaturas_total.toLocaleString("pt-BR")}
          principal_label="candidaturas históricas"
          secundarios={[
            { label: "pessoas únicas", valor: data.tse.pessoas_total.toLocaleString("pt-BR") },
            ...data.tse.por_eleicao.slice(0, 3).map((e) => ({
              label: `eleição ${e.ano}`,
              valor: e.total.toLocaleString("pt-BR"),
            })),
          ]}
          rodape="cdn.tse.jus.br/estatistica/sead/odsele"
          cor="#EA580C"
        />
        <CardStats
          icon={MessageSquare}
          titulo="Pesquisas (JSON)"
          principal={data.pesquisas.eleitorais + data.pesquisas.tematicas}
          principal_label="pesquisas importadas"
          secundarios={[
            { label: "eleitorais", valor: data.pesquisas.eleitorais },
            { label: "temáticas", valor: data.pesquisas.tematicas },
          ]}
          rodape="Importação manual via /pesquisas/importar"
          cor="#DB2777"
        />
      </div>

      <button onClick={() => refetch()} className="btn-secondary text-sm">
        <RefreshCw className="h-4 w-4" /> Atualizar
      </button>
    </div>
  );
}

function CardStats({
  icon: Icon,
  titulo,
  principal,
  principal_label,
  secundarios,
  rodape,
  cor,
}: {
  icon: any;
  titulo: string;
  principal: any;
  principal_label: string;
  secundarios: { label: string; valor: any }[];
  rodape: string;
  cor: string;
}) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded flex items-center justify-center" style={{ backgroundColor: `${cor}15`, color: cor }}>
          <Icon className="h-4 w-4" />
        </div>
        <h3 className="font-display font-semibold">{titulo}</h3>
      </div>
      <div className="text-3xl font-bold font-mono mb-0.5" style={{ color: cor }}>{principal}</div>
      <div className="text-xs text-gray-500 mb-2">{principal_label}</div>
      <div className="space-y-0.5 text-xs border-t border-gray-100 pt-2">
        {secundarios.map((s, i) => (
          <div key={i} className="flex justify-between">
            <span className="text-gray-500">{s.label}</span>
            <span className="font-mono">{s.valor}</span>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-gray-400 mt-2 pt-2 border-t border-gray-100 truncate">{rodape}</div>
    </div>
  );
}

// ===== Câmara =====

function CamaraPanel() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async (vars: { com_detalhes: boolean }) => {
      const params = new URLSearchParams();
      params.set("com_detalhes", String(vars.com_detalhes));
      params.set("sincrono", "true");
      return (await api.post(`/admin/ingestao/camara/run?${params}`)).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ingestao-visao"] }),
  });

  return (
    <div className="space-y-4">
      <div className="card">
        <h2 className="font-display font-semibold mb-2">Sincronização da Câmara dos Deputados</h2>
        <p className="text-sm text-gray-600 mb-3">
          Busca lista atual de deputados em exercício, atualiza pessoas/filiações/mandatos no banco. Detecta mudanças de partido e cria eventos automáticos na timeline.
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => mutation.mutate({ com_detalhes: false })}
            disabled={mutation.isPending}
            className="btn-primary"
          >
            <Play className="h-4 w-4" /> Sincronizar (modo rápido — ~5s)
          </button>
          <button
            onClick={() => mutation.mutate({ com_detalhes: true })}
            disabled={mutation.isPending}
            className="btn-secondary"
          >
            <Play className="h-4 w-4" /> Sincronizar com detalhes (~3min)
          </button>
        </div>
        {mutation.isPending && <div className="mt-2 text-sm text-info">Processando…</div>}
        {mutation.data && (
          <div className="mt-3 card !p-3 bg-green-50 border-green-200 text-sm">
            <CheckCircle2 className="inline h-4 w-4 text-sucesso mr-1" />
            <strong>{mutation.data.total_listados}</strong> listados ·{" "}
            {mutation.data.novas} novos · {mutation.data.atualizadas} atualizados ·{" "}
            <strong>{mutation.data.mudancas_partido}</strong> mudanças de partido detectadas em{" "}
            {mutation.data.duracao_segundos}s
            {mutation.data.mudancas_detalhes?.length > 0 && (
              <ul className="mt-2 ml-4 text-xs list-disc">
                {mutation.data.mudancas_detalhes.map((m: any, i: number) => (
                  <li key={i}>
                    <strong>{m.nome}</strong>: {m.de} → {m.para}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ===== Senado =====

function SenadoPanel() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async () =>
      (await api.post("/admin/ingestao/senado/run?sincrono=true")).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ingestao-visao"] }),
  });

  return (
    <div className="card">
      <h2 className="font-display font-semibold mb-2">Sincronização do Senado Federal</h2>
      <p className="text-sm text-gray-600 mb-3">
        Busca os 81 senadores em exercício, marca o ciclo eleitoral (renovação 2026 = 54 vagas eleitas em 2018, ou 2030 = 27 eleitas em 2022).
      </p>
      <button onClick={() => mutation.mutate()} disabled={mutation.isPending} className="btn-primary">
        <Play className="h-4 w-4" /> Sincronizar agora
      </button>
      {mutation.data && (
        <div className="mt-3 card !p-3 bg-green-50 border-green-200 text-sm">
          <CheckCircle2 className="inline h-4 w-4 text-sucesso mr-1" />
          <strong>{mutation.data.total_listados}</strong> senadores · {mutation.data.novas} novos ·{" "}
          {mutation.data.atualizadas} atualizados em {mutation.data.duracao_segundos}s
          <div className="mt-2 text-xs">
            Ciclo 2026 (eleitos 2018 — renovação): <strong>{mutation.data.ciclo_2026}</strong> ·
            Ciclo 2030 (eleitos 2022): <strong>{mutation.data.ciclo_2030}</strong>
          </div>
        </div>
      )}
    </div>
  );
}

// ===== TSE =====

function TSEPanel() {
  const [ano, setAno] = useState(2022);
  const [uf, setUF] = useState("BR");
  const [apenasPrincipais, setApenasPrincipais] = useState(true);

  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams({
        ano: String(ano),
        uf: uf.toUpperCase(),
        apenas_principais: String(apenasPrincipais),
        sincrono: "true",
      });
      return (await api.post(`/admin/ingestao/tse/run?${params}`)).data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["ingestao-visao"] }),
  });

  return (
    <div className="card">
      <h2 className="font-display font-semibold mb-2">Ingestão TSE Dados Abertos</h2>
      <p className="text-sm text-gray-600 mb-3">
        Baixa CSV de candidaturas registradas no TSE para uma eleição específica.
        <br />
        <strong>Atenção:</strong> arquivo zip de ~4MB por eleição (todos UFs). Processamento de uma UF leva 1-5s; "BR" (todas as 27) leva ~1min.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <div>
          <label className="label !text-xs">Ano</label>
          <select className="input" value={ano} onChange={(e) => setAno(parseInt(e.target.value))}>
            <option value={2018}>2018</option>
            <option value={2022}>2022</option>
            <option value={2024}>2024 (municipal)</option>
            <option value={2026}>2026</option>
          </select>
        </div>
        <div>
          <label className="label !text-xs">UF</label>
          <select className="input" value={uf} onChange={(e) => setUF(e.target.value)}>
            <option value="BR">Todos os 27 estados</option>
            {["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"].map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
        </div>
        <div className="md:col-span-2 flex items-end">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={apenasPrincipais}
              onChange={(e) => setApenasPrincipais(e.target.checked)}
            />
            Apenas Pres/Gov/Sen/DepFed (mais rápido)
          </label>
        </div>
      </div>
      <button onClick={() => mutation.mutate()} disabled={mutation.isPending} className="btn-primary">
        <Play className="h-4 w-4" /> Iniciar ingestão
      </button>
      {mutation.isPending && <div className="mt-2 text-sm text-info">Processando (pode demorar)…</div>}
      {mutation.data && (
        <div className="mt-3 card !p-3 bg-green-50 border-green-200 text-sm">
          {mutation.data.todas_ufs ? (
            <>
              <CheckCircle2 className="inline h-4 w-4 text-sucesso mr-1" />
              <strong>{mutation.data.resultados?.length || 0}</strong> UFs processadas
              <ul className="mt-2 max-h-40 overflow-y-auto text-xs">
                {mutation.data.resultados.map((r: any, i: number) => (
                  <li key={i}>
                    <strong>{r.uf}</strong>:{" "}
                    {r.erro ? <span className="text-alerta">ERRO {r.erro}</span> : `${r.candidaturas_criadas || 0} cand, ${r.pessoas_criadas || 0} pessoas`}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <>
              <CheckCircle2 className="inline h-4 w-4 text-sucesso mr-1" />
              <strong>{mutation.data.uf}</strong> {mutation.data.ano}: {mutation.data.candidaturas_criadas} candidaturas,{" "}
              {mutation.data.pessoas_criadas} pessoas em {mutation.data.duracao_segundos}s
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ===== Pesquisas =====

function PesquisasPanel() {
  return (
    <div className="card">
      <h2 className="font-display font-semibold mb-2">Importação de Pesquisas</h2>
      <p className="text-sm text-gray-600 mb-3">
        Pesquisas eleitorais e temáticas são importadas via JSON estruturado (formato Quaest e similares).
        Use a página de importação dedicada com upload de arquivo + análise IA opcional.
      </p>
      <a href="/pesquisas/importar" className="btn-primary inline-flex">
        Ir para importador →
      </a>
    </div>
  );
}

// ===== RSS (versão completa do AdminIngestaoPage anterior) =====

function RSSPanel() {
  const queryClient = useQueryClient();
  const [filtroAbrang, setFiltroAbrang] = useState<string>("");
  const [filtroFalha, setFiltroFalha] = useState(false);

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ["admin", "rss-status"],
    queryFn: async () => (await api.get("/admin/ingestao/rss/status")).data,
    refetchInterval: 10_000,
  });

  const { data: fontes = [] } = useQuery({
    queryKey: ["admin", "fontes-status"],
    queryFn: async () =>
      (await api.get<FonteStatus[]>("/admin/ingestao/rss/fontes?incluir_inativas=true")).data,
  });

  const triggerMutation = useMutation({
    mutationFn: async (vars: { todas?: boolean; fonte_id?: string }) => {
      const params = new URLSearchParams();
      if (vars.todas) params.set("todas", "true");
      if (vars.fonte_id) params.set("fonte_id", vars.fonte_id);
      return (await api.post(`/admin/ingestao/rss/run?${params}`)).data;
    },
    onSuccess: () => {
      const t = setInterval(() => refetchStatus(), 3000);
      setTimeout(() => clearInterval(t), 30_000);
      queryClient.invalidateQueries({ queryKey: ["admin"] });
    },
  });

  const toggleAtivoMutation = useMutation({
    mutationFn: async (vars: { fonte_id: string; ativo: boolean }) =>
      (await api.patch(`/admin/ingestao/rss/fontes/${vars.fonte_id}`, { ativo: vars.ativo })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "fontes-status"] }),
  });

  const fontesFiltradas = fontes.filter((f) => {
    if (filtroAbrang && f.abrangencia !== filtroAbrang) return false;
    if (filtroFalha && !f.esta_em_falha) return false;
    return true;
  });

  return (
    <div className="space-y-3">
      <div className="card !p-3 flex items-center justify-between">
        <div className="text-sm">
          <strong>{status?.fontes_ativas}</strong> fontes ativas · <strong>{status?.total_materias?.toLocaleString("pt-BR")}</strong> matérias capturadas ·{" "}
          {status?.ultimo_polling && (
            <span>último polling: {formatDistanceToNow(new Date(status.ultimo_polling), { locale: ptBR, addSuffix: true })}</span>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => triggerMutation.mutate({})}
            className="btn-secondary text-sm"
          >
            <RefreshCw className="h-4 w-4" /> Polling devidas
          </button>
          <button
            onClick={() => triggerMutation.mutate({ todas: true })}
            className="btn-primary text-sm"
          >
            <Play className="h-4 w-4" /> Polling de todas
          </button>
        </div>
      </div>

      <div className="card !p-0 overflow-hidden">
        <div className="p-2 border-b border-gray-200 flex gap-2 text-xs">
          <select className="input !py-1 !text-xs max-w-[180px]" value={filtroAbrang} onChange={(e) => setFiltroAbrang(e.target.value)}>
            <option value="">Todas abrangências</option>
            <option value="nacional">Nacional</option>
            <option value="estadual">Estadual</option>
          </select>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={filtroFalha} onChange={(e) => setFiltroFalha(e.target.checked)} />
            Só com falha
          </label>
          <span className="ml-auto text-gray-500 self-center">{fontesFiltradas.length} fontes</span>
        </div>
        <table className="w-full text-xs">
          <thead className="bg-gray-50 text-gray-500 uppercase text-[10px]">
            <tr>
              <th className="px-2 py-1.5 text-left">Status</th>
              <th className="px-2 py-1.5 text-left">Fonte</th>
              <th className="px-2 py-1.5 text-right">Capt.</th>
              <th className="px-2 py-1.5 text-right">Aprov.</th>
              <th className="px-2 py-1.5 text-left">Último OK</th>
              <th className="px-2 py-1.5 text-right">Ação</th>
            </tr>
          </thead>
          <tbody>
            {fontesFiltradas.map((f) => (
              <tr key={f.id} className={`border-b border-gray-100 ${!f.ativo ? "opacity-50" : ""}`}>
                <td className="px-2 py-1.5">
                  {f.esta_em_falha ? <AlertTriangle className="h-4 w-4 text-alerta" /> : f.ultimo_sucesso ? <CheckCircle2 className="h-4 w-4 text-sucesso" /> : <span className="inline-block h-2 w-2 rounded-full bg-gray-300" />}
                </td>
                <td className="px-2 py-1.5">
                  <div className="font-medium">{f.nome}</div>
                  <div className="text-gray-400 truncate max-w-xs" title={f.url_feed}>{f.url_feed}</div>
                </td>
                <td className="px-2 py-1.5 text-right font-mono">{f.total_materias_capturadas}</td>
                <td className="px-2 py-1.5 text-right font-mono text-sucesso">{f.total_materias_aproveitadas}</td>
                <td className="px-2 py-1.5 text-gray-500">
                  {f.ultimo_sucesso ? formatDistanceToNow(new Date(f.ultimo_sucesso), { locale: ptBR, addSuffix: true }) : "—"}
                </td>
                <td className="px-2 py-1.5 text-right whitespace-nowrap">
                  <button
                    onClick={() => triggerMutation.mutate({ fonte_id: f.id })}
                    className="text-info hover:underline mr-2"
                  >
                    polling
                  </button>
                  <button
                    onClick={() => toggleAtivoMutation.mutate({ fonte_id: f.id, ativo: !f.ativo })}
                    className="text-gray-500 hover:text-alerta"
                  >
                    {f.ativo ? <X className="inline h-3 w-3" /> : "ativar"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
