import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, ExternalLink, Info, X } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

import { api } from "../lib/api";
import { Estado, Evento, Materia, Pesquisa, StatusEstado } from "../lib/types";

interface Candidatura {
  id: string;
  cargo: string;
  eh_titular: boolean;
  observacao: string | null;
  pessoa: { nome_urna: string; nome_completo: string } | null;
  partido: { sigla: string; cor_hex: string | null } | null;
}

interface Props {
  estado: Estado;
  status?: StatusEstado;
  onClose: () => void;
}

const NIVEL_LABEL: Record<string, string> = {
  consolidado: "Consolidado",
  em_construcao: "Em construção",
  disputado: "Disputado",
  adverso: "Adverso",
};

const CENARIO_LABEL: Record<string, string> = {
  candidatura_propria: "Candidatura própria",
  vice_aliado: "Vice / aliado",
  apoio_sem_cargo: "Apoio sem cargo",
  oposicao: "Oposição",
  indefinido: "Indefinido",
};

export function DrawerEstado({ estado, status, onClose }: Props) {
  const { data: pesquisas = [] } = useQuery({
    queryKey: ["pesquisas", estado.id],
    queryFn: async () => {
      const r = await api.get<Pesquisa[]>("/pesquisas", { params: { estado_id: estado.id, limit: 5 } });
      return r.data;
    },
  });

  const { data: eventos = [] } = useQuery({
    queryKey: ["eventos", estado.id],
    queryFn: async () => {
      const r = await api.get<Evento[]>("/eventos", { params: { estado_id: estado.id, limit: 10 } });
      return r.data;
    },
  });

  const { data: materias = [] } = useQuery({
    queryKey: ["materias", estado.id],
    queryFn: async () => {
      const r = await api.get<Materia[]>("/midia/materias", { params: { estado_id: estado.id, limit: 8 } });
      return r.data;
    },
  });

  const { data: candidaturas = [] } = useQuery({
    queryKey: ["candidaturas", estado.id],
    queryFn: async () => {
      const r = await api.get<Candidatura[]>("/candidaturas", { params: { estado_id: estado.id } });
      return r.data;
    },
  });

  const ultimaPesquisa = pesquisas[0];

  return (
    <aside className="w-full lg:w-[480px] bg-white border-l border-gray-200 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-200 flex items-start justify-between flex-shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-700">
              {estado.sigla}
            </span>
            <span className="text-xs text-gray-500 capitalize">{estado.regiao}</span>
          </div>
          <h2 className="text-xl font-display font-semibold text-gray-900">
            {estado.nome}
          </h2>
          <div className="text-xs text-gray-500 mt-1">
            {estado.eleitorado_atual?.toLocaleString("pt-BR")} eleitores · capital {estado.capital}
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-gray-100 rounded text-gray-500"
          title="Fechar (Esc)"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Conteúdo */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
        {/* Resumo estratégico */}
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-2 uppercase tracking-wide">
            Resumo estratégico
          </h3>
          <div className="space-y-2 text-sm">
            <Linha label="Status">
              {status ? (
                <span className={statusClass(status.nivel_consolidacao)}>
                  {NIVEL_LABEL[status.nivel_consolidacao]}
                </span>
              ) : (
                <span className="text-gray-400">—</span>
              )}
            </Linha>
            <Linha label="Governador">
              {status ? CENARIO_LABEL[status.cenario_governador] : "—"}
            </Linha>
            <Linha label="Senado">
              {status ? CENARIO_LABEL[status.cenario_senado] : "—"}
            </Linha>
            <Linha label="Prioridade">
              {status ? "★".repeat(status.prioridade_estrategica) : "—"}
            </Linha>
          </div>
        </section>

        {/* Pré-candidatos */}
        {candidaturas.length > 0 && (
          <section>
            <h3 className="text-sm font-semibold text-gray-900 mb-2 uppercase tracking-wide">
              Pré-candidatos 2026
            </h3>
            {(() => {
              const gov = candidaturas.filter((c) => c.cargo === "governador");
              const sen = candidaturas.filter((c) => c.cargo === "senador");
              const vice = candidaturas.filter((c) => c.cargo === "vice_governador");
              return (
                <div className="space-y-3 text-sm">
                  {gov.length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 uppercase mb-1">
                        Governador ({gov.length})
                      </div>
                      <div className="space-y-1">
                        {gov.map((c) => (
                          <div key={c.id} className="flex items-center gap-2">
                            <span
                              className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                              style={{ backgroundColor: c.partido?.cor_hex || "#9CA3AF" }}
                            />
                            <span className="font-medium">{c.pessoa?.nome_urna}</span>
                            <span className="text-gray-500 text-xs font-mono">
                              ({c.partido?.sigla})
                            </span>
                          </div>
                        ))}
                      </div>
                      {vice.length > 0 && (
                        <div className="mt-1 text-xs text-gray-500">
                          Vice: {vice.map((v) => `${v.pessoa?.nome_urna} (${v.partido?.sigla})`).join(", ")}
                        </div>
                      )}
                    </div>
                  )}
                  {sen.length > 0 && (
                    <div>
                      <div className="text-xs text-gray-500 uppercase mb-1">
                        Senado ({sen.length})
                      </div>
                      <div className="space-y-1">
                        {sen.map((c) => (
                          <div key={c.id} className="flex items-center gap-2">
                            <span
                              className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                              style={{ backgroundColor: c.partido?.cor_hex || "#9CA3AF" }}
                            />
                            <span className="font-medium">{c.pessoa?.nome_urna}</span>
                            <span className="text-gray-500 text-xs font-mono">
                              ({c.partido?.sigla})
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </section>
        )}

        {/* Última pesquisa */}
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-2 uppercase tracking-wide">
            Última pesquisa
          </h3>
          {ultimaPesquisa ? (
            <div className="card !p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {ultimaPesquisa.contratante || "Sem contratante"}
                </span>
                <span className="text-xs text-gray-500">
                  {ultimaPesquisa.data_fim_campo &&
                    format(new Date(ultimaPesquisa.data_fim_campo), "dd MMM yyyy", { locale: ptBR })}
                </span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Amostra {ultimaPesquisa.amostra} · margem ±{ultimaPesquisa.margem_erro}pp
              </div>
            </div>
          ) : (
            <EmptyHint>Nenhuma pesquisa cadastrada para este estado.</EmptyHint>
          )}
        </section>

        {/* Feed de mídia */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
              Mídia recente
            </h3>
            <span className="text-xs text-gray-400">{materias.length}</span>
          </div>
          {materias.length === 0 ? (
            <EmptyHint>
              Sem matérias capturadas. Configure ingestão RSS em <code>/admin</code> (Fase 4).
            </EmptyHint>
          ) : (
            <div className="space-y-3">
              {materias.map((m) => (
                <article key={m.id} className="border-l-2 border-info pl-3 text-sm">
                  <a
                    href={m.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-gray-900 hover:text-info inline-flex items-start gap-1"
                  >
                    {m.titulo}
                    <ExternalLink className="h-3 w-3 mt-1 flex-shrink-0" />
                  </a>
                  {m.snippet && (
                    <p className="text-xs text-gray-600 mt-0.5 line-clamp-2">{m.snippet}</p>
                  )}
                  <div className="text-xs text-gray-400 mt-1">
                    {format(new Date(m.data_publicacao), "dd MMM, HH:mm", { locale: ptBR })}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {/* Timeline */}
        <section>
          <h3 className="text-sm font-semibold text-gray-900 mb-2 uppercase tracking-wide">
            Timeline ({eventos.length})
          </h3>
          {eventos.length === 0 ? (
            <EmptyHint>Nenhum evento registrado para este estado.</EmptyHint>
          ) : (
            <ul className="space-y-2">
              {eventos.map((e) => (
                <li key={e.id} className="text-sm">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-gray-400 font-mono">
                      {format(new Date(e.data_evento), "dd/MM", { locale: ptBR })}
                    </span>
                    <span className="font-medium text-gray-900">{e.titulo}</span>
                  </div>
                  {e.descricao && (
                    <p className="text-xs text-gray-600 ml-10 line-clamp-2">{e.descricao}</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-200 bg-gray-50 flex items-center gap-2 flex-shrink-0">
        <Link
          to={`/estados/${estado.sigla}`}
          className="btn-primary flex-1 text-center text-sm"
        >
          Ver ficha completa <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </aside>
  );
}

function Linha({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-sm text-gray-900 font-medium text-right">{children}</span>
    </div>
  );
}

function statusClass(nivel: string): string {
  return (
    "badge " +
    {
      consolidado: "bg-green-100 text-green-800",
      em_construcao: "bg-lime-100 text-lime-800",
      disputado: "bg-yellow-100 text-yellow-800",
      adverso: "bg-red-100 text-red-800",
    }[nivel] || "bg-gray-100 text-gray-800"
  );
}

function EmptyHint({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-xs text-gray-500 bg-gray-50 border border-dashed border-gray-300 rounded p-3 flex items-start gap-2">
      <Info className="h-4 w-4 mt-0.5 flex-shrink-0 text-gray-400" />
      <span>{children}</span>
    </div>
  );
}
