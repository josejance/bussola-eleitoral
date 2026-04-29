import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, NavLink, useParams } from "react-router-dom";
import { ArrowLeft, ChevronLeft, ChevronRight, Edit3, FileDown, FileText } from "lucide-react";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import clsx from "clsx";

import { api } from "../lib/api";
import { Estado, Evento, Materia, Nota, Pesquisa, StatusEstado } from "../lib/types";
import { useAuth } from "../store/auth";
import { PainelGovernador } from "../components/PainelGovernador";
import { formatLocalDateTime } from "../lib/datetime";

const ABAS = [
  { key: "visao-geral", label: "Visão Geral" },
  { key: "candidaturas", label: "Candidaturas" },
  { key: "pesquisas", label: "Pesquisas" },
  { key: "bancada", label: "Bancada" },
  { key: "midia", label: "Mídia" },
  { key: "timeline", label: "Timeline" },
  { key: "notas", label: "Notas" },
];

export function FichaEstadual() {
  const { uf, aba = "visao-geral" } = useParams();
  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });
  const estado = estados.find((e) => e.sigla === uf?.toUpperCase());
  const { data: status } = useQuery({
    queryKey: ["status", uf],
    queryFn: async () => (await api.get<StatusEstado>(`/estados/${uf}/status`)).data,
    enabled: !!uf,
    retry: false,
  });

  if (!uf) return null;
  if (!estado) {
    return (
      <div className="p-6">
        <Link to="/estados" className="text-info text-sm">
          ← Voltar para estados
        </Link>
        <p className="mt-4 text-gray-500">Estado não encontrado: {uf}</p>
      </div>
    );
  }

  // Navegação prev/next por sigla
  const sortedEstados = useMemo(
    () => [...estados].sort((a, b) => a.sigla.localeCompare(b.sigla)),
    [estados]
  );
  const idx = sortedEstados.findIndex((e) => e.sigla === uf.toUpperCase());
  const prevEstado = idx > 0 ? sortedEstados[idx - 1] : null;
  const nextEstado = idx < sortedEstados.length - 1 ? sortedEstados[idx + 1] : null;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 md:px-6 pt-3 md:pt-4">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="min-w-0 flex-1">
            <Link to="/estados" className="text-xs text-gray-500 hover:text-info inline-flex items-center gap-1">
              <ArrowLeft className="h-3 w-3" /> Estados
            </Link>
            <div className="flex items-baseline gap-2 md:gap-3 mt-1 flex-wrap">
              <h1 className="text-xl md:text-3xl font-display font-bold text-gray-900">{estado.nome}</h1>
              <span className="font-mono text-lg md:text-2xl text-gray-400">{estado.sigla}</span>
            </div>
            <div className="text-xs md:text-sm text-gray-500 mt-1">
              <span className="capitalize">{estado.regiao.replace("_", " ")}</span> ·{" "}
              <span className="hidden sm:inline">
                {estado.eleitorado_atual?.toLocaleString("pt-BR")} eleitores · capital {estado.capital}
              </span>
              <span className="sm:hidden">{estado.capital}</span>
            </div>
          </div>
          <div className="flex items-center gap-1 md:gap-2 flex-shrink-0">
            {prevEstado && (
              <Link
                to={`/estados/${prevEstado.sigla}`}
                className="btn-secondary !p-2"
                title={`Anterior: ${prevEstado.nome}`}
              >
                <ChevronLeft className="h-4 w-4" />
              </Link>
            )}
            {nextEstado && (
              <Link
                to={`/estados/${nextEstado.sigla}`}
                className="btn-secondary !p-2"
                title={`Próximo: ${nextEstado.nome}`}
              >
                <ChevronRight className="h-4 w-4" />
              </Link>
            )}
            <button className="btn-secondary text-sm hidden md:inline-flex">
              <FileDown className="h-4 w-4" /> Exportar PDF
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 -mb-px overflow-x-auto">
          {ABAS.map((tab) => (
            <NavLink
              key={tab.key}
              to={`/estados/${uf}/${tab.key}`}
              className={({ isActive }) =>
                clsx(
                  "px-4 py-2.5 text-sm font-medium border-b-2 transition whitespace-nowrap",
                  isActive
                    ? "border-info text-info"
                    : "border-transparent text-gray-600 hover:text-gray-900"
                )
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </div>
      </div>

      {/* Conteúdo */}
      <div className="flex-1 overflow-y-auto p-3 md:p-6 bg-gray-50">
        {aba === "visao-geral" && <AbaVisaoGeral estado={estado} status={status} />}
        {aba === "candidaturas" && <AbaCandidaturas estado={estado} />}
        {aba === "pesquisas" && <AbaPesquisas estado={estado} />}
        {aba === "bancada" && <AbaBancada estado={estado} />}
        {aba === "midia" && <AbaMidia estado={estado} />}
        {aba === "timeline" && <AbaTimeline estado={estado} />}
        {aba === "notas" && <AbaNotas estado={estado} />}
      </div>
    </div>
  );
}

// =================== ABAS ===================

function AbaVisaoGeral({ estado, status }: { estado: Estado; status?: StatusEstado }) {
  const user = useAuth((s) => s.user);
  const podeEditar =
    user?.papel === "admin" ||
    user?.papel === "editor_nacional" ||
    (user?.papel === "editor_estadual" && user?.estado_referencia_id === estado.id);

  const [editando, setEditando] = useState(false);
  const [form, setForm] = useState({
    cenario_governador: status?.cenario_governador ?? "indefinido",
    cenario_senado: status?.cenario_senado ?? "indefinido",
    nivel_consolidacao: status?.nivel_consolidacao ?? "em_construcao",
    prioridade_estrategica: status?.prioridade_estrategica ?? 3,
    cenario_governador_detalhe: status?.cenario_governador_detalhe ?? "",
    cenario_senado_detalhe: status?.cenario_senado_detalhe ?? "",
    observacao_geral: status?.observacao_geral ?? "",
  });

  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: async (payload: any) => {
      return (await api.patch(`/estados/${estado.sigla}/status`, payload)).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["status", estado.sigla] });
      queryClient.invalidateQueries({ queryKey: ["status_estados"] });
      setEditando(false);
    },
  });

  if (editando) {
    return (
      <div className="card max-w-3xl">
        <h2 className="text-lg font-display font-semibold mb-4">Editar status estratégico</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Cenário Governador</label>
            <select
              className="input"
              value={form.cenario_governador}
              onChange={(e) => setForm({ ...form, cenario_governador: e.target.value as any })}
            >
              <option value="candidatura_propria">Candidatura própria</option>
              <option value="vice_aliado">Vice / aliado</option>
              <option value="apoio_sem_cargo">Apoio sem cargo</option>
              <option value="oposicao">Oposição</option>
              <option value="indefinido">Indefinido</option>
            </select>
          </div>
          <div>
            <label className="label">Cenário Senado</label>
            <select
              className="input"
              value={form.cenario_senado}
              onChange={(e) => setForm({ ...form, cenario_senado: e.target.value as any })}
            >
              <option value="candidatura_propria">Candidatura própria</option>
              <option value="vice_aliado">Vice / aliado</option>
              <option value="apoio_sem_cargo">Apoio sem cargo</option>
              <option value="oposicao">Oposição</option>
              <option value="indefinido">Indefinido</option>
            </select>
          </div>
          <div>
            <label className="label">Nível de Consolidação</label>
            <select
              className="input"
              value={form.nivel_consolidacao}
              onChange={(e) => setForm({ ...form, nivel_consolidacao: e.target.value as any })}
            >
              <option value="consolidado">Consolidado</option>
              <option value="em_construcao">Em construção</option>
              <option value="disputado">Disputado</option>
              <option value="adverso">Adverso</option>
            </select>
          </div>
          <div>
            <label className="label">Prioridade Estratégica (1-5)</label>
            <input
              type="number"
              min={1}
              max={5}
              className="input"
              value={form.prioridade_estrategica}
              onChange={(e) =>
                setForm({ ...form, prioridade_estrategica: parseInt(e.target.value) })
              }
            />
          </div>
          <div className="col-span-2">
            <label className="label">Detalhe — Governador</label>
            <textarea
              className="input"
              rows={2}
              value={form.cenario_governador_detalhe}
              onChange={(e) => setForm({ ...form, cenario_governador_detalhe: e.target.value })}
            />
          </div>
          <div className="col-span-2">
            <label className="label">Detalhe — Senado</label>
            <textarea
              className="input"
              rows={2}
              value={form.cenario_senado_detalhe}
              onChange={(e) => setForm({ ...form, cenario_senado_detalhe: e.target.value })}
            />
          </div>
          <div className="col-span-2">
            <label className="label">Observação Geral</label>
            <textarea
              className="input"
              rows={3}
              value={form.observacao_geral}
              onChange={(e) => setForm({ ...form, observacao_geral: e.target.value })}
            />
          </div>
        </div>
        <div className="flex gap-2 mt-4">
          <button className="btn-primary" onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
            {mutation.isPending ? "Salvando…" : "Salvar"}
          </button>
          <button className="btn-secondary" onClick={() => setEditando(false)}>
            Cancelar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-4">
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display font-semibold text-gray-900">Status Estratégico</h2>
            {podeEditar && (
              <button onClick={() => setEditando(true)} className="text-sm text-info hover:underline inline-flex items-center gap-1">
                <Edit3 className="h-3 w-3" /> Editar
              </button>
            )}
          </div>
          {status ? (
            <div className="space-y-3">
              <CampoLeitura label="Nível de consolidação" valor={labelNivel(status.nivel_consolidacao)} />
              <CampoLeitura label="Cenário Governador" valor={labelCenario(status.cenario_governador)} detalhe={status.cenario_governador_detalhe} />
              <CampoLeitura label="Cenário Senado" valor={labelCenario(status.cenario_senado)} detalhe={status.cenario_senado_detalhe} />
              <CampoLeitura label="Prioridade" valor={"★".repeat(status.prioridade_estrategica) + "☆".repeat(5 - status.prioridade_estrategica)} />
              {status.observacao_geral && (
                <div>
                  <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">Observação</div>
                  <div className="text-sm whitespace-pre-line">{status.observacao_geral}</div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Status ainda não definido. Clique em editar para configurar.</p>
          )}
        </div>

        <CardBancadaCompacta estadoId={estado.id} />
        <CardCandidatosResumo estadoId={estado.id} />
      </div>

      <div className="space-y-4">
        <div className="card">
          <h3 className="text-sm font-display font-semibold text-gray-900 mb-2">Saúde dos dados</h3>
          <div className="space-y-1 text-xs text-gray-600">
            <div>Última pesquisa: <em className="text-gray-400">não capturada ainda</em></div>
            <div>Última matéria: <em className="text-gray-400">não capturada ainda</em></div>
            <div>Última edição: {status?.updated_at ? formatLocalDateTime(status.updated_at, "dd/MM HH:mm") : "—"}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CampoLeitura({ label, valor, detalhe }: { label: string; valor: string; detalhe?: string | null }) {
  return (
    <div>
      <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
      <div className="text-sm text-gray-900 font-medium">{valor}</div>
      {detalhe && <div className="text-xs text-gray-600 mt-0.5">{detalhe}</div>}
    </div>
  );
}

function labelNivel(n: string) {
  return ({ consolidado: "Consolidado", em_construcao: "Em construção", disputado: "Disputado", adverso: "Adverso" } as any)[n] || n;
}
function labelCenario(c: string) {
  return ({
    candidatura_propria: "Candidatura própria",
    vice_aliado: "Vice / aliado",
    apoio_sem_cargo: "Apoio sem cargo",
    oposicao: "Oposição",
    indefinido: "Indefinido",
  } as any)[c] || c;
}

interface Candidatura {
  id: string;
  cargo: string;
  status_registro: string;
  eh_titular: boolean;
  numero_urna: number | null;
  observacao: string | null;
  pessoa: { id: string; nome_completo: string; nome_urna: string; foto_url: string | null } | null;
  partido: { id: string; sigla: string; nome_completo: string; cor_hex: string | null; espectro: string | null } | null;
}

const CARGO_LABELS: Record<string, string> = {
  governador: "Governador",
  vice_governador: "Vice-Governador",
  senador: "Senador",
  deputado_federal: "Deputado Federal",
  deputado_estadual: "Deputado Estadual",
};

const CARGO_ORDEM = ["governador", "vice_governador", "senador", "deputado_federal", "deputado_estadual"];

function AbaCandidaturas({ estado }: { estado: Estado }) {
  const { data: candidaturas = [] } = useQuery({
    queryKey: ["candidaturas", estado.id],
    queryFn: async () =>
      (await api.get<Candidatura[]>("/candidaturas", { params: { estado_id: estado.id } })).data,
  });

  if (candidaturas.length === 0) {
    return (
      <div className="card text-sm text-gray-500">
        <p>Nenhuma candidatura cadastrada para este estado.</p>
        <p className="mt-2 text-xs">Para popular: rode <code>python -m app.seeds.runner_gte</code> no backend (importa dados do GTE 17/04/2026).</p>
      </div>
    );
  }

  // Agrupa por cargo
  const grupos = candidaturas.reduce<Record<string, Candidatura[]>>((acc, c) => {
    (acc[c.cargo] ??= []).push(c);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {CARGO_ORDEM.filter((cargo) => grupos[cargo]).map((cargo) => (
        <section key={cargo}>
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">
            {CARGO_LABELS[cargo] ?? cargo} ({grupos[cargo].length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {grupos[cargo].map((c) => <CardCandidato key={c.id} c={c} />)}
          </div>
        </section>
      ))}
    </div>
  );
}

function CardCandidato({ c }: { c: Candidatura }) {
  const partidoColor = c.partido?.cor_hex || "#9CA3AF";
  return (
    <div className="card hover:shadow-md transition !p-3">
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-full flex-shrink-0 bg-gray-100 flex items-center justify-center text-sm font-semibold text-gray-500">
          {c.pessoa?.nome_urna?.[0] || c.pessoa?.nome_completo?.[0] || "?"}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <div className="font-display font-semibold text-gray-900 leading-tight truncate">
              {c.pessoa?.nome_urna || c.pessoa?.nome_completo || "—"}
            </div>
            {!c.eh_titular && (
              <span className="badge bg-gray-100 text-gray-600 text-xs">vice</span>
            )}
          </div>
          {c.partido && (
            <div className="flex items-center gap-1 mb-1">
              <span
                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: partidoColor }}
              />
              <span className="text-xs font-mono text-gray-700">{c.partido.sigla}</span>
              {c.partido.espectro && (
                <span className="text-xs text-gray-400 capitalize">· {c.partido.espectro.replace(/_/g, " ")}</span>
              )}
            </div>
          )}
          <div className="text-xs text-gray-500 capitalize">
            <span className="badge bg-blue-50 text-info text-xs">
              {c.status_registro.replace(/_/g, " ")}
            </span>
          </div>
          {c.observacao && (
            <p className="text-xs text-gray-600 mt-2 italic">{c.observacao}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function AbaPesquisas({ estado }: { estado: Estado }) {
  const { data: pesquisas = [] } = useQuery({
    queryKey: ["pesquisas", estado.id],
    queryFn: async () => (await api.get<Pesquisa[]>("/pesquisas", { params: { estado_id: estado.id } })).data,
  });

  return (
    <div className="space-y-4">
      {/* Painel especializado: avaliação do governador + intenção 1T */}
      <PainelGovernador estado={estado} />

      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display font-semibold text-gray-900">
            Pesquisas cadastradas ({pesquisas.length})
          </h2>
          <Link to="/pesquisas/importar" className="text-xs text-info hover:underline">
            + importar pesquisa JSON
          </Link>
        </div>

        {pesquisas.length === 0 ? (
          <p className="text-sm text-gray-500">
            Nenhuma pesquisa cadastrada para este estado ainda.
          </p>
        ) : (
          <div className="space-y-2">
            {pesquisas.map((p) => <CardPesquisaComIA key={p.id} pesquisa={p} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function CardPesquisaComIA({ pesquisa }: { pesquisa: Pesquisa }) {
  const [mostrarIA, setMostrarIA] = useState(false);

  const { data: cenariosData } = useQuery({
    queryKey: ["pesquisa-cenarios-card", pesquisa.id],
    queryFn: async () => (await api.get(`/pesquisas/${pesquisa.id}/cenarios`)).data,
  });

  const { data: dadosBrutos } = useQuery<{ analise_ia: any | null; formato_origem: string | null }>({
    queryKey: ["pesquisa-brutos", pesquisa.id],
    queryFn: async () => (await api.get(`/admin/pesquisas/${pesquisa.id}/dados-brutos`)).data,
    retry: false,
    enabled: mostrarIA,
  });

  const queryClient = useQueryClient();
  const reanalisar = useMutation({
    mutationFn: async () =>
      (await api.post(`/admin/pesquisas/${pesquisa.id}/analisar-ia?aplicar_sugestoes=true`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pesquisa-brutos", pesquisa.id] });
      queryClient.invalidateQueries({ queryKey: ["status"] });
      queryClient.invalidateQueries({ queryKey: ["status_estados"] });
    },
  });

  const analise = dadosBrutos?.analise_ia;

  return (
    <div className="card !p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium">{pesquisa.contratante || "Pesquisa"}</span>
        <div className="flex items-center gap-2">
          {pesquisa.registro_tse && (
            <span className="badge bg-blue-50 text-info text-xs font-mono">
              {pesquisa.registro_tse}
            </span>
          )}
          <span className="text-xs text-gray-500">
            {pesquisa.data_fim_campo &&
              format(parseISO(pesquisa.data_fim_campo), "dd MMM yyyy", { locale: ptBR })}
          </span>
        </div>
      </div>
      <div className="text-xs text-gray-500 mt-1">
        Amostra {pesquisa.amostra} · margem ±{pesquisa.margem_erro}pp · {pesquisa.metodologia} ·{" "}
        {pesquisa.tipo_cenario}
      </div>

      {/* Resumo de cenários se houver intenção de voto */}
      {cenariosData?.cenarios && cenariosData.cenarios.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <div className="text-xs text-gray-500 mb-1">{cenariosData.cenarios.length} cenário(s) de intenção de voto:</div>
          {cenariosData.cenarios.slice(0, 1).map((cen: any) => (
            <div key={cen.label} className="text-xs">
              <div className="font-medium text-gray-700 mb-1">{cen.label}</div>
              {cen.candidatos.slice(0, 4).map((c: any) => (
                <div key={c.nome} className="flex items-center justify-between text-xs ml-2">
                  <span className="truncate">{c.nome}</span>
                  <span className="font-mono font-bold text-info ml-2">{c.percentual}%</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      <div className="mt-2 flex items-center gap-2 pt-2 border-t border-gray-100">
        <Link to={`/pesquisas/${pesquisa.id}`} className="text-xs text-info hover:underline">
          ver detalhe completo →
        </Link>
        <button
          onClick={() => setMostrarIA(!mostrarIA)}
          className="text-xs text-info hover:underline"
        >
          {mostrarIA ? "esconder análise IA" : "ver análise IA"}
        </button>
        <button
          onClick={() => reanalisar.mutate()}
          disabled={reanalisar.isPending}
          className="text-xs text-gray-500 hover:text-info"
        >
          {reanalisar.isPending ? "analisando…" : "↻ re-analisar"}
        </button>
      </div>

      {mostrarIA && (
        <div className="mt-2 text-xs space-y-2 pt-2 border-t border-gray-100">
          {!dadosBrutos && <span className="text-gray-400">Carregando…</span>}
          {dadosBrutos && !analise && (
            <div className="text-gray-500">
              Pesquisa sem análise IA. Clique em "↻ re-analisar" para gerar (requer ANTHROPIC_API_KEY).
            </div>
          )}
          {analise && (
            <>
              {analise.resumo_executivo && (
                <div>
                  <div className="text-xs uppercase tracking-wide text-gray-500">Resumo</div>
                  <p className="text-gray-800">{analise.resumo_executivo}</p>
                </div>
              )}
              {analise.implicacoes_pt && (
                <div>
                  <div className="text-xs uppercase tracking-wide text-gray-500">
                    Implicações para o PT
                  </div>
                  <p className="text-gray-800">{analise.implicacoes_pt}</p>
                </div>
              )}
              {analise.tendencias_observadas?.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">Tendências</div>
                  {analise.tendencias_observadas.map((t: any, i: number) => (
                    <div key={i}>
                      <span
                        className={
                          t.direcao === "subindo"
                            ? "text-sucesso"
                            : t.direcao === "caindo"
                              ? "text-alerta"
                              : "text-gray-500"
                        }
                      >
                        {t.direcao === "subindo" ? "↗" : t.direcao === "caindo" ? "↘" : "→"}
                      </span>{" "}
                      <strong>{t.metrica}</strong>: {t.magnitude} — {t.implicacao}
                    </div>
                  ))}
                </div>
              )}
              {analise.alertas?.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">Alertas</div>
                  {analise.alertas.map((a: any, i: number) => (
                    <div
                      key={i}
                      className={`px-2 py-1 rounded mb-1 ${
                        a.tipo === "risco"
                          ? "bg-red-50 text-red-900"
                          : a.tipo === "oportunidade"
                            ? "bg-green-50 text-green-900"
                            : "bg-yellow-50 text-yellow-900"
                      }`}
                    >
                      [{a.tipo}] {a.descricao}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

interface VotacaoHistorica {
  ano: number;
  cargo: string;
  votos_totais: number;
  percentual_total: number | null;
  bancada_eleita: number;
}

function AbaBancada({ estado }: { estado: Estado }) {
  const { data: historico = [] } = useQuery({
    queryKey: ["historico", estado.id, "PT"],
    queryFn: async () =>
      (await api.get<VotacaoHistorica[]>("/historico/votacao-partido-estado", {
        params: { estado_id: estado.id, partido_sigla: "PT" },
      })).data,
  });

  if (historico.length === 0) {
    return (
      <div className="card text-sm text-gray-500">
        <p>Nenhum histórico cadastrado para este estado.</p>
        <p className="mt-2 text-xs">Para popular: rode <code>python -m app.seeds.runner_gte</code> no backend.</p>
      </div>
    );
  }

  // Separa por cargo
  const federal = historico.filter((h) => h.cargo === "deputado_federal").sort((a, b) => a.ano - b.ano);
  const estadual = historico.filter((h) => h.cargo === "deputado_estadual").sort((a, b) => a.ano - b.ano);

  const calcVariacao = (atual: VotacaoHistorica, anterior?: VotacaoHistorica) => {
    if (!anterior || !atual.percentual_total || !anterior.percentual_total) return null;
    return atual.percentual_total - anterior.percentual_total;
  };

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="font-display font-semibold text-gray-900 mb-3">
          Bancada Federal (Deputados Federais — PT no estado)
        </h2>
        <TabelaBancada items={federal} />
      </div>

      <div className="card">
        <h2 className="font-display font-semibold text-gray-900 mb-3">
          Bancada Estadual (Deputados Estaduais — PT)
        </h2>
        <TabelaBancada items={estadual} />
      </div>

      <div className="card !p-3 bg-blue-50 border-blue-200 text-xs text-blue-900">
        <strong>Projeção 2026:</strong> a estimativa para a próxima eleição (cenários conservador/mediano/otimista) será calculada quando a Fase 5 (modelo de regressão treinado nas eleições históricas) for implementada.
      </div>
    </div>
  );
}

function TabelaBancada({ items }: { items: VotacaoHistorica[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-gray-500">Sem dados.</p>;
  }
  return (
    <table className="w-full text-sm">
      <thead className="border-b border-gray-200 text-xs text-gray-500 uppercase">
        <tr>
          <th className="text-left py-2 px-2">Eleição</th>
          <th className="text-right py-2 px-2">Cadeiras</th>
          <th className="text-right py-2 px-2">Votação Absoluta</th>
          <th className="text-right py-2 px-2">% Válidos</th>
          <th className="text-right py-2 px-2">Variação</th>
        </tr>
      </thead>
      <tbody>
        {items.map((h, i) => {
          const ant = i > 0 ? items[i - 1] : undefined;
          const variacao =
            ant && h.percentual_total != null && ant.percentual_total != null
              ? h.percentual_total - ant.percentual_total
              : null;
          return (
            <tr key={`${h.ano}-${h.cargo}`} className="border-b border-gray-100">
              <td className="py-2 px-2 font-mono">{h.ano}</td>
              <td className="py-2 px-2 text-right font-mono font-semibold">{h.bancada_eleita}</td>
              <td className="py-2 px-2 text-right font-mono">{h.votos_totais.toLocaleString("pt-BR")}</td>
              <td className="py-2 px-2 text-right font-mono">
                {h.percentual_total != null ? `${h.percentual_total.toFixed(2)}%` : "—"}
              </td>
              <td className="py-2 px-2 text-right font-mono">
                {variacao != null ? (
                  <span className={variacao > 0 ? "text-sucesso" : variacao < 0 ? "text-alerta" : "text-gray-500"}>
                    {variacao > 0 ? "+" : ""}{variacao.toFixed(2)}pp
                  </span>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function AbaMidia({ estado }: { estado: Estado }) {
  const { data: materias = [] } = useQuery({
    queryKey: ["materias", estado.id],
    queryFn: async () => (await api.get<Materia[]>("/midia/materias", { params: { estado_id: estado.id, limit: 30 } })).data,
  });

  if (materias.length === 0) {
    return (
      <div className="card text-sm text-gray-500">
        Nenhuma matéria capturada. A ingestão de RSS (Fase 4 — Prompt 12) povoará esta seção em tempo real.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {materias.map((m) => (
        <article key={m.id} className="card !p-4">
          <a href={m.url} target="_blank" rel="noreferrer" className="font-display font-semibold text-gray-900 hover:text-info">
            {m.titulo}
          </a>
          {m.snippet && <p className="text-sm text-gray-600 mt-1">{m.snippet}</p>}
          <div className="text-xs text-gray-400 mt-2">
            {formatLocalDateTime(m.data_publicacao, "dd MMM yyyy, HH:mm")}
          </div>
        </article>
      ))}
    </div>
  );
}

function AbaTimeline({ estado }: { estado: Estado }) {
  const { data: eventos = [] } = useQuery({
    queryKey: ["eventos", estado.id],
    queryFn: async () => (await api.get<Evento[]>("/eventos", { params: { estado_id: estado.id, limit: 100 } })).data,
  });

  if (eventos.length === 0) {
    return (
      <div className="card text-sm text-gray-500">
        Nenhum evento registrado. Use a página <Link to="/eventos" className="text-info hover:underline">/eventos</Link> para criar manualmente.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {eventos.map((e) => (
        <div key={e.id} className="border-l-2 border-info pl-4 py-1">
          <div className="text-xs text-gray-400 font-mono">
            {formatLocalDateTime(e.data_evento, "dd MMM yyyy HH:mm")}
          </div>
          <div className="font-display font-semibold text-gray-900">{e.titulo}</div>
          {e.descricao && <p className="text-sm text-gray-600 mt-1">{e.descricao}</p>}
          {e.fonte_url && (
            <a href={e.fonte_url} target="_blank" rel="noreferrer" className="text-xs text-info hover:underline mt-1 inline-block">
              {e.fonte_descricao || e.fonte_url} →
            </a>
          )}
        </div>
      ))}
    </div>
  );
}

function AbaNotas({ estado }: { estado: Estado }) {
  const { data: notas = [] } = useQuery({
    queryKey: ["notas", estado.id],
    queryFn: async () => (await api.get<Nota[]>("/notas", { params: { estado_id: estado.id, limit: 100 } })).data,
  });

  if (notas.length === 0) {
    return (
      <div className="card text-sm text-gray-500">
        <FileText className="inline h-4 w-4 mr-1" />
        Nenhuma nota editorial vinculada. Use <Link to="/notas" className="text-info hover:underline">/notas</Link> para criar.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {notas.map((n) => (
        <article key={n.id} className="card !p-4">
          <div className="flex items-center justify-between mb-1">
            <h3 className="font-display font-semibold text-gray-900">{n.titulo}</h3>
            <span className="badge bg-gray-100 text-gray-700">{n.sensibilidade}</span>
          </div>
          <div className="text-xs text-gray-500 mb-2">
            {formatLocalDateTime(n.created_at, "dd MMM yyyy")} · {n.tema}
          </div>
          <p className="text-sm text-gray-700 whitespace-pre-line line-clamp-4">{n.conteudo}</p>
        </article>
      ))}
    </div>
  );
}

// =================== Cards compactos para Visão Geral ===================

function CardBancadaCompacta({ estadoId }: { estadoId: string }) {
  const { data: historico = [] } = useQuery({
    queryKey: ["historico", estadoId, "PT"],
    queryFn: async () =>
      (await api.get<VotacaoHistorica[]>("/historico/votacao-partido-estado", {
        params: { estado_id: estadoId, partido_sigla: "PT" },
      })).data,
  });

  if (historico.length === 0) return null;

  const federal = historico.filter((h) => h.cargo === "deputado_federal").sort((a, b) => a.ano - b.ano);
  const estadual = historico.filter((h) => h.cargo === "deputado_estadual").sort((a, b) => a.ano - b.ano);

  return (
    <div className="card">
      <h2 className="font-display font-semibold text-gray-900 mb-3">Bancada PT — Histórico</h2>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <MiniBancada title="Federal" items={federal} />
        <MiniBancada title="Estadual" items={estadual} />
      </div>
    </div>
  );
}

function MiniBancada({ title, items }: { title: string; items: VotacaoHistorica[] }) {
  if (items.length === 0) return <div className="text-xs text-gray-500">Sem dados de {title}</div>;
  return (
    <div>
      <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{title}</div>
      <table className="w-full text-xs">
        <tbody>
          {items.map((h) => (
            <tr key={h.ano} className="border-b border-gray-100 last:border-0">
              <td className="py-1 text-gray-500">{h.ano}</td>
              <td className="py-1 text-right">
                <span className="font-mono font-bold">{h.bancada_eleita}</span>
                <span className="text-gray-400 ml-1">cad.</span>
              </td>
              <td className="py-1 text-right font-mono text-gray-600">
                {h.percentual_total != null ? `${h.percentual_total.toFixed(1)}%` : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CardCandidatosResumo({ estadoId }: { estadoId: string }) {
  const { data: candidaturas = [] } = useQuery({
    queryKey: ["candidaturas", estadoId],
    queryFn: async () =>
      (await api.get<Candidatura[]>("/candidaturas", { params: { estado_id: estadoId } })).data,
  });

  if (candidaturas.length === 0) return null;

  const governo = candidaturas.filter((c) => c.cargo === "governador");
  const senado = candidaturas.filter((c) => c.cargo === "senador");

  return (
    <div className="card">
      <h2 className="font-display font-semibold text-gray-900 mb-3">Pré-candidatos 2026</h2>
      {governo.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            Governador ({governo.length})
          </div>
          <div className="space-y-1">
            {governo.map((c) => (
              <div key={c.id} className="flex items-center gap-2 text-sm">
                <span
                  className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: c.partido?.cor_hex || "#9CA3AF" }}
                />
                <span className="font-medium">{c.pessoa?.nome_urna}</span>
                <span className="text-gray-500 text-xs font-mono">({c.partido?.sigla})</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {senado.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">
            Senado ({senado.length})
          </div>
          <div className="space-y-1">
            {senado.map((c) => (
              <div key={c.id} className="flex items-center gap-2 text-sm">
                <span
                  className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                  style={{ backgroundColor: c.partido?.cor_hex || "#9CA3AF" }}
                />
                <span className="font-medium">{c.pessoa?.nome_urna}</span>
                <span className="text-gray-500 text-xs font-mono">({c.partido?.sigla})</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
