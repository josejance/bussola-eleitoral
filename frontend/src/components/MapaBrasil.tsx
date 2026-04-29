import { useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { useUI } from "../store/ui";
import { Estado, StatusEstado, NivelConsolidacao, CenarioGov } from "../lib/types";

// Topojson do Brasil (via CDN público — compatível com IBGE 2020)
const GEO_URL =
  "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/brazil-states.geojson";

// Paleta refinada com gradiente sutil para profundidade visual
const CORES_STATUS: Record<NivelConsolidacao, { fill: string; stroke: string; label: string }> = {
  consolidado: { fill: "#15803D", stroke: "#166534", label: "Consolidado" },
  em_construcao: { fill: "#84CC16", stroke: "#65A30D", label: "Em construção" },
  disputado: { fill: "#EAB308", stroke: "#CA8A04", label: "Disputado" },
  adverso: { fill: "#DC2626", stroke: "#B91C1C", label: "Adverso" },
};

const CORES_GOV: Record<CenarioGov, { fill: string; stroke: string; label: string }> = {
  candidatura_propria: { fill: "#15803D", stroke: "#166534", label: "Candidatura própria" },
  vice_aliado: { fill: "#84CC16", stroke: "#65A30D", label: "Vice / aliado" },
  apoio_sem_cargo: { fill: "#EAB308", stroke: "#CA8A04", label: "Apoio sem cargo" },
  oposicao: { fill: "#DC2626", stroke: "#B91C1C", label: "Oposição" },
  indefinido: { fill: "#9CA3AF", stroke: "#6B7280", label: "Indefinido" },
};

interface Props {
  estados: Estado[];
  status: StatusEstado[];
  onSelectEstado: (sigla: string) => void;
  selectedSigla?: string | null;
}

interface TooltipData {
  estado: Estado;
  status?: StatusEstado;
  x: number;
  y: number;
}

export function MapaBrasil({ estados, status, onSelectEstado, selectedSigla }: Props) {
  const mapLayer = useUI((s) => s.mapLayer);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  const statusByEstadoId = useMemo(
    () => new Map(status.map((s) => [s.estado_id, s])),
    [status]
  );
  const estadoBySigla = useMemo(
    () => new Map(estados.map((e) => [e.sigla, e])),
    [estados]
  );

  function getCor(sigla: string): { fill: string; stroke: string } {
    const estado = estadoBySigla.get(sigla);
    if (!estado) return { fill: "#E5E7EB", stroke: "#D1D5DB" };
    const st = statusByEstadoId.get(estado.id);
    if (!st) return { fill: "#E5E7EB", stroke: "#D1D5DB" };
    if (mapLayer === "status") return CORES_STATUS[st.nivel_consolidacao] ?? { fill: "#E5E7EB", stroke: "#D1D5DB" };
    if (mapLayer === "governador") return CORES_GOV[st.cenario_governador] ?? { fill: "#E5E7EB", stroke: "#D1D5DB" };
    if (mapLayer === "senado") return CORES_GOV[st.cenario_senado] ?? { fill: "#E5E7EB", stroke: "#D1D5DB" };
    return { fill: "#E5E7EB", stroke: "#D1D5DB" };
  }

  return (
    <div className="relative w-full h-full bg-gradient-to-br from-blue-50/30 via-white to-gray-50 rounded-lg border border-gray-200 overflow-hidden shadow-inner">
      {/* SVG defs para sombras e gradientes */}
      <svg width="0" height="0" style={{ position: "absolute" }}>
        <defs>
          <filter id="state-shadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="1" stdDeviation="0.5" floodOpacity="0.15" />
          </filter>
          <filter id="state-shadow-selected" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.35" />
          </filter>
        </defs>
      </svg>

      <ComposableMap
        projection="geoMercator"
        projectionConfig={{ scale: 720, center: [-54, -15] }}
        width={800}
        height={700}
        style={{ width: "100%", height: "100%" }}
      >
        <Geographies geography={GEO_URL}>
          {({ geographies }) =>
            geographies.map((geo: any) => {
              const sigla: string = geo.properties.sigla || geo.properties.SIGLA_UF || geo.id;
              const isSelected = sigla === selectedSigla;
              const isOtherSelected = selectedSigla && !isSelected;
              const cor = getCor(sigla);
              const estado = estadoBySigla.get(sigla);
              const st = estado ? statusByEstadoId.get(estado.id) : undefined;

              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  onClick={() => onSelectEstado(sigla)}
                  onMouseEnter={(e) => {
                    if (estado) {
                      setTooltip({
                        estado,
                        status: st,
                        x: e.clientX,
                        y: e.clientY,
                      });
                    }
                  }}
                  onMouseMove={(e) => {
                    setTooltip((prev) => prev ? { ...prev, x: e.clientX, y: e.clientY } : null);
                  }}
                  onMouseLeave={() => setTooltip(null)}
                  style={{
                    default: {
                      fill: cor.fill,
                      stroke: isSelected ? "#0F172A" : cor.stroke,
                      strokeWidth: isSelected ? 2.5 : 0.6,
                      strokeLinejoin: "round",
                      outline: "none",
                      cursor: "pointer",
                      filter: isSelected ? "url(#state-shadow-selected)" : "url(#state-shadow)",
                      opacity: isOtherSelected ? 0.45 : 1,
                      transition: "all 220ms cubic-bezier(0.4, 0, 0.2, 1)",
                    },
                    hover: {
                      fill: cor.fill,
                      stroke: "#0F172A",
                      strokeWidth: 1.8,
                      outline: "none",
                      filter: "url(#state-shadow-selected) brightness(1.08)",
                      opacity: 1,
                      cursor: "pointer",
                    },
                    pressed: {
                      fill: cor.fill,
                      outline: "none",
                    },
                  }}
                />
              );
            })
          }
        </Geographies>
      </ComposableMap>

      {/* Tooltip flutuante */}
      {tooltip && (
        <MapaTooltip
          estado={tooltip.estado}
          status={tooltip.status}
          x={tooltip.x}
          y={tooltip.y}
          camada={mapLayer}
        />
      )}

      {/* Marca d'água no canto */}
      <div className="absolute bottom-2 right-3 text-[10px] text-gray-400 font-mono pointer-events-none select-none">
        Bússola Eleitoral · {estados.length} UFs
      </div>
    </div>
  );
}

