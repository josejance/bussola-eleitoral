import { useQuery } from "@tanstack/react-query";
import { format, formatDistanceToNow, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Activity, Clock, Database, Server, Zap } from "lucide-react";

import { api } from "../lib/api";

export function AdminSaudePage() {
  const { data: visao, isLoading } = useQuery({
    queryKey: ["saude-visao"],
    queryFn: async () => (await api.get("/admin/ingestao/visao-geral")).data,
    refetchInterval: 10_000,
  });

  const { data: rss } = useQuery({
    queryKey: ["saude-rss"],
    queryFn: async () => (await api.get("/admin/ingestao/rss/status")).data,
    refetchInterval: 30_000,
  });

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900 flex items-center gap-2">
          <Activity className="h-6 w-6 text-info" /> Saúde do Sistema
        </h1>
        <p className="text-sm text-gray-500 mt-1">Monitor agregado de todos os subsistemas em tempo real</p>
      </header>

      {/* Cards principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <CardMetrica
          icon={Server}
          titulo="Backend"
          valor="OK"
          sub="API + scheduler ativo"
          cor="text-sucesso"
        />
        <CardMetrica
          icon={Database}
          titulo="Banco de dados"
          valor="SQLite"
          sub={`${visao ? (visao.tse?.candidaturas_total || 0).toLocaleString("pt-BR") : "…"} candidaturas`}
          cor="text-info"
        />
        <CardMetrica
          icon={Zap}
          titulo="Schedulers"
          valor="4 ativos"
          sub="RSS 15min · Câmara/Senado 24h · Alertas 5min"
          cor="text-info"
        />
        <CardMetrica
          icon={Clock}
          titulo="Última atividade"
          valor={visao?.rss?.ultimo_polling ? formatDistanceToNow(new Date(visao.rss.ultimo_polling), { locale: ptBR, addSuffix: true }) : "—"}
          sub="último polling RSS"
          cor="text-info"
        />
      </div>

      {/* Tabela detalhada */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
            Volume por subsistema
          </h2>
          <div className="space-y-2 text-sm">
            {visao && (
              <>
                <LinhaMetrica label="Fontes RSS ativas" valor={visao.rss?.fontes_ativas} max={100} />
                <LinhaMetrica label="Matérias capturadas" valor={visao.rss?.materias_total?.toLocaleString("pt-BR")} sub="cumulativo" />
                <LinhaMetrica label="Aproveitadas pelo filtro" valor={visao.rss?.materias_aproveitadas?.toLocaleString("pt-BR")} sub={`${Math.round((visao.rss?.materias_aproveitadas / Math.max(visao.rss?.materias_total, 1)) * 100)}%`} />
                <LinhaMetrica label="Deputados (Câmara)" valor={`${visao.camara?.deputados_ativos}/513`} max={513} />
                <LinhaMetrica label="Senadores" valor={`${visao.senado?.senadores_ativos}/81`} max={81} />
                <LinhaMetrica label="Candidaturas TSE" valor={visao.tse?.candidaturas_total?.toLocaleString("pt-BR")} />
                <LinhaMetrica label="Pessoas únicas" valor={visao.tse?.pessoas_total?.toLocaleString("pt-BR")} />
                <LinhaMetrica label="Pesquisas eleitorais" valor={visao.pesquisas?.eleitorais} />
                <LinhaMetrica label="Pesquisas temáticas" valor={visao.pesquisas?.tematicas} />
              </>
            )}
          </div>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
            Custos estimados (mês)
          </h2>
          <div className="space-y-2 text-sm">
            <LinhaMetrica label="Anthropic Claude" valor="R$ ~5–20" sub="depende de pesquisas + matérias analisadas" />
            <LinhaMetrica label="Hospedagem (local)" valor="R$ 0" sub="rodando localhost" />
            <LinhaMetrica label="Banco SQLite" valor="0 MB" sub="armazenamento local" />
          </div>
          <div className="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500">
            <p>Em produção (Supabase Pro + Render + Anthropic moderado): ~R$ 300/mês fora de pico.</p>
          </div>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
            Status dos schedulers automáticos
          </h2>
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 text-xs uppercase text-gray-500">
              <tr>
                <th className="text-left py-2">Job</th>
                <th className="text-right py-2">Frequência</th>
                <th className="text-left py-2 pl-3">Última execução</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="py-2 font-medium">RSS poller</td>
                <td className="py-2 text-right font-mono text-xs">15 min</td>
                <td className="py-2 pl-3 text-xs text-gray-500">
                  {visao?.rss?.ultimo_polling || "—"}
                </td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 font-medium">Câmara sync</td>
                <td className="py-2 text-right font-mono text-xs">24 h</td>
                <td className="py-2 pl-3 text-xs text-gray-500">—</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 font-medium">Senado sync</td>
                <td className="py-2 text-right font-mono text-xs">24 h</td>
                <td className="py-2 pl-3 text-xs text-gray-500">—</td>
              </tr>
              <tr>
                <td className="py-2 font-medium">Alertas engine</td>
                <td className="py-2 text-right font-mono text-xs">5 min</td>
                <td className="py-2 pl-3 text-xs text-gray-500">a cada execução</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
            Configuração e ambiente
          </h2>
          <div className="space-y-1 text-xs font-mono">
            <div>Backend: <strong>FastAPI 0.115 + SQLAlchemy 2.0</strong></div>
            <div>Frontend: <strong>React 18 + Vite 5 + Tailwind 3</strong></div>
            <div>IA: <strong>Anthropic Claude Haiku 4.5</strong> (configurada)</div>
            <div>Scheduler: <strong>APScheduler</strong></div>
            <div>Auth: <strong>JWT local (HS256, 8h sessão)</strong></div>
            <div>Storage: filesystem local (data/)</div>
          </div>
          <div className="mt-3 pt-3 border-t border-gray-200">
            <a
              href={`${import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"}/docs`}
              target="_blank"
              rel="noreferrer"
              className="text-info hover:underline text-sm"
            >
              📋 Documentação OpenAPI / Swagger →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

function CardMetrica({ icon: Icon, titulo, valor, sub, cor }: { icon: any; titulo: string; valor: any; sub: string; cor: string }) {
  return (
    <div className="card !p-3">
      <div className="flex items-start gap-2">
        <Icon className={`h-5 w-5 ${cor}`} />
        <div className="flex-1 min-w-0">
          <div className="text-xs text-gray-500 uppercase">{titulo}</div>
          <div className={`text-2xl font-bold font-mono ${cor} truncate`}>{valor}</div>
          <div className="text-xs text-gray-500 truncate" title={sub}>{sub}</div>
        </div>
      </div>
    </div>
  );
}

function LinhaMetrica({ label, valor, sub, max }: { label: string; valor: any; sub?: string; max?: number }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-gray-700">{label}</span>
      <div className="text-right">
        <span className="font-mono font-bold">{valor}</span>
        {sub && <span className="text-xs text-gray-500 ml-2">{sub}</span>}
      </div>
    </div>
  );
}
