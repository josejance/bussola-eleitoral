import { FormEvent, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";

import { api } from "../lib/api";
import { Estado, Nota } from "../lib/types";
import { useAuth } from "../store/auth";
import { formatLocalDateTime } from "../lib/datetime";

const TEMAS = ["governo", "senado", "bancada_federal", "bancada_estadual", "coligacao", "articulacao_geral", "midia", "inteligencia", "outros"];
const SENSIB = ["publico", "interno", "restrito_direcao"];

const SENSIB_CLASS: Record<string, string> = {
  publico: "bg-green-50 text-green-700",
  interno: "bg-blue-50 text-blue-700",
  restrito_direcao: "bg-red-50 text-red-700",
};

export function NotasPage() {
  const user = useAuth((s) => s.user);
  const podeAdicionar = user && ["admin", "editor_nacional", "editor_estadual"].includes(user.papel);

  const [showForm, setShowForm] = useState(false);
  const [estadoFilter, setEstadoFilter] = useState<string>("");
  const [temaFilter, setTemaFilter] = useState<string>("");

  const { data: notas = [] } = useQuery({
    queryKey: ["notas", "list", estadoFilter, temaFilter],
    queryFn: async () =>
      (await api.get<Nota[]>("/notas", { params: { estado_id: estadoFilter || undefined, tema: temaFilter || undefined, limit: 100 } })).data,
  });
  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });

  return (
    <div className="p-6 max-w-5xl">
      <header className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-display font-semibold text-gray-900">Notas Editoriais</h1>
          <p className="text-sm text-gray-500 mt-1">{notas.length} notas (filtradas pelo seu nível de permissão)</p>
        </div>
        {podeAdicionar && (
          <button onClick={() => setShowForm(true)} className="btn-primary">
            <Plus className="h-4 w-4" /> Nova nota
          </button>
        )}
      </header>

      <div className="flex gap-3 mb-4">
        <select className="input max-w-xs" value={estadoFilter} onChange={(e) => setEstadoFilter(e.target.value)}>
          <option value="">Todos os estados</option>
          {estados.map((e) => <option key={e.id} value={e.id}>{e.sigla}</option>)}
        </select>
        <select className="input max-w-xs" value={temaFilter} onChange={(e) => setTemaFilter(e.target.value)}>
          <option value="">Todos os temas</option>
          {TEMAS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {showForm && <NovaNotaForm estados={estados} onClose={() => setShowForm(false)} />}

      <div className="space-y-3">
        {notas.length === 0 && (
          <div className="card text-sm text-gray-500">
            Nenhuma nota visível com seu nível de permissão.
          </div>
        )}
        {notas.map((n) => (
          <article key={n.id} className="card !p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className={`badge ${SENSIB_CLASS[n.sensibilidade]}`}>{n.sensibilidade}</span>
                <span className="badge bg-gray-100 text-gray-700 capitalize">{n.tema.replace(/_/g, " ")}</span>
                {n.acao_requerida && (
                  <span className="badge bg-orange-50 text-orange-700">Ação requerida</span>
                )}
              </div>
              <span className="text-xs text-gray-400">
                {formatLocalDateTime(n.created_at, "dd MMM yyyy")} · v{n.versao}
              </span>
            </div>
            <h3 className="font-display font-semibold text-gray-900 mb-2">{n.titulo}</h3>
            <p className="text-sm text-gray-700 whitespace-pre-line">{n.conteudo}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function NovaNotaForm({ estados, onClose }: { estados: Estado[]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    titulo: "",
    conteudo: "",
    tema: "outros",
    sensibilidade: "interno",
    estado_id: "",
    acao_requerida: false,
    fonte_tipo: "",
    fonte_referencia: "",
    fonte_url: "",
  });

  const mutation = useMutation({
    mutationFn: async (payload: any) => (await api.post("/notas", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notas"] });
      onClose();
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    const payload: any = { ...form };
    Object.keys(payload).forEach((k) => { if (payload[k] === "") delete payload[k]; });
    mutation.mutate(payload);
  }

  return (
    <form onSubmit={submit} className="card mb-4 space-y-3">
      <h2 className="font-display font-semibold">Nova nota editorial</h2>
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className="label">Título *</label>
          <input className="input" required value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} />
        </div>
        <div>
          <label className="label">Estado</label>
          <select className="input" value={form.estado_id} onChange={(e) => setForm({ ...form, estado_id: e.target.value })}>
            <option value="">Nacional</option>
            {estados.map((e) => <option key={e.id} value={e.id}>{e.sigla}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Tema</label>
          <select className="input" value={form.tema} onChange={(e) => setForm({ ...form, tema: e.target.value })}>
            {TEMAS.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Sensibilidade</label>
          <select className="input" value={form.sensibilidade} onChange={(e) => setForm({ ...form, sensibilidade: e.target.value })}>
            {SENSIB.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <div className="flex items-end">
          <label className="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.acao_requerida} onChange={(e) => setForm({ ...form, acao_requerida: e.target.checked })} />
            Ação requerida
          </label>
        </div>
        <div className="col-span-2">
          <label className="label">Conteúdo (markdown) *</label>
          <textarea className="input font-mono text-sm" rows={6} required value={form.conteudo} onChange={(e) => setForm({ ...form, conteudo: e.target.value })} />
        </div>
        <div>
          <label className="label">Tipo de fonte</label>
          <input className="input" placeholder="off / coluna / declaração / etc" value={form.fonte_tipo} onChange={(e) => setForm({ ...form, fonte_tipo: e.target.value })} />
        </div>
        <div>
          <label className="label">URL da fonte</label>
          <input className="input" value={form.fonte_url} onChange={(e) => setForm({ ...form, fonte_url: e.target.value })} />
        </div>
        <div className="col-span-2">
          <label className="label">Referência da fonte</label>
          <input className="input" value={form.fonte_referencia} onChange={(e) => setForm({ ...form, fonte_referencia: e.target.value })} />
        </div>
      </div>
      <div className="flex gap-2">
        <button type="submit" className="btn-primary" disabled={mutation.isPending}>
          {mutation.isPending ? "Salvando…" : "Salvar"}
        </button>
        <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
      </div>
      {mutation.isError && (
        <div className="text-sm text-alerta">
          Erro: {(mutation.error as any)?.response?.data?.detail || (mutation.error as any).message}
        </div>
      )}
    </form>
  );
}