function MapaTooltip({
  estado,
  status,
  x,
  y,
  camada,
}: {
  estado: Estado;
  status?: StatusEstado;
  x: number;
  y: number;
  camada: "status" | "governador" | "senado";
}) {
  // Posiciona próximo ao cursor mas sem cobrir
  const offsetX = 15;
  const offsetY = 15;

  let valorPrincipal = "Sem dados";
  let corValor = "#9CA3AF";
  if (status) {
    if (camada === "status") {
      const c = CORES_STATUS[status.nivel_consolidacao];
      valorPrincipal = c?.label ?? status.nivel_consolidacao;
      corValor = c?.fill ?? "#9CA3AF";
    } else if (camada === "governador") {
      const c = CORES_GOV[status.cenario_governador];
      valorPrincipal = c?.label ?? status.cenario_governador;
      corValor = c?.fill ?? "#9CA3AF";
    } else if (camada === "senado") {
      const c = CORES_GOV[status.cenario_senado];
      valorPrincipal = c?.label ?? status.cenario_senado;
      corValor = c?.fill ?? "#9CA3AF";
    }
  }

  return (
    <div
      className="fixed pointer-events-none z-50 bg-white rounded-lg shadow-xl border border-gray-200 p-3 text-sm min-w-[220px] max-w-[280px]"
      style={{
        left: x + offsetX,
        top: y + offsetY,
        transform: x > window.innerWidth - 300 ? "translateX(-110%)" : undefined,
      }}
    >
      <div className="flex items-baseline gap-2 mb-2">
        <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 font-semibold">
          {estado.sigla}
        </span>
        <span className="font-display font-semibold text-gray-900">{estado.nome}</span>
      </div>

      <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100">
        <span
          className="inline-block w-3 h-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: corValor }}
        />
        <div>
          <div className="text-xs text-gray-500 leading-tight uppercase tracking-wide">
            {camada === "status" ? "Status" : camada === "governador" ? "Governador" : "Senado"}
          </div>
          <div className="font-medium text-gray-900 leading-tight">{valorPrincipal}</div>
        </div>
      </div>

      <div className="space-y-1 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500">Eleitorado</span>
          <span className="font-mono">{(estado.eleitorado_atual ?? 0).toLocaleString("pt-BR")}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Capital</span>
          <span>{estado.capital}</span>
        </div>
        {status?.prioridade_estrategica && (
          <div className="flex justify-between">
            <span className="text-gray-500">Prioridade</span>
            <span className="text-yellow-600">{"★".repeat(status.prioridade_estrategica)}</span>
          </div>
        )}
      </div>

      <div className="mt-2 pt-2 border-t border-gray-100 text-xs text-info text-center">
        Clique para detalhes →
      </div>
    </div>
  );
}

export function LegendaMapa({ tipo }: { tipo: "status" | "governador" | "senado" }) {
  const items =
    tipo === "status"
      ? Object.entries(CORES_STATUS).map(([k, v]) => [v.label, v.fill])
      : Object.entries(CORES_GOV).map(([k, v]) => [v.label, v.fill]);

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-700">
      {items.map(([label, cor]) => (
        <div key={label} className="flex items-center gap-1.5">
          <span
            className="inline-block w-3 h-3 rounded-sm border border-gray-300 shadow-sm"
            style={{ backgroundColor: cor }}
          />
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}
