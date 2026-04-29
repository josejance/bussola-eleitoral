import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { ArrowLeft, ExternalLink, FileText, Newspaper, Vote } from "lucide-react";

import { api } from "../lib/api";

interface PessoaDetalhe {
  id: string;
  nome_completo: string;
  nome_urna: string | null;
  nascimento: string | null;
  genero: string | null;
  raca_cor: string | null;
  foto_url: string | null;
  biografia: string | null;
  email_publico: string | null;
  site_pessoal: string | null;
  escolaridade: string | null;
  partido_atual: any;
  filiacoes: any[];
  mandatos: any[];
  candidaturas: any[];
  materias: any[];
  pesquisas: any[];
  notas: any[];
  stats: { [key: string]: number };
}

export function PerfilPessoaPage() {
  const { id } = useParams();

  const { data: p, isLoading } = useQuery({
    queryKey: ["pessoa", id],
    queryFn: async () => (await api.get<PessoaDetalhe>(`/pessoas/${id}`)).data,
    enabled: !!id,
  });

  if (isLoading) return <div className="p-6 text-gray-400">Carregando…</div>;
  if (!p) return <div className="p-6 text-gray-500">Pessoa não encontrada.</div>;

  return (
    <div className="p-6 max-w-6xl">
      <button
        onClick={() => window.history.back()}
        className="text-xs text-gray-500 hover:text-info inline-flex items-center gap-1 mb-2"
      >
        <ArrowLeft className="h-3 w-3" /> Voltar
      </button>

      {/* Header */}
      <div className="card mb-4">
        <div className="flex items-start gap-4">
          <div className="w-24 h-24 rounded-full bg-gray-100 flex-shrink-0 flex items-center justify-center text-3xl font-display font-bold text-gray-400">
            {p.nome_urna?.[0] || p.nome_completo[0]}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-display font-bold text-gray-900">{p.nome_completo}</h1>
            {p.nome_urna && p.nome_urna !== p.nome_completo && (
              <div className="text-sm text-gray-600">Nome de urna: {p.nome_urna}</div>
            )}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              {p.partido_atual && (
                <span
                  className="badge text-xs font-bold"
                  style={{
                    backgroundColor: `${p.partido_atual.partido_cor}15`,
                    color: p.partido_atual.partido_cor,
                  }}
                >
                  {p.partido_atual.partido_sigla}
                </span>
              )}
              {p.genero && <span className="badge bg-gray-100 text-gray-700 capitalize">{p.genero}</span>}
              {p.raca_cor && <span className="badge bg-gray-100 text-gray-700 capitalize">{p.raca_cor}</span>}
              {p.escolaridade && (
                <span className="badge bg-gray-100 text-gray-700">{p.escolaridade}</span>
              )}
              {p.nascimento && (
                <span className="text-xs text-gray-500">
                  Nascido em {format(parseISO(p.nascimento), "dd/MM/yyyy", { locale: ptBR })}
                </span>
              )}
            </div>
            {p.biografia && (
              <p className="text-sm text-gray-700 mt-3 whitespace-pre-line">{p.biografia}</p>
            )}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mb-4">
        {[
          ["Mandatos", p.stats.total_mandatos],
          ["Candidaturas", p.stats.total_candidaturas],
          ["Filiações", p.stats.total_filiacoes],
          ["Pesquisas", p.stats.total_pesquisas],
          ["Matérias", p.stats.total_materias],
          ["Notas", p.stats.total_notas],
        ].map(([label, val]) => (
          <div key={label as string} className="card !p-3 text-center">
            <div className="text-xs text-gray-500">{label}</div>
            <div className="text-2xl font-bold font-mono text-info">{val}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Trajetória política */}
        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
            Trajetória política
          </h2>
          {p.filiacoes.length === 0 && p.mandatos.length === 0 ? (
            <p className="text-sm text-gray-400">Sem trajetória registrada.</p>
          ) : (
            <div className="space-y-3">
              {p.filiacoes.length > 0 && (
                <div>
                  <h3 className="text-xs uppercase text-gray-500 mb-1">Filiações partidárias</h3>
                  {p.filiacoes.map((f) => (
                    <div key={f.id} className="flex items-center gap-2 py-1 text-sm">
                      <span
                        className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: f.partido_cor }}
                      />
                      <span className="font-mono font-bold">{f.partido_sigla}</span>
                      <span className="text-gray-500 text-xs">{f.partido_nome}</span>
                      <span className="text-xs text-gray-400 ml-auto">
                        {f.inicio && format(parseISO(f.inicio), "yyyy")}
                        {f.fim ? ` - ${format(parseISO(f.fim), "yyyy")}` : f.inicio ? " - atual" : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {p.mandatos.length > 0 && (
                <div>
                  <h3 className="text-xs uppercase text-gray-500 mb-1">Mandatos</h3>
                  {p.mandatos.map((m) => (
                    <div key={m.id} className="flex items-center gap-2 py-1 text-sm">
                      <span className="text-gray-400">→</span>
                      <span className="capitalize font-medium">{m.cargo.replace(/_/g, " ")}</span>
                      {m.estado_sigla && (
                        <span className="font-mono text-xs">/{m.estado_sigla}</span>
                      )}
                      <span className="text-xs text-gray-400 ml-auto">
                        {m.inicio && format(parseISO(m.inicio), "yyyy")}
                        {m.fim ? ` - ${format(parseISO(m.fim), "yyyy")}` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Candidaturas */}
        <div className="card">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3 flex items-center gap-1">
            <Vote className="h-4 w-4" /> Candidaturas
          </h2>
          {p.candidaturas.length === 0 ? (
            <p className="text-sm text-gray-400">Nenhuma candidatura registrada.</p>
          ) : (
            <div className="space-y-2">
              {p.candidaturas.map((c) => (
                <div key={c.id} className="text-sm border-b border-gray-100 pb-2 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-gray-500">{c.eleicao_ano}</span>
                    <span className="font-medium capitalize">{c.cargo.replace(/_/g, " ")}</span>
                    {c.estado_sigla && (
                      <span className="badge bg-blue-50 text-info text-xs">{c.estado_sigla}</span>
                    )}
                    {c.partido_sigla && (
                      <span
                        className="badge text-xs"
                        style={{
                          backgroundColor: `${c.partido_cor || "#6B7280"}15`,
                          color: c.partido_cor || "#6B7280",
                        }}
                      >
                        {c.partido_sigla}
                      </span>
                    )}
                    <span className="badge bg-gray-100 text-gray-700 text-xs ml-auto">
                      {c.status_registro?.replace(/_/g, " ")}
                    </span>
                  </div>
                  {c.observacao && (
                    <div className="text-xs text-gray-600 italic mt-0.5">{c.observacao}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pesquisas */}
        {p.pesquisas.length > 0 && (
          <div className="card">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
              Aparições em pesquisas
            </h2>
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 text-xs uppercase text-gray-500">
                <tr>
                  <th className="text-left py-1">Data</th>
                  <th className="text-left py-1">Escopo</th>
                  <th className="text-right py-1">Posição</th>
                  <th className="text-right py-1">%</th>
                </tr>
              </thead>
              <tbody>
                {p.pesquisas.map((pq, i) => (
                  <tr key={i} className="border-b border-gray-100 last:border-0">
                    <td className="py-1 text-xs">
                      <Link to={`/pesquisas/${pq.pesquisa_id}`} className="text-info hover:underline">
                        {pq.data && format(parseISO(pq.data), "dd/MM/yy", { locale: ptBR })}
                      </Link>
                    </td>
                    <td className="py-1 text-xs capitalize">{pq.abrangencia}</td>
                    <td className="py-1 text-right text-xs">#{pq.posicao || "—"}</td>
                    <td className="py-1 text-right font-mono font-bold">{pq.percentual?.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Matérias */}
        {p.materias.length > 0 && (
          <div className="card">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3 flex items-center gap-1">
              <Newspaper className="h-4 w-4" /> Matérias na mídia
            </h2>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {p.materias.map((m) => (
                <a
                  key={m.id}
                  href={m.url}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-sm border-b border-gray-100 pb-2 last:border-0 hover:bg-gray-50 -mx-2 px-2"
                >
                  <div className="flex items-start gap-1">
                    <span className="flex-1 font-medium text-gray-900">{m.titulo}</span>
                    <ExternalLink className="h-3 w-3 text-gray-400 flex-shrink-0 mt-1" />
                  </div>
                  {m.snippet && (
                    <p className="text-xs text-gray-600 mt-1 line-clamp-2">{m.snippet}</p>
                  )}
                  <div className="text-xs text-gray-400 mt-0.5">
                    {m.data_publicacao && format(parseISO(m.data_publicacao), "dd/MM/yy", { locale: ptBR })}
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Notas */}
        {p.notas.length > 0 && (
          <div className="card">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3 flex items-center gap-1">
              <FileText className="h-4 w-4" /> Notas editoriais
            </h2>
            <div className="space-y-2">
              {p.notas.map((n) => (
                <div key={n.id} className="text-sm border-b border-gray-100 pb-2 last:border-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{n.titulo}</span>
                    <span className="badge bg-gray-100 text-gray-700 text-xs ml-auto">{n.sensibilidade}</span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {n.tema} · {format(parseISO(n.created_at), "dd/MM/yyyy", { locale: ptBR })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
