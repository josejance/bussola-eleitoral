import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Newspaper, RefreshCw } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import { formatLocalDateTime, formatRelativeUtc } from "../lib/datetime";
import { Estado, Materia } from "../lib/types";
import { useAuth } from "../store/auth";

interface FonteRSS {
  id: string;
  nome: string;
  url_site: string | null;
  tipo: string | null;
  espectro_editorial: string | null;
  ativo: boolean;
}

interface IngestaoStatus {
  total_materias: number;
  materias_aproveitadas: number;
  capturadas_ultimas_24h: number;
  ultimo_polling: string | null;
  fontes_ativas: number;
}

const ESPECTRO_CLASS: Record<string, string> = {
  esquerda: "bg-red-100 text-red-700",
  centro_esquerda: "bg-rose-50 text-rose-700",
  centro: "bg-purple-50 text-purple-700",
  centro_direita: "bg-blue-50 text-blue-700",
  direita: "bg-blue-100 text-blue-800",
  tecnico: "bg-gray-100 text-gray-700",
};

export function MidiaPage() {
  const user = useAuth((s) => s.user);
  const podeVerStatus = user && ["admin", "editor_nacional"].includes(user.papel);

  const [estadoFilter, setEstadoFilter] = useState<string>("");
  const [fonteFilter, setFonteFilter] = useState<string>("");

  const { data: materias = [], isFetching, refetch } = useQuery({
    queryKey: ["materias", "feed", estadoFilter, fonteFilter],
    queryFn: async () =>
      (
        await api.get<Materia[]>("/midia/materias", {
          params: {
            limit: 50,
            estado_id: estadoFilter || undefined,
            fonte_id: fonteFilter || undefined,
          },
        })
      ).data,
    refetchInterval: 30_000,
  });

  const { data: fontes = [] } = useQuery({
    queryKey: ["fontes"],
    queryFn: async () => (await api.get<FonteRSS[]>("/midia/fontes")).data,
  });

  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });

  const { data: status } = useQuery({
    queryKey: ["admin", "ingestao-status-mini"],
    queryFn: async () => (await api.get<IngestaoStatus>("/admin/ingestao/rss/status")).data,
    enabled: !!podeVerStatus,
  });

  const fontesMap = new Map(fontes.map((f) => [f.id, f]));
  const estadosMap = new Map(estados.map((e) => [e.id, e]));

  return (
    <div className="p-6">
      <header className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-display font-semibold text-gray-900">Mídia</h1>
          <p className="text-sm text-gray-500 mt-1">
            {fontes.length} fontes RSS · {materias.length} matérias listadas
            {status && <> · {status.capturadas_ultimas_24h} capturadas nas últimas 24h</>}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => refetch()} className="btn-secondary text-sm" disabled={isFetching}>
            <RefreshCw className={`h-4 w-4 ${isFetching ? "animate-spin" : ""}`} />
            Atualizar
          </button>
          {podeVerStatus && (
            <Link to="/admin/ingestao" className="btn-primary text-sm">
              Gerenciar ingestão →
            </Link>
          )}
        </div>
      </header>

      {status?.ultimo_polling && (
        <div className="text-xs text-gray-500 mb-3">
          Último polling: {formatRelativeUtc(status.ultimo_polling)}
          {" "}· Scheduler: a cada 15 min
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <select
              className="input !py-1 !text-sm max-w-xs"
              value={estadoFilter}
              onChange={(e) => setEstadoFilter(e.target.value)}
            >
              <option value="">Todos os estados</option>
              {estados
                .sort((a, b) => a.nome.localeCompare(b.nome))
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.sigla} - {e.nome}
                  </option>
                ))}
            </select>
            <select
              className="input !py-1 !text-sm max-w-xs"
              value={fonteFilter}
              onChange={(e) => setFonteFilter(e.target.value)}
            >
              <option value="">Todas as fontes</option>
              {fontes
                .sort((a, b) => a.nome.localeCompare(b.nome))
                .map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.nome}
                  </option>
                ))}
            </select>
          </div>

          {materias.length === 0 ? (
            <div className="card text-sm text-gray-500">
              <p>Nenhuma matéria encontrada com os filtros atuais.</p>
              {podeVerStatus && (
                <p className="mt-2">
                  <Link to="/admin/ingestao" className="text-info hover:underline">
                    Disparar polling manual em /admin/ingestao →
                  </Link>
                </p>
              )}
            </div>
          ) : (
            materias.map((m) => {
              const fonte = fontesMap.get(m.fonte_id);
              return (
                <article key={m.id} className="card !p-4">
                  <div className="flex items-center gap-2 mb-1 text-xs text-gray-500">
                    <Newspaper className="h-3 w-3" />
                    <span className="font-medium">{fonte?.nome ?? "Fonte"}</span>
                    {fonte?.espectro_editorial && (
                      <span className={`badge text-xs ${ESPECTRO_CLASS[fonte.espectro_editorial] || "bg-gray-100"}`}>
                        {fonte.espectro_editorial.replace(/_/g, " ")}
                      </span>
                    )}
                    <span>·</span>
                    <span>
                      {formatLocalDateTime(m.data_publicacao, "dd MMM HH:mm")}
                    </span>
                  </div>
                  <a
                    href={m.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-display font-semibold text-gray-900 hover:text-info inline-flex items-start gap-1"
                  >
                    {m.titulo}
                    <ExternalLink className="h-3 w-3 mt-1.5 flex-shrink-0" />
                  </a>
                  {m.snippet && (
                    <p className="text-sm text-gray-600 mt-1 line-clamp-3">{m.snippet}</p>
                  )}
                  {m.imagem_url && (
                    <img
                      src={m.imagem_url}
                      alt=""
                      loading="lazy"
                      className="mt-2 max-h-40 rounded object-cover"
                    />
                  )}
                </article>
              );
            })
          )}
        </div>

        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
            Fontes cadastradas ({fontes.length})
          </h2>
          <div className="card !p-3 space-y-1.5 max-h-[700px] overflow-y-auto">
            {fontes
              .sort((a, b) => a.nome.localeCompare(b.nome))
              .map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFonteFilter(fonteFilter === f.id ? "" : f.id)}
                  className={`w-full text-left flex items-center justify-between py-1 border-b border-gray-100 last:border-0 text-sm hover:bg-gray-50 px-1 rounded ${
                    fonteFilter === f.id ? "bg-blue-50" : ""
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-medium text-gray-900 truncate">{f.nome}</div>
                    <div className="text-xs text-gray-500 truncate">
                      {f.tipo} ·{" "}
                      <span className="capitalize">
                        {f.espectro_editorial?.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>
                  {f.ativo ? (
                    <span className="badge bg-green-50 text-green-700 ml-2 flex-shrink-0">on</span>
                  ) : (
                    <span className="badge bg-gray-100 text-gray-500 ml-2 flex-shrink-0">off</span>
                  )}
                </button>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
