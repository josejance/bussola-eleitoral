import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";

import { formatRelativeUtc } from "../lib/datetime";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  Bell,
  Maximize2,
  Newspaper,
  Pause,
  Play,
  Radar,
  RefreshCw,
  TrendingUp,
  Users2,
  Vote,
} from "lucide-react";

import { api } from "../lib/api";

export function WarRoomPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [agora, setAgora] = useState(new Date());

  // Atualiza relógio a cada segundo
  useEffect(() => {
    const t = setInterval(() => setAgora(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-white p-4">
      <header className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <Link to="/nacional" className="text-slate-400 hover:text-white inline-flex items-center gap-1 text-sm">
            <ArrowLeft className="h-4 w-4" /> Sair
          </Link>
          <h1 className="text-xl font-display font-bold flex items-center gap-2">
            <Radar className="h-5 w-5 text-red-500 animate-pulse" /> WAR ROOM
          </h1>
          <span className="badge bg-red-900/30 text-red-300 text-xs animate-pulse">AO VIVO</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-2xl font-mono font-bold tabular-nums">
            {format(agora, "HH:mm:ss", { locale: ptBR })}
          </div>
          <div className="text-xs text-slate-400">
            {format(agora, "EEE, dd MMM yyyy", { locale: ptBR })}
          </div>
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className="btn-secondary !bg-slate-800 !border-slate-700 !text-white text-xs"
          >
            {autoRefresh ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
            {autoRefresh ? "Pausar" : "Retomar"}
          </button>
        </div>
      </header>

      {/* Grid de widgets 3x4 */}
      <div className="grid grid-cols-12 gap-3 auto-rows-min">
        <div className="col-span-12 lg:col-span-4">
          <WidgetMateriasRecentes autoRefresh={autoRefresh} />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <WidgetVotacoesRecentes autoRefresh={autoRefresh} />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <WidgetEventosTimeline autoRefresh={autoRefresh} />
        </div>

        <div className="col-span-12 lg:col-span-6">
          <WidgetPesquisasUltimas autoRefresh={autoRefresh} />
        </div>
        <div className="col-span-12 lg:col-span-3">
          <WidgetAlertasPrioritarios autoRefresh={autoRefresh} />
        </div>
        <div className="col-span-12 lg:col-span-3">
          <WidgetSaudeIngestao autoRefresh={autoRefresh} />
        </div>

        <div className="col-span-12 lg:col-span-6">
          <WidgetBaseAliada autoRefresh={autoRefresh} />
        </div>
        <div className="col-span-12 lg:col-span-6">
          <WidgetMencoes autoRefresh={autoRefresh} />
        </div>
      </div>
    </div>
  );
}

// ===== Widgets =====

function WidgetCard({ titulo, icon: Icon, children, action }: { titulo: string; icon: any; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 h-full">
      <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-700">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <Icon className="h-4 w-4 text-info" /> {titulo}
        </div>
        {action}
      </div>
      <div className="overflow-y-auto max-h-72">{children}</div>
    </div>
  );
}

function WidgetMateriasRecentes({ autoRefresh }: { autoRefresh: boolean }) {
  const { data = [] } = useQuery({
    queryKey: ["war-materias"],
    queryFn: async () => (await api.get("/midia/materias?limit=15")).data,
    refetchInterval: autoRefresh ? 30_000 : false,
  });

  return (
    <WidgetCard titulo="Mídia em tempo real" icon={Newspaper}>
      {data.length === 0 ? (
        <div className="text-xs text-slate-500 py-4 text-center">Sem matérias recentes</div>
      ) : (
        <div className="space-y-1.5">
          {data.map((m: any) => (
            <a key={m.id} href={m.url} target="_blank" rel="noreferrer" className="block hover:bg-slate-700 -mx-1 px-1 py-0.5 rounded">
              <div className="text-xs font-medium text-slate-100 line-clamp-2">{m.titulo}</div>
              <div className="text-[10px] text-slate-500">
                {m.data_publicacao && formatRelativeUtc(m.data_publicacao)}
              </div>
            </a>
          ))}
        </div>
      )}
    </WidgetCard>
  );
}

function WidgetVotacoesRecentes({ autoRefresh }: { autoRefresh: boolean }) {
  const { data = [] } = useQuery({
    queryKey: ["war-votacoes"],
    queryFn: async () => (await api.get("/governo/votacoes?limit=10")).data,
    refetchInterval: autoRefresh ? 60_000 : false,
  });

  return (
    <WidgetCard titulo="Votações Câmara" icon={Vote}>
      {data.length === 0 ? (
        <div className="text-xs text-slate-500 py-4 text-center">Sem votações recentes</div>
      ) : (
        <div className="space-y-1.5">
          {data.map((v: any) => (
            <div key={v.id} className="text-xs border-l-2 border-slate-600 pl-2">
              <div className="text-slate-300 font-mono">
                {format(parseISO(v.data), "dd/MM", { locale: ptBR })} ·{" "}
                <span
                  className={
                    v.posicionamento_governo === "a_favor"
                      ? "text-green-400"
                      : v.posicionamento_governo === "contra"
                        ? "text-red-400"
                        : "text-slate-500"
                  }
                >
                  {v.posicionamento_governo}
                </span>
              </div>
              <div className="text-slate-200 line-clamp-2">{v.ementa}</div>
              {v.resultado && (
                <div className={`text-[10px] ${v.resultado === "aprovado" ? "text-green-400" : "text-red-400"}`}>
                  {v.resultado}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </WidgetCard>
  );
}

function WidgetEventosTimeline({ autoRefresh }: { autoRefresh: boolean }) {
  const { data = [] } = useQuery({
    queryKey: ["war-eventos"],
    queryFn: async () => (await api.get("/eventos?limit=15")).data,
    refetchInterval: autoRefresh ? 60_000 : false,
  });

  return (
    <WidgetCard titulo="Timeline política" icon={Activity}>
      {data.length === 0 ? (
        <div className="text-xs text-slate-500 py-4 text-center">Sem eventos recentes</div>
      ) : (
        <div className="space-y-1.5">
          {data.map((e: any) => (
            <div key={e.id} className="text-xs">
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className="text-[10px] text-slate-500 font-mono">
                  {format(parseISO(e.data_evento), "dd/MM HH:mm", { locale: ptBR })}
                </span>
                <span className="badge bg-slate-700 text-slate-300 text-[9px]">{e.tipo}</span>
              </div>
              <div className="text-slate-200 line-clamp-2">{e.titulo}</div>
            </div>
          ))}
        </div>
      )}
    </WidgetCard>
  );
}

function WidgetPesquisasUltimas({ autoRefresh }: { autoRefresh: boolean }) {
  const { data: agregado } = useQuery({
    queryKey: ["war-agregado"],
    queryFn: async () => (await api.get("/pesquisas/agregador?cenario=estimulado")).data,
    refetchInterval: autoRefresh ? 5 * 60_000 : false,
  });

  const candidatos = agregado?.candidatos?.slice(0, 6) || [];

  return (
    <WidgetCard
      titulo="Agregado nacional (presidente)"
      icon={TrendingUp}
      action={<span className="text-[10px] text-slate-500">{agregado?.meta?.n_pesquisas || 0} pesquisas</span>}
    >
      {candidatos.length === 0 ? (
        <div className="text-xs text-slate-500 py-4 text-center">Sem pesquisas</div>
      ) : (
        <div className="space-y-2">
          {candidatos.map((c: any) => (
            <div key={c.nome} className="text-xs">
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-slate-200 truncate flex-1">{c.nome}</span>
                <span className="font-mono font-bold text-info">{c.estimativa.toFixed(1)}%</span>
              </div>
              <div className="relative h-2 bg-slate-700 rounded">
                <div
                  className="absolute h-2 bg-info rounded transition-all"
                  style={{ width: `${Math.min(c.estimativa, 100)}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {c.banda_inferior.toFixed(1)}–{c.banda_superior.toFixed(1)}% · {c.n_pesquisas} pesq
              </div>
            </div>
          ))}
        </div>
      )}
    </WidgetCard>
  );
}

function WidgetAlertasPrioritarios({ autoRefresh }: { autoRefresh: boolean }) {
  const { data: contagem } = useQuery({
    queryKey: ["war-notif-contagem"],
    queryFn: async () => (await api.get("/notificacoes/contagem")).data,
    refetchInterval: autoRefresh ? 15_000 : false,
  });
  const { data = [] } = useQuery({
    queryKey: ["war-notifs"],
    queryFn: async () => (await api.get("/notificacoes?limit=8&nao_lidas=true")).data,
    refetchInterval: autoRefresh ? 30_000 : false,
  });

  return (
    <WidgetCard
      titulo="Notificações"
      icon={Bell}
      action={
        contagem?.nao_lidas > 0 ? (
          <span className="badge bg-red-900/50 text-red-300 text-[10px] animate-pulse">{contagem.nao_lidas}</span>
        ) : null
      }
    >
      {data.length === 0 ? (
        <div className="text-xs text-slate-500 py-4 text-center">Sem alertas pendentes</div>
      ) : (
        <div className="space-y-1.5">
          {data.map((n: any) => (
            <div key={n.id} className="text-xs border-l-2 border-red-500 pl-2">
              <div className="text-slate-200 font-medium line-clamp-1">{n.titulo}</div>
              <div className="text-[10px] text-slate-500">
                {formatRelativeUtc(n.created_at)}
              </div>
            </div>
          ))}
        </div>
      )}
    </WidgetCard>
  );
}

function WidgetSaudeIngestao({ autoRefresh }: { autoRefresh: boolean }) {
  const { data } = useQuery({
    queryKey: ["war-saude"],
    queryFn: async () => (await api.get("/admin/ingestao/visao-geral")).data,
    refetchInterval: autoRefresh ? 60_000 : false,
  });

  if (!data) return <WidgetCard titulo="Saúde dos dados" icon={RefreshCw}><div className="text-xs">…</div></WidgetCard>;

  return (
    <WidgetCard titulo="Saúde dos dados" icon={RefreshCw}>
      <div className="space-y-1.5 text-xs">
        <Linha label="Fontes RSS" valor={data.rss?.fontes_ativas} extra={`${data.rss?.materias_total} matérias`} />
        <Linha label="Câmara" valor={data.camara?.deputados_ativos} extra={`/${513}`} />
        <Linha label="Senado" valor={data.senado?.senadores_ativos} extra={`/${81}`} />
        <Linha label="Pesquisas" valor={data.pesquisas?.eleitorais + data.pesquisas?.tematicas} />
      </div>
    </WidgetCard>
  );
}

function Linha({ label, valor, extra }: { label: string; valor: any; extra?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-400">{label}</span>
      <span className="font-mono font-bold text-info">
        {valor} {extra && <span className="text-[10px] text-slate-500 ml-1">{extra}</span>}
      </span>
    </div>
  );
}

function WidgetBaseAliada({ autoRefresh }: { autoRefresh: boolean }) {
  const { data } = useQuery({
    queryKey: ["war-base"],
    queryFn: async () => (await api.get("/governo/base-aliada/sumario?meses=12")).data,
    refetchInterval: autoRefresh ? 5 * 60_000 : false,
  });

  if (!data || data.total_parlamentares_avaliados === 0) {
    return (
      <WidgetCard titulo="Base aliada (Congresso)" icon={Users2}>
        <div className="text-xs text-slate-500 py-4 text-center">
          Aguardando ingestão de votações classificadas
        </div>
      </WidgetCard>
    );
  }

  return (
    <WidgetCard titulo="Base aliada (Congresso)" icon={Users2}>
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center p-2 bg-slate-700 rounded">
          <div className="text-[10px] text-slate-400 uppercase">Fidelidade</div>
          <div className="text-2xl font-bold text-info">{data.fidelidade_media}%</div>
        </div>
        <div className="text-center p-2 bg-slate-700 rounded">
          <div className="text-[10px] text-slate-400 uppercase">Alta (≥70%)</div>
          <div className="text-2xl font-bold text-green-400">{data.alta_fidelidade}</div>
        </div>
        <div className="text-center p-2 bg-slate-700 rounded">
          <div className="text-[10px] text-slate-400 uppercase">Rebeldes</div>
          <div className="text-2xl font-bold text-red-400">{data.rebeldes_da_base}</div>
        </div>
      </div>
      {data.rebeldes_lista?.slice(0, 4).map((r: any, i: number) => (
        <div key={i} className="text-xs flex items-center gap-2 py-0.5">
          <span className="text-red-400">⚠</span>
          <span className="text-slate-200 flex-1 truncate">{r.nome}</span>
          <span className="font-mono text-xs text-slate-400">{r.partido_sigla}</span>
          <span className="font-mono font-bold text-red-400 w-10 text-right">{r.fidelidade.toFixed(0)}%</span>
        </div>
      ))}
    </WidgetCard>
  );
}

function WidgetMencoes({ autoRefresh }: { autoRefresh: boolean }) {
  // Top pessoas mais mencionadas — proxy via API geral
  return (
    <WidgetCard titulo="Sentimento da mídia" icon={AlertTriangle}>
      <div className="text-xs text-slate-300 space-y-2">
        <p>
          <strong>Análise em tempo real</strong> da cobertura midiática nas {" "}
          <span className="text-info">100 fontes RSS</span> ativas.
        </p>
        <p className="text-slate-400">
          Visualização detalhada em <Link to="/midia" className="text-info underline">/midia</Link>.
        </p>
        <p className="text-slate-400 text-[10px]">
          Análise IA Claude está disponível por matéria individual. Detecção de narrativas (clustering
          semântico) requer pipeline batch separado.
        </p>
      </div>
    </WidgetCard>
  );
}
