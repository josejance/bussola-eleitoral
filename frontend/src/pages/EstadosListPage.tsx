import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import { Estado, StatusEstado } from "../lib/types";

const NIVEL_CLASS: Record<string, string> = {
  consolidado: "bg-green-100 text-green-800",
  em_construcao: "bg-lime-100 text-lime-800",
  disputado: "bg-yellow-100 text-yellow-800",
  adverso: "bg-red-100 text-red-800",
};

const NIVEL_LABEL: Record<string, string> = {
  consolidado: "Consolidado",
  em_construcao: "Em construção",
  disputado: "Disputado",
  adverso: "Adverso",
};

export function EstadosListPage() {
  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });
  const { data: status = [] } = useQuery({
    queryKey: ["status_estados"],
    queryFn: async () => (await api.get<StatusEstado[]>("/estados/status/all")).data,
  });
  const statusByEstadoId = new Map(status.map((s) => [s.estado_id, s]));

  const grouped = estados.reduce<Record<string, Estado[]>>((acc, e) => {
    (acc[e.regiao] ??= []).push(e);
    return acc;
  }, {});

  const REGIOES_ORDEM = ["norte", "nordeste", "centro_oeste", "sudeste", "sul"];

  return (
    <div className="p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-gray-900">Estados</h1>
        <p className="text-sm text-gray-500 mt-1">
          Cenário do PT em cada uma das 27 unidades da federação
        </p>
      </header>

      {REGIOES_ORDEM.map((regiao) => {
        const lista = grouped[regiao];
        if (!lista) return null;
        return (
          <section key={regiao} className="mb-8">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3 capitalize">
              {regiao.replace("_", " ")} ({lista.length})
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
              {lista
                .sort((a, b) => a.nome.localeCompare(b.nome))
                .map((e) => {
                  const st = statusByEstadoId.get(e.id);
                  return (
                    <Link
                      key={e.id}
                      to={`/estados/${e.sigla}`}
                      className="card hover:shadow-md hover:border-info transition !p-3"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-lg font-bold text-gray-900">
                          {e.sigla}
                        </span>
                        {st && (
                          <span
                            className={`badge ${NIVEL_CLASS[st.nivel_consolidacao] || "bg-gray-100 text-gray-700"}`}
                          >
                            {NIVEL_LABEL[st.nivel_consolidacao]}
                          </span>
                        )}
                      </div>
                      <div className="text-sm font-medium text-gray-900 leading-tight">
                        {e.nome}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {(e.eleitorado_atual ?? 0).toLocaleString("pt-BR")} eleitores
                      </div>
                      {st && (
                        <div className="text-xs text-gray-500 mt-1">
                          Prioridade {"★".repeat(st.prioridade_estrategica)}
                        </div>
                      )}
                    </Link>
                  );
                })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
