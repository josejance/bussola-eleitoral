import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { ArrowDown, ArrowUp, FlaskConical, Play, Sparkles } from "lucide-react";

import { api } from "../lib/api";

const GEO_URL =
  "https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/public/data/brazil-states.geojson";

const CENARIO_OPCOES = [
  { key: "candidatura_propria", label: "Candidatura própria" },
  { key: "vice_aliado", label: "Vice / aliado" },
  { key: "apoio_sem_cargo", label: "Apoio sem cargo" },
  { key: "oposicao", label: "Oposição" },
  { key: "indefinido", label: "Indefinido" },
];

interface Projecao {
  estado_sigla: string;
  estado_nome: string;
  cenario_governador: string;
  estimativa_candidato_apoiado_pct: number;
  prob_vitoria_apoiado: number;
  bancada_federal_atual: number;
  bancada_federal_projetada: number;
  fatores: any;
}

interface SimulacaoResult {
  parametros: any;
  agregados: {
    total_estados: number;
    estados_candidatura_propria: number;
    estados_chapa_majoritaria: number;
    bancada_federal_atual: number;
    bancada_federal_projetada: number;
    delta_bancada: number;
    vitorias_provaveis_governador: number;
    media_prob_vitoria: number;
  };
  projecoes_por_estado: Projecao[];
}

interface Preset {
  key: string;
  nome: string;
  descricao: string;
  aprovacao_lula: number;
}

