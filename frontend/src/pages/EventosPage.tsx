import { FormEvent, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Plus } from "lucide-react";

import { api } from "../lib/api";
import { Estado, Evento } from "../lib/types";
import { useAuth } from "../store/auth";

const TIPO_EVENTO = [
  "filiacao",
  "desfiliacao",
  "anuncio_pre_candidatura",
  "anuncio_candidatura",
  "registro_candidatura",
  "desistencia",
  "coligacao_anunciada",
  "coligacao_alterada",
  "pesquisa_publicada",
  "mudanca_lideranca",
  "voto_relevante",
  "declaracao_publica",
  "materia_relevante",
  "decisao_judicial",
  "outros",
];

export function EventosPage() {
  const user = useAuth((s) => s.user);
  const podeAdicionar = user && ["admin", "editor_nacional", "editor_estadual"].includes(user.papel);

  const [showForm, setShowForm] = useState(false);
  const [tipoFilter, setTipoFilter] = useState<string>("");

  const { data: eventos = [] } = useQuery({
    queryKey: ["eventos", "list", tipoFilter],
    queryFn: async () =>
      (await api.get<Evento[]>("/eventos", { params: { tipo: tipoFilter || undefined, limit: 100 } })).data,
  });

  return (
    <div className="p-6 max-w-5xl">
      <header className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-display font-semibold text-gray-900">Timeline Política</h1>
          <p className="text-sm text-gray-500 mt-1">{eventos.length} eventos · ordenados do mais recente</p>
        </div>
        {podeAdicionar && (
          <button onClick={() => setShowForm(true)} className="btn-primary">
            <Plus className="h-4 w-4" /> Novo evento
          </button>
        )}
      </header>

      <div className="mb-4">
        <select className="input max-w-xs" value={tipoFilter} onChange={(e) => setTipoFilter(e.target.value)}>
          <option value="">Todos os tipos</option>
          {TIPO_EVENTO.map((t) => (
            <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
          ))}
        </select>
      </div>

      {showForm && <NovoEventoForm onClose={() => setShowForm(false)} />}

      <div className="space-y-3">
        {eventos.length === 0 && (
          <div className="card text-sm text-gray-500">Nenhum evento registrado.</div>
        )}
        {eventos.map((e) => (
          <article key={e.id} className="card !p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="badge bg-gray-100 text-gray-700 text-xs capitalize">
                    {e.tipo.replace(/_/g, " ")}
                  </span>
                  <span className="text-xs text-gray-400 font-mono">
                    {format(new Date(e.data_evento), "dd MMM yyyy HH:mm", { locale: ptBR })}
                  </span>
                  {e.automatico && (
                    <span className="badge bg-purple-50 text-purple-700 text-xs">automático</span>
                  )}
                </div>
                <h3 className="font-display font-semibold text-gray-900">{e.titulo}</h3>
                {e.descricao && <p className="text-sm text-gray-600 mt-1">{e.descricao}</p>}
                {e.fonte_url && (
                  <a href={e.fonte_url} target="_blank" rel="noreferrer" className="text-xs text-info hover:underline mt-2 inline-block">
                    {e.fonte_descricao || "Fonte"} →
                  </a>
                )}
              </div>
              <div className="text-xs text-gray-400">★{e.relevancia}</div>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function NovoEventoForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });

  const [form, setForm] = useState({
    tipo: "outros",
    titulo: "",
    descricao: "",
    estado_id: "",
    data_evento: new Date().toISOString().slice(0, 16),
    fonte_url: "",
    fonte_descricao: "",
    relevancia: 3,
    sensibilidade: "publico",
  });

  const mutation = useMutation({
    mutationFn: async (payload: any) => (await api.post("/eventos", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["eventos"] });
      onClose();
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    const payload: any = { ...form };
    if (!payload.estado_id) delete payload.estado_id;
    if (!payload.fonte_url) delete payload.fonte_url;
    if (!payload.fonte_descricao) delete payload.fonte_descricao;
    payload.data_evento = new Date(payload.data_evento).toISOString();
    mutation.mutate(payload);
  }

  return (
    <form onSubmit={submit} className="card mb-4 space-y-3">
      <h2 className="font-display font-semibold">Novo evento</h2>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Tipo</label>
          <select className="input" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
            {TIPO_EVENTO.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Estado</label>
          <select className="input" value={form.estado_id} onChange={(e) => setForm({ ...form, estado_id: e.target.value })}>
            <option value="">Nacional / nenhum</option>
            {estados.map((e) => <option key={e.id} value={e.id}>{e.sigla}</option>)}
          </select>
        </div>
        <div className="col-span-2">
          <label className="label">Título *</label>
          <input className="input" required value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} />
        </div>
        <div className="col-span-2">
          <label className="label">Descrição</label>
          <textarea className="input" rows={3} value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} />
        </div>
        <div>
          <label className="label">Data</label>
          <input type="datetime-local" className="input" value={form.data_evento} onChange={(e) => setForm({ ...form, data_evento: e.target.value })} />
        </div>
        <div>
          <label className="label">Relevância (1-5)</label>
          <input type="number" min={1} max={5} className="input" value={form.relevancia} onChange={(e) => setForm({ ...form, relevancia: +e.target.value })} />
        </div>
        <div>
          <label className="label">URL da fonte</label>
          <input className="input" value={form.fonte_url} onChange={(e) => setForm({ ...form, fonte_url: e.target.value })} />
        </div>
        <div>
          <label className="label">Descrição da fonte</label>
          <input className="input" value={form.fonte_descricao} onChange={(e) => setForm({ ...form, fonte_descricao: e.target.value })} />
        </div>
      </div>
      <div className="flex gap-2">
        <button type="submit" className="btn-primary" disabled={mutation.isPending}>
          {mutation.isPending ? "Salvando…" : "Salvar"}
        </button>
        <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
      </div>
    </form>
  );
}
