import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Bell, Plus, Trash2, ToggleLeft, ToggleRight, Sparkles } from "lucide-react";

import { api } from "../lib/api";
import { Estado, Partido } from "../lib/types";

interface Alerta {
  id: string;
  nome: string;
  tipo: string;
  configuracao: any;
  canais: string[];
  ativo: boolean;
  frequencia_max: string;
  ultimo_disparo: string | null;
  total_disparos: number;
  created_at: string;
}

const TIPOS_ALERTA = [
  { key: "pesquisa", label: "Nova pesquisa", desc: "Quando uma pesquisa for divulgada para os estados/cargos selecionados" },
  { key: "movimentacao_politica", label: "Movimentação política", desc: "Filiações, candidaturas, coligações novas" },
  { key: "midia", label: "Menções na mídia", desc: "Quando matérias mencionarem pessoas/partidos/estados específicos" },
  { key: "editorial", label: "Notas editoriais", desc: "Novas notas com sensibilidade configurada" },
];

export function AlertasPage() {
  const [showForm, setShowForm] = useState(false);
  const queryClient = useQueryClient();

  const { data: alertas = [] } = useQuery({
    queryKey: ["alertas"],
    queryFn: async () => (await api.get<Alerta[]>("/alertas")).data,
  });

  const toggleMutation = useMutation({
    mutationFn: async (vars: { id: string; ativo: boolean }) =>
      (await api.patch(`/alertas/${vars.id}`, { ativo: vars.ativo })).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alertas"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => (await api.delete(`/alertas/${id}`)).data,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alertas"] }),
  });

  const avaliarMutation = useMutation({
    mutationFn: async () =>
      (await api.post("/alertas/avaliar-agora?sincrono=true")).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alertas"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-contagem"] });
    },
  });

  return (
    <div className="p-6 max-w-5xl">
      <header className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-display font-semibold text-gray-900 flex items-center gap-2">
            <Bell className="h-6 w-6 text-info" /> Meus Alertas
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Configure regras para receber notificações automáticas. Avaliação a cada 5 min.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => avaliarMutation.mutate()}
            disabled={avaliarMutation.isPending}
            className="btn-secondary text-sm"
          >
            <Sparkles className="h-4 w-4" /> Avaliar agora
          </button>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary">
            <Plus className="h-4 w-4" /> Novo alerta
          </button>
        </div>
      </header>

      {avaliarMutation.data && (
        <div className="card !p-3 mb-3 bg-blue-50 border-blue-200 text-sm">
          {avaliarMutation.data.alertas_avaliados} alertas avaliados ·{" "}
          <strong>{avaliarMutation.data.notificacoes_criadas}</strong> notificações criadas
        </div>
      )}

      {showForm && <NovoAlertaForm onClose={() => setShowForm(false)} />}

      {alertas.length === 0 ? (
        <div className="card text-center text-gray-500 py-8">
          Nenhum alerta configurado. Crie um para começar a receber notificações.
        </div>
      ) : (
        <div className="space-y-2">
          {alertas.map((a) => {
            const tipoMeta = TIPOS_ALERTA.find((t) => t.key === a.tipo);
            return (
              <div key={a.id} className="card !p-4">
                <div className="flex items-start gap-3">
                  <button
                    onClick={() => toggleMutation.mutate({ id: a.id, ativo: !a.ativo })}
                    className={a.ativo ? "text-sucesso" : "text-gray-400"}
                  >
                    {a.ativo ? <ToggleRight className="h-6 w-6" /> : <ToggleLeft className="h-6 w-6" />}
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium">{a.nome}</span>
                      <span className="badge bg-blue-50 text-info text-xs">{tipoMeta?.label || a.tipo}</span>
                      {!a.ativo && <span className="badge bg-gray-100 text-gray-500 text-xs">inativo</span>}
                    </div>
                    <div className="text-xs text-gray-500">
                      {a.total_disparos} notificações disparadas
                      {a.ultimo_disparo && ` · último: ${format(parseISO(a.ultimo_disparo), "dd/MM HH:mm", { locale: ptBR })}`}
                    </div>
                    {Object.keys(a.configuracao).length > 0 && (
                      <details className="mt-1">
                        <summary className="text-xs text-info cursor-pointer">configuração</summary>
                        <pre className="text-[10px] bg-gray-50 p-2 rounded mt-1 overflow-x-auto">
                          {JSON.stringify(a.configuracao, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                  <button
                    onClick={() => {
                      if (confirm("Excluir este alerta?")) deleteMutation.mutate(a.id);
                    }}
                    className="text-gray-400 hover:text-alerta"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function NovoAlertaForm({ onClose }: { onClose: () => void }) {
  const [tipo, setTipo] = useState("pesquisa");
  const [nome, setNome] = useState("");
  const [estadosIds, setEstadosIds] = useState<string[]>([]);
  const [pessoaIds, setPessoaIds] = useState<string[]>([]);
  const [partidoIds, setPartidoIds] = useState<string[]>([]);
  const [sensibilidades, setSensibilidades] = useState<string[]>(["interno", "restrito_direcao"]);
  const [apenasAcao, setApenasAcao] = useState(false);

  const queryClient = useQueryClient();

  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });
  const { data: partidos = [] } = useQuery({
    queryKey: ["partidos"],
    queryFn: async () => (await api.get<Partido[]>("/partidos")).data,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      let configuracao: any = {};
      if (tipo === "pesquisa" || tipo === "movimentacao_politica") {
        configuracao = { estados_ids: estadosIds };
      } else if (tipo === "midia") {
        configuracao = { pessoa_ids: pessoaIds, partido_ids: partidoIds, estado_ids: estadosIds };
      } else if (tipo === "editorial") {
        configuracao = { sensibilidades, apenas_acao_requerida: apenasAcao };
      }

      return (await api.post("/alertas", {
        nome: nome || `Alerta ${tipo}`,
        tipo,
        configuracao,
        canais: ["in_app"],
        frequencia_max: "imediato",
      })).data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alertas"] });
      onClose();
    },
  });

  return (
    <div className="card mb-4">
      <h3 className="font-semibold mb-3">Novo alerta</h3>
      <div className="space-y-3">
        <div>
          <label className="label !text-xs">Tipo</label>
          <div className="grid grid-cols-2 gap-2">
            {TIPOS_ALERTA.map((t) => (
              <button
                key={t.key}
                onClick={() => setTipo(t.key)}
                className={`text-left p-2 rounded border text-sm ${
                  tipo === t.key ? "bg-blue-50 border-info" : "bg-white border-gray-200"
                }`}
              >
                <div className="font-medium">{t.label}</div>
                <div className="text-xs text-gray-500">{t.desc}</div>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label !text-xs">Nome</label>
          <input
            className="input"
            placeholder={`ex: Alerta de ${tipo}`}
            value={nome}
            onChange={(e) => setNome(e.target.value)}
          />
        </div>

        {(tipo === "pesquisa" || tipo === "movimentacao_politica" || tipo === "midia") && (
          <div>
            <label className="label !text-xs">
              Estados (vazio = todos)
            </label>
            <select
              multiple
              className="input min-h-[120px]"
              value={estadosIds}
              onChange={(e) => setEstadosIds(Array.from(e.target.selectedOptions, (o) => o.value))}
            >
              {estados.sort((a, b) => a.nome.localeCompare(b.nome)).map((e) => (
                <option key={e.id} value={e.id}>{e.sigla} - {e.nome}</option>
              ))}
            </select>
          </div>
        )}

        {tipo === "midia" && (
          <div>
            <label className="label !text-xs">Partidos a monitorar</label>
            <select
              multiple
              className="input min-h-[100px]"
              value={partidoIds}
              onChange={(e) => setPartidoIds(Array.from(e.target.selectedOptions, (o) => o.value))}
            >
              {partidos.map((p) => (
                <option key={p.id} value={p.id}>{p.sigla}</option>
              ))}
            </select>
          </div>
        )}

        {tipo === "editorial" && (
          <>
            <div>
              <label className="label !text-xs">Sensibilidades</label>
              {["publico", "interno", "restrito_direcao"].map((s) => (
                <label key={s} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={sensibilidades.includes(s)}
                    onChange={(e) => {
                      setSensibilidades(
                        e.target.checked
                          ? [...sensibilidades, s]
                          : sensibilidades.filter((x) => x !== s)
                      );
                    }}
                  />
                  {s}
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={apenasAcao}
                onChange={(e) => setApenasAcao(e.target.checked)}
              />
              Apenas notas com ação requerida
            </label>
          </>
        )}

        <div className="flex gap-2">
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="btn-primary"
          >
            Criar alerta
          </button>
          <button onClick={onClose} className="btn-secondary">
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