export function SimuladorPage() {
  const [aprovacaoLula, setAprovacaoLula] = useState(40);
  const [bonusGeral, setBonusGeral] = useState(0);
  const [ajustesEstados, setAjustesEstados] = useState<Record<string, { cenario_governador?: string; bonus_coligacao?: number }>>({});
  const [estadoEditando, setEstadoEditando] = useState<string | null>(null);

  const { data: presets = [] } = useQuery({
    queryKey: ["simulador-presets"],
    queryFn: async () => (await api.get<Preset[]>("/simulador/presets")).data,
  });

  const { data: baseAtual } = useQuery({
    queryKey: ["simulador-base"],
    queryFn: async () => (await api.get<SimulacaoResult>("/simulador/presets/atual")).data,
  });

  const simMutation = useMutation({
    mutationFn: async () =>
      (await api.post<SimulacaoResult>("/simulador/simular", {
        aprovacao_lula: aprovacaoLula,
        bonus_coligacao_geral: bonusGeral,
        ajustes_estados: ajustesEstados,
      })).data,
  });

  const presetMutation = useMutation({
    mutationFn: async (key: string) =>
      (await api.get<SimulacaoResult & { preset: Preset }>(`/simulador/presets/${key}`)).data,
    onSuccess: (data) => {
      setAprovacaoLula(data.parametros.aprovacao_lula);
      setBonusGeral(data.parametros.bonus_coligacao_geral || 0);
    },
  });

  const simulado = simMutation.data || presetMutation.data;
  const projecoes = simulado?.projecoes_por_estado || [];
  const projecaoPorSigla = new Map(projecoes.map((p) => [p.estado_sigla, p]));

  // Diferenças vs base
  const diff = useMemo(() => {
    if (!baseAtual || !simulado) return null;
    return {
      bancada: simulado.agregados.bancada_federal_projetada - baseAtual.agregados.bancada_federal_projetada,
      vitorias: simulado.agregados.vitorias_provaveis_governador - baseAtual.agregados.vitorias_provaveis_governador,
      media_prob: (simulado.agregados.media_prob_vitoria - baseAtual.agregados.media_prob_vitoria).toFixed(1),
    };
  }, [baseAtual, simulado]);

  function corPorProb(pct: number): string {
    if (pct >= 60) return "#15803D";
    if (pct >= 40) return "#84CC16";
    if (pct >= 25) return "#EAB308";
    return "#DC2626";
  }

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900 flex items-center gap-2">
          <FlaskConical className="h-6 w-6 text-info" /> Simulador de Cenários
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Manipule variáveis estratégicas e visualize impacto na bancada projetada e mapa nacional.
          Modelo heurístico (não substitui análise política qualitativa).
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* PAINEL ESQUERDO - CONFIGURAÇÃO */}
        <div className="space-y-3">
          {/* Presets */}
          <div className="card !p-3">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
              Cenários pré-configurados
            </h3>
            <div className="space-y-1">
              {presets.map((p) => (
                <button
                  key={p.key}
                  onClick={() => presetMutation.mutate(p.key)}
                  className="w-full text-left text-xs p-2 rounded border border-gray-200 hover:border-info hover:bg-blue-50 transition"
                >
                  <div className="font-medium">{p.nome}</div>
                  <div className="text-gray-500 mt-0.5">{p.descricao}</div>
                  <div className="text-gray-400 mt-0.5">Aprovação Lula: {p.aprovacao_lula}%</div>
                </button>
              ))}
            </div>
          </div>

          {/* Variáveis */}
          <div className="card !p-3">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
              Variáveis nacionais
            </h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <label className="font-medium">Aprovação Lula</label>
                  <span className="font-mono font-bold text-info">{aprovacaoLula}%</span>
                </div>
                <input
                  type="range"
                  min={20}
                  max={70}
                  step={1}
                  value={aprovacaoLula}
                  onChange={(e) => setAprovacaoLula(parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="flex justify-between text-[10px] text-gray-400">
                  <span>20%</span>
                  <span>70%</span>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <label className="font-medium">Bônus coligação geral</label>
                  <span className="font-mono font-bold text-info">{bonusGeral > 0 ? "+" : ""}{bonusGeral}pp</span>
                </div>
                <input
                  type="range"
                  min={-10}
                  max={10}
                  step={1}
                  value={bonusGeral}
                  onChange={(e) => setBonusGeral(parseInt(e.target.value))}
                  className="w-full"
                />
              </div>
            </div>
            <button
              onClick={() => simMutation.mutate()}
              disabled={simMutation.isPending}
              className="btn-primary w-full mt-3"
            >
              <Play className="h-4 w-4" /> {simMutation.isPending ? "Simulando…" : "Simular"}
            </button>
          </div>

          {/* Ajustes específicos */}
          {Object.keys(ajustesEstados).length > 0 && (
            <div className="card !p-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
                Estados ajustados
              </h3>
              <div className="space-y-1">
                {Object.entries(ajustesEstados).map(([sigla, aj]) => (
                  <div key={sigla} className="flex items-center gap-1 text-xs">
                    <span className="font-mono font-bold w-8">{sigla}</span>
                    <span className="text-gray-500 flex-1 truncate">
                      {aj.cenario_governador} {aj.bonus_coligacao ? `· ${aj.bonus_coligacao > 0 ? "+" : ""}${aj.bonus_coligacao}pp` : ""}
                    </span>
                    <button
                      onClick={() => {
                        const novo = { ...ajustesEstados };
                        delete novo[sigla];
                        setAjustesEstados(novo);
                      }}
                      className="text-alerta hover:underline"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setAjustesEstados({})}
                className="text-xs text-info hover:underline mt-2"
              >
                limpar todos
              </button>
            </div>
          )}
        </div>

        {/* PAINEL CENTRAL - MAPA + AGREGADOS */}
        <div className="lg:col-span-2 space-y-3">
          {/* Indicadores agregados */}
          {simulado && (
            <div className="grid grid-cols-2 gap-3">
              <CardAgregado
                label="Bancada Federal projetada"
                valor={simulado.agregados.bancada_federal_projetada}
                comparacao={baseAtual?.agregados.bancada_federal_projetada}
                sub={`atual: ${simulado.agregados.bancada_federal_atual}`}
              />
              <CardAgregado
                label="Vitórias prováveis (governador)"
                valor={simulado.agregados.vitorias_provaveis_governador}
                comparacao={baseAtual?.agregados.vitorias_provaveis_governador}
                sub={`média prob: ${simulado.agregados.media_prob_vitoria}%`}
              />
            </div>
          )}

          {/* Mapa */}
          <div className="card !p-2" style={{ height: 480 }}>
            <ComposableMap
              projection="geoMercator"
              projectionConfig={{ scale: 720, center: [-54, -15] }}
              width={800}
              height={480}
              style={{ width: "100%", height: "100%" }}
            >
              <Geographies geography={GEO_URL}>
                {({ geographies }) =>
                  geographies.map((geo: any) => {
                    const sigla: string = geo.properties.sigla || geo.properties.SIGLA_UF || geo.id;
                    const proj = projecaoPorSigla.get(sigla);
                    const cor = proj ? corPorProb(proj.prob_vitoria_apoiado) : "#E5E7EB";
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        onClick={() => setEstadoEditando(sigla)}
                        style={{
                          default: {
                            fill: cor,
                            stroke: "#FFFFFF",
                            strokeWidth: 0.6,
                            outline: "none",
                            cursor: "pointer",
                          },
                          hover: {
                            fill: cor,
                            stroke: "#0F172A",
                            strokeWidth: 1.5,
                            outline: "none",
                          },
                          pressed: { fill: cor, outline: "none" },
                        }}
                      >
                        <title>{`${sigla}: ${proj?.prob_vitoria_apoiado.toFixed(0) || "—"}%`}</title>
                      </Geography>
                    );
                  })
                }
              </Geographies>
            </ComposableMap>
          </div>

          <div className="text-xs text-gray-500 flex items-center gap-3">
            <span>Cores = probabilidade de vitória do candidato apoiado pelo PT/aliado:</span>
            <div className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: "#15803D" }} />
              ≥60%
            </div>
            <div className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: "#84CC16" }} />
              40-60%
            </div>
            <div className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: "#EAB308" }} />
              25-40%
            </div>
            <div className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded" style={{ backgroundColor: "#DC2626" }} />
              &lt;25%
            </div>
          </div>
        </div>

        {/* PAINEL DIREITO - DETALHE / RANKING */}
        <div className="space-y-3">
          {estadoEditando && (
            <div className="card !p-3">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold">Ajustar {estadoEditando}</h3>
                <button onClick={() => setEstadoEditando(null)} className="text-gray-400 hover:text-gray-700">✕</button>
              </div>
              <div className="space-y-2 text-sm">
                <div>
                  <label className="label !text-xs">Cenário governo</label>
                  <select
                    className="input !py-1 !text-sm"
                    value={ajustesEstados[estadoEditando]?.cenario_governador || ""}
                    onChange={(e) => {
                      const novo = { ...ajustesEstados };
                      novo[estadoEditando] = { ...(novo[estadoEditando] || {}), cenario_governador: e.target.value };
                      setAjustesEstados(novo);
                    }}
                  >
                    <option value="">(usar atual)</option>
                    {CENARIO_OPCOES.map((c) => (
                      <option key={c.key} value={c.key}>{c.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <label>Bônus coligação</label>
                    <span className="font-mono">{ajustesEstados[estadoEditando]?.bonus_coligacao ?? 0}pp</span>
                  </div>
                  <input
                    type="range"
                    min={-15}
                    max={15}
                    value={ajustesEstados[estadoEditando]?.bonus_coligacao ?? 0}
                    onChange={(e) => {
                      const novo = { ...ajustesEstados };
                      novo[estadoEditando] = { ...(novo[estadoEditando] || {}), bonus_coligacao: parseInt(e.target.value) };
                      setAjustesEstados(novo);
                    }}
                    className="w-full"
                  />
                </div>
                <button
                  onClick={() => {
                    setEstadoEditando(null);
                    simMutation.mutate();
                  }}
                  className="btn-primary w-full text-sm"
                >
                  Aplicar e simular
                </button>
              </div>
            </div>
          )}

          {/* Ranking */}
          {projecoes.length > 0 && (
            <div className="card !p-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
                Ranking projeção
              </h3>
              <div className="space-y-1 max-h-[400px] overflow-y-auto">
                {projecoes.map((p) => (
                  <button
                    key={p.estado_sigla}
                    onClick={() => setEstadoEditando(p.estado_sigla)}
                    className="w-full flex items-center gap-2 text-xs p-1 hover:bg-gray-50 rounded"
                  >
                    <span className="font-mono font-bold w-8">{p.estado_sigla}</span>
                    <span className="flex-1 truncate text-left">{p.estado_nome}</span>
                    <span
                      className="font-mono font-bold w-12 text-right"
                      style={{ color: corPorProb(p.prob_vitoria_apoiado) }}
                    >
                      {p.prob_vitoria_apoiado.toFixed(0)}%
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 card !p-3 bg-yellow-50 border-yellow-200 text-xs text-yellow-900">
        <strong>⚠ Limitações do modelo:</strong> baseado em pesquisa atual + histórico do PT no estado +
        ajuste por aprovação Lula + cenário/coligação. Não considera escândalos, candidatura surpresa,
        eventos macroeconômicos. Use como exploração estratégica, não como projeção definitiva.
      </div>
    </div>
  );
}

function CardAgregado({
  label,
  valor,
  comparacao,
  sub,
}: {
  label: string;
  valor: number;
  comparacao?: number;
  sub: string;
}) {
  const delta = comparacao !== undefined ? valor - comparacao : null;
  return (
    <div className="card !p-3">
      <div className="text-xs text-gray-500 uppercase">{label}</div>
      <div className="flex items-baseline gap-2 mt-1">
        <span className="text-3xl font-bold font-mono">{valor}</span>
        {delta !== null && delta !== 0 && (
          <span
            className={`text-sm font-bold ${delta > 0 ? "text-sucesso" : "text-alerta"} flex items-center`}
          >
            {delta > 0 ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
            {Math.abs(delta)}
          </span>
        )}
      </div>
      <div className="text-xs text-gray-500 mt-1">{sub}</div>
    </div>
  );
}
