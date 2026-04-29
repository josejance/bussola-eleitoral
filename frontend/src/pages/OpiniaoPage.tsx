import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { ArrowRight, BarChart3, Globe, MessageSquare, Sparkles, Trophy, Users, Vote } from "lucide-react";

import { api } from "../lib/api";

const ICONES: Record<string, any> = {
  trophy: Trophy,
  globe: Globe,
  vote: Vote,
  users: Users,
  scale: BarChart3,
  "file-text": MessageSquare,
  flag: Globe,
  "help-circle": MessageSquare,
};

interface TemaMeta {
  tema: string;
  total: number;
  label: string;
  icone: string;
  cor: string;
}

interface PesquisaTematica {
  id: string;
  titulo: string;
  subtitulo: string | null;
  tema: string;
  abrangencia: string;
  estado_sigla: string | null;
  data_inicio_campo: string | null;
  data_fim_campo: string | null;
  amostra: number | null;
  margem_erro: number | null;
  metodologia: string | null;
  contratante: string | null;
  instituto_nome: string;
  instituto_sigla: string | null;
  registro_eleitoral: string | null;
  publico_alvo: string | null;
  n_questoes: number;
}

export function OpiniaoPage() {
  const [temaFilter, setTemaFilter] = useState<string>("");

  const { data: temas = [] } = useQuery({
    queryKey: ["opiniao-temas-meta"],
    queryFn: async () => (await api.get<TemaMeta[]>("/opiniao/temas/metadata")).data,
  });

  const { data: pesquisas = [] } = useQuery({
    queryKey: ["opiniao-pesquisas", temaFilter],
    queryFn: async () =>
      (
        await api.get<PesquisaTematica[]>("/opiniao/pesquisas", {
          params: { tema: temaFilter || undefined, limit: 100 },
        })
      ).data,
  });

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900">
          Opinião Pública sobre Temas
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Pesquisas de opinião não-eleitorais — apostas esportivas, Copa do Mundo, STF, IR, Venezuela, etc.
        </p>
      </header>

      {/* Cards de temas */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        <button
          onClick={() => setTemaFilter("")}
          className={`card hover:shadow-md transition !p-3 text-left ${
            temaFilter === "" ? "ring-2 ring-info" : ""
          }`}
        >
          <div className="text-xs text-gray-500 uppercase tracking-wide">Todos</div>
          <div className="text-2xl font-bold font-mono text-info">
            {temas.reduce((s, t) => s + t.total, 0)}
          </div>
          <div className="text-xs text-gray-500">pesquisas</div>
        </button>
        {temas.map((t) => {
          const Icon = ICONES[t.icone] || MessageSquare;
          return (
            <button
              key={t.tema}
              onClick={() => setTemaFilter(t.tema === temaFilter ? "" : t.tema)}
              className={`card hover:shadow-md transition !p-3 text-left ${
                t.tema === temaFilter ? "ring-2 ring-info" : ""
              }`}
            >
              <div className="flex items-start justify-between">
                <Icon className="h-5 w-5" style={{ color: t.cor }} />
                <span className="text-2xl font-bold font-mono" style={{ color: t.cor }}>
                  {t.total}
                </span>
              </div>
              <div className="text-sm font-medium text-gray-900 mt-1">{t.label}</div>
            </button>
          );
        })}
      </div>

      {/* Lista de pesquisas */}
      <div className="space-y-3">
        {pesquisas.length === 0 ? (
          <div className="card text-sm text-gray-500 text-center py-8">
            Nenhuma pesquisa temática encontrada com o filtro atual.
          </div>
        ) : (
          pesquisas.map((p) => <CardPesquisaTematica key={p.id} p={p} temas={temas} />)
        )}
      </div>

      <div className="mt-6 text-center">
        <Link to="/pesquisas/importar" className="btn-secondary text-sm">
          <Sparkles className="h-4 w-4" /> Importar mais JSONs
        </Link>
      </div>
    </div>
  );
}

function CardPesquisaTematica({ p, temas }: { p: PesquisaTematica; temas: TemaMeta[] }) {
  const meta = temas.find((t) => t.tema === p.tema);
  const Icon = meta ? ICONES[meta.icone] || MessageSquare : MessageSquare;
  const cor = meta?.cor || "#6B7280";

  return (
    <Link
      to={`/opiniao/${p.id}`}
      className="card hover:shadow-md hover:border-info transition block"
    >
      <div className="flex items-start gap-3">
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ backgroundColor: `${cor}15`, color: cor }}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="badge text-xs font-medium"
              style={{ backgroundColor: `${cor}15`, color: cor }}
            >
              {meta?.label || p.tema}
            </span>
            <span className="badge bg-gray-100 text-gray-600 text-xs">
              {p.instituto_nome}
            </span>
            {p.estado_sigla && (
              <span className="badge bg-blue-50 text-info text-xs font-mono">
                {p.estado_sigla}
              </span>
            )}
            <span className="text-xs text-gray-400 ml-auto">
              {p.data_fim_campo && format(parseISO(p.data_fim_campo), "dd MMM yyyy", { locale: ptBR })}
            </span>
          </div>
          <h3 className="font-display font-semibold text-gray-900 leading-tight">{p.titulo}</h3>
          {p.subtitulo && <p className="text-xs text-gray-600 mt-0.5">{p.subtitulo}</p>}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 mt-2">
            <span className="font-mono">{p.n_questoes} questões</span>
            {p.amostra && <span>amostra {p.amostra.toLocaleString("pt-BR")}</span>}
            {p.margem_erro && <span>±{p.margem_erro}pp</span>}
            {p.metodologia && <span className="capitalize">{p.metodologia}</span>}
            {p.registro_eleitoral && (
              <span className="font-mono text-info">{p.registro_eleitoral}</span>
            )}
          </div>
        </div>
        <ArrowRight className="h-4 w-4 text-gray-400 flex-shrink-0 mt-3" />
      </div>
    </Link>
  );
}
