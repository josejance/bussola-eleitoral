import { FormEvent, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { FileJson, Plus } from "lucide-react";

import { api } from "../lib/api";
import { Estado, Pesquisa } from "../lib/types";
import { useAuth } from "../store/auth";

interface Instituto {
  id: string;
  nome: string;
  sigla: string;
  confiabilidade_score: number;
}
interface Eleicao {
  id: string;
  ano: number;
  turno: number;
  tipo: string;
}

export function PesquisasPage() {
  const user = useAuth((s) => s.user);
  const podeAdicionar = user && ["admin", "editor_nacional", "editor_estadual"].includes(user.papel);

  const [showForm, setShowForm] = useState(false);
  const [estadoFilter, setEstadoFilter] = useState<string>("");

  const { data: pesquisas = [], isLoading } = useQuery({
    queryKey: ["pesquisas", "list", estadoFilter],
    queryFn: async () =>
      (await api.get<Pesquisa[]>("/pesquisas", { params: { estado_id: estadoFilter || undefined, limit: 100 } })).data,
  });

  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });
  const estadoNome = (id: string | null | undefined) => estados.find((e) => e.id === id)?.sigla || "—";

  return (
    <div className="p-6">
      <header className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-display font-semibold text-gray-900">Pesquisas Eleitorais</h1>
          <p className="text-sm text-gray-500 mt-1">
            {pesquisas.length} pesquisa{pesquisas.length !== 1 ? "s" : ""} · Origem: TSE PesqEle, Poder360, ou inserção manual
          </p>
        </div>
        {podeAdicionar && (
          <div className="flex gap-2">
            <Link to="/pesquisas/importar" className="btn-secondary">
              <FileJson className="h-4 w-4" /> Importar JSON
            </Link>
            <button onClick={() => setShowForm(true)} className="btn-primary">
              <Plus className="h-4 w-4" /> Nova pesquisa
            </button>
          </div>
        )}
      </header>

      <div className="flex gap-3 mb-4">
        <select
          className="input max-w-xs"
          value={estadoFilter}
          onChange={(e) => setEstadoFilter(e.target.value)}
        >
          <option value="">Todos os estados</option>
          {estados.map((e) => (
            <option key={e.id} value={e.id}>{e.sigla} - {e.nome}</option>
          ))}
        </select>
      </div>

      {showForm && (
        <NovaPesquisaForm
          estados={estados}
          onClose={() => setShowForm(false)}
        />
      )}

      <div className="card !p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-2 text-left">Estado</th>
              <th className="px-4 py-2 text-left">Contratante</th>
              <th className="px-4 py-2 text-left">Data campo</th>
              <th className="px-4 py-2 text-right">Amostra</th>
              <th className="px-4 py-2 text-right">Margem</th>
              <th className="px-4 py-2 text-left">Cenário</th>
              <th className="px-4 py-2 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Carregando…</td></tr>
            ) : pesquisas.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Nenhuma pesquisa cadastrada.</td></tr>
            ) : (
              pesquisas.map((p) => (
                <tr key={p.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-xs">{estadoNome(p.estado_id)}</td>
                  <td className="px-4 py-2">{p.contratante || "—"}</td>
                  <td className="px-4 py-2 text-xs">
                    {p.data_fim_campo && format(new Date(p.data_fim_campo), "dd/MM/yy", { locale: ptBR })}
                  </td>
                  <td className="px-4 py-2 text-right font-mono">{p.amostra ?? "—"}</td>
                  <td className="px-4 py-2 text-right font-mono">±{p.margem_erro ?? "—"}</td>
                  <td className="px-4 py-2 capitalize">{p.tipo_cenario}</td>
                  <td className="px-4 py-2">
                    <span className="badge bg-blue-50 text-info">{p.status_revisao}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NovaPesquisaForm({ estados, onClose }: { estados: Estado[]; onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: institutos = [] } = useQuery({
    queryKey: ["institutos"],
    queryFn: async () => {
      // Aproveita rota futura; por enquanto, busca via SQL direto não é exposto. Mock de 1 endpoint inline:
      // Vou usar fontes_rss do midia como exemplo? Não. Deixo manual.
      return [
        { id: "manual", nome: "Selecione...", sigla: "", confiabilidade_score: 0 },
      ] as Instituto[];
    },
  });

  const [form, setForm] = useState({
    instituto_id: "",
    eleicao_id: "",
    estado_id: "",
    contratante: "",
    data_inicio_campo: "",
    data_fim_campo: "",
    data_divulgacao: "",
    amostra: 800,
    margem_erro: 3.5,
    nivel_confianca: 95,
    metodologia: "presencial",
    tipo_cenario: "estimulado",
    turno_referencia: 1,
  });

  const mutation = useMutation({
    mutationFn: async (payload: any) => (await api.post("/pesquisas", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pesquisas"] });
      onClose();
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const payload: any = { ...form };
    Object.keys(payload).forEach((k) => {
      if (payload[k] === "" || payload[k] === null) delete payload[k];
    });
    mutation.mutate(payload);
  }

  return (
    <div className="card mb-4">
      <h2 className="font-display font-semibold mb-3">Nova pesquisa (entrada manual)</h2>
      <p className="text-xs text-gray-500 mb-4">
        Versão simplificada para demonstração. O wizard completo (Fase 3 — Prompt 6) inclui upload de PDF e extração via Claude.
      </p>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <div>
          <label className="label">Estado</label>
          <select className="input" value={form.estado_id} onChange={(e) => setForm({ ...form, estado_id: e.target.value })}>
            <option value="">Nacional</option>
            {estados.map((e) => (
              <option key={e.id} value={e.id}>{e.sigla}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Eleição</label>
          <input className="input" placeholder="ID da eleição" value={form.eleicao_id} onChange={(e) => setForm({ ...form, eleicao_id: e.target.value })} />
        </div>
        <div>
          <label className="label">Instituto</label>
          <input className="input" placeholder="ID do instituto" value={form.instituto_id} onChange={(e) => setForm({ ...form, instituto_id: e.target.value })} />
        </div>
        <div>
          <label className="label">Contratante</label>
          <input className="input" value={form.contratante} onChange={(e) => setForm({ ...form, contratante: e.target.value })} />
        </div>
        <div>
          <label className="label">Início campo</label>
          <input type="date" className="input" value={form.data_inicio_campo} onChange={(e) => setForm({ ...form, data_inicio_campo: e.target.value })} />
        </div>
        <div>
          <label className="label">Fim campo</label>
          <input type="date" className="input" value={form.data_fim_campo} onChange={(e) => setForm({ ...form, data_fim_campo: e.target.value })} />
        </div>
        <div>
          <label className="label">Amostra</label>
          <input type="number" className="input" value={form.amostra} onChange={(e) => setForm({ ...form, amostra: +e.target.value })} />
        </div>
        <div>
          <label className="label">Margem ±</label>
          <input type="number" step={0.1} className="input" value={form.margem_erro} onChange={(e) => setForm({ ...form, margem_erro: +e.target.value })} />
        </div>
        <div>
          <label className="label">Metodologia</label>
          <select className="input" value={form.metodologia} onChange={(e) => setForm({ ...form, metodologia: e.target.value })}>
            <option value="presencial">Presencial</option>
            <option value="telefonica">Telefônica</option>
            <option value="online">Online</option>
            <option value="mista">Mista</option>
          </select>
        </div>
        <div className="col-span-full flex gap-2 mt-2">
          <button type="submit" className="btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Salvando…" : "Salvar pesquisa"}
          </button>
          <button type="button" className="btn-secondary" onClick={onClose}>Cancelar</button>
        </div>
        {mutation.isError && (
          <div className="col-span-full text-sm text-alerta">
            Erro: {(mutation.error as any)?.response?.data?.detail || (mutation.error as any).message}
          </div>
        )}
      </form>
    </div>
  );
}
