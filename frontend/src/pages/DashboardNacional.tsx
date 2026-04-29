import { useMemo, useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import { Estado, StatusEstado } from "../lib/types";
import { LegendaMapa, MapaBrasil } from "../components/MapaBrasil";
import { DrawerEstado } from "../components/DrawerEstado";
import { PainelPresidencial } from "../components/PainelPresidencial";
import { useUI } from "../store/ui";

export function DashboardNacional() {
  const [selectedSigla, setSelectedSigla] = useState<string | null>(null);
  const mapLayer = useUI((s) => s.mapLayer);
  const setMapLayer = useUI((s) => s.setMapLayer);

  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });

  const { data: status = [] } = useQuery({
    queryKey: ["status_estados"],
    queryFn: async () => (await api.get<StatusEstado[]>("/estados/status/all")).data,
  });

  // Indicadores agregados
  const indicadores = useMemo(() => {
    const total = status.length;
    const propria = status.filter((s) => s.cenario_governador === "candidatura_propria").length;
    const chapaMaj = status.filter((s) =>
      ["candidatura_propria", "vice_aliado"].includes(s.cenario_governador)
    ).length;
    const adverso = status.filter((s) => s.nivel_consolidacao === "adverso").length;
    const disputado = status.filter((s) => s.nivel_consolidacao === "disputado").length;
    return { total, propria, chapaMaj, adverso, disputado };
  }, [status]);

  const selectedEstado = useMemo(
    () => estados.find((e) => e.sigla === selectedSigla) ?? null,
    [estados, selectedSigla]
  );
  const selectedStatus = useMemo(
    () => status.find((s) => s.estado_id === selectedEstado?.id),
    [status, selectedEstado]
  );

  // Fechar drawer com ESC
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setSelectedSigla(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="h-full flex">
      <div className="flex-1 p-3 md:p-6 min-w-0">
        <header className="mb-3 md:mb-4">
          <h1 className="text-xl md:text-2xl font-display font-semibold text-gray-900">Visão Nacional</h1>
          <p className="text-xs md:text-sm text-gray-500 mt-1">
            Cenário estratégico do PT em tempo real — toque em um estado para detalhes
          </p>
        </header>

        {/* Cards de indicadores */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2 md:gap-3 mb-3 md:mb-4">
          <CardIndicador
            label="Candidatura própria"
            valor={indicadores.propria}
            sub={`de ${indicadores.total} estados`}
            cor="text-sucesso"
          />
          <CardIndicador
            label="PT em chapa majoritária"
            valor={indicadores.chapaMaj}
            sub="governador ou vice"
            cor="text-info"
          />
          <CardIndicador
            label="Disputados"
            valor={indicadores.disputado}
            sub="cenário em aberto"
            cor="text-atencao"
          />
          <CardIndicador
            label="Adversos"
            valor={indicadores.adverso}
            sub="oposição consolidada"
            cor="text-alerta"
          />
        </div>

        {/* Controles do mapa */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-3">
          <div className="inline-flex rounded-md shadow-sm overflow-x-auto" role="group">
            {(["status", "governador", "senado"] as const).map((layer) => (
              <button
                key={layer}
                onClick={() => setMapLayer(layer)}
                className={`px-2 md:px-3 py-1.5 text-xs md:text-sm font-medium border whitespace-nowrap ${
                  mapLayer === layer
                    ? "bg-info text-white border-info"
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
                } first:rounded-l-md last:rounded-r-md -ml-px first:ml-0`}
              >
                <span className="md:hidden">{layer === "status" ? "Status" : layer === "governador" ? "Governo" : "Senado"}</span>
                <span className="hidden md:inline">{layer === "status" ? "Status estratégico" : layer === "governador" ? "Cenário governo" : "Cenário senado"}</span>
              </button>
            ))}
          </div>
          <LegendaMapa tipo={mapLayer} />
        </div>

        {/* Mapa: altura responsiva */}
        <div
          className="card !p-2 h-[60vh] md:h-[calc(100vh-320px)]"
          style={{ minHeight: 320 }}
        >
          <MapaBrasil
            estados={estados}
            status={status}
            onSelectEstado={(s) => setSelectedSigla(s)}
            selectedSigla={selectedSigla}
          />
        </div>

        {/* Painel presidencial — avaliação do governo federal Lula */}
        <div className="mt-4">
          <PainelPresidencial />
        </div>
      </div>

      {/* Drawer */}
      {selectedEstado && (
        <DrawerEstado
          estado={selectedEstado}
          status={selectedStatus}
          onClose={() => setSelectedSigla(null)}
        />
      )}
    </div>
  );
}

function CardIndicador({
  label,
  valor,
  sub,
  cor,
}: {
  label: string;
  valor: number;
  sub: string;
  cor: string;
}) {
  return (
    <div className="card !p-2 md:!p-3">
      <div className="text-[10px] md:text-xs text-gray-500 uppercase tracking-wide leading-tight">{label}</div>
      <div className={`text-2xl md:text-3xl font-display font-bold ${cor} my-1 font-mono`}>{valor}</div>
      <div className="text-[10px] md:text-xs text-gray-500 leading-tight">{sub}</div>
    </div>
  );
}
