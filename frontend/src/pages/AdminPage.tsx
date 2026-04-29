import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ArrowRight, Database, Newspaper, Settings2, ShieldCheck, Activity, Code2 } from "lucide-react";

import { api } from "../lib/api";
import { Estado } from "../lib/types";

interface IngestaoStatus {
  total_fontes: number;
  fontes_ativas: number;
  total_materias: number;
  materias_aproveitadas: number;
  capturadas_ultimas_24h: number;
  fontes_com_falha_ultima: number;
  ultimo_polling: string | null;
}

export function AdminPage() {
  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });

  const { data: ingestao } = useQuery({
    queryKey: ["admin", "ingestao-status"],
    queryFn: async () => (await api.get<IngestaoStatus>("/admin/ingestao/rss/status")).data,
  });

  return (
    <div className="p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-gray-900">Administração</h1>
        <p className="text-sm text-gray-500 mt-1">Gestão do sistema, ingestões e configurações</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Link to="/admin/ingestao" className="card hover:shadow-md hover:border-info transition group">
          <div className="flex items-start justify-between mb-2">
            <Newspaper className="h-6 w-6 text-info" />
            <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-info" />
          </div>
          <h3 className="font-display font-semibold mb-1">Ingestão de mídia</h3>
          {ingestao ? (
            <div className="text-sm text-gray-600 space-y-0.5">
              <div>{ingestao.fontes_ativas} fontes ativas</div>
              <div>{ingestao.total_materias.toLocaleString("pt-BR")} matérias capturadas</div>
              <div>
                <span className="text-sucesso font-medium">{ingestao.capturadas_ultimas_24h}</span> nas últimas 24h
              </div>
              {ingestao.fontes_com_falha_ultima > 0 && (
                <div className="text-alerta">{ingestao.fontes_com_falha_ultima} fontes em falha</div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500">Configure e monitore polling de RSS</p>
          )}
        </Link>

        <div className="card">
          <Database className="h-6 w-6 text-gray-700 mb-2" />
          <h3 className="font-display font-semibold mb-1">Banco de dados</h3>
          <ul className="text-sm space-y-0.5 text-gray-700">
            <li>{estados.length} estados carregados</li>
            <li>SQLite local: <code className="text-xs">backend/bussola.db</code></li>
          </ul>
        </div>

        <a
          href={`${import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000"}/docs`}
          target="_blank"
          rel="noreferrer"
          className="card hover:shadow-md hover:border-info transition group"
        >
          <div className="flex items-start justify-between mb-2">
            <Code2 className="h-6 w-6 text-info" />
            <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-info" />
          </div>
          <h3 className="font-display font-semibold mb-1">API REST</h3>
          <p className="text-sm text-gray-600">Documentação interativa Swagger em <code>/docs</code></p>
        </a>

        <div className="card opacity-60">
          <ShieldCheck className="h-6 w-6 text-gray-400 mb-2" />
          <h3 className="font-display font-semibold mb-1">Usuários</h3>
          <p className="text-sm text-gray-500">CRUD de usuários e papéis. Por ora, apenas o admin via seed.</p>
        </div>

        <div className="card opacity-60">
          <Activity className="h-6 w-6 text-gray-400 mb-2" />
          <h3 className="font-display font-semibold mb-1">Auditoria</h3>
          <p className="text-sm text-gray-500">
            Logs de mudanças críticas. Tabela <code>audit_log</code> pronta no schema.
          </p>
        </div>

        <div className="card opacity-60">
          <Settings2 className="h-6 w-6 text-gray-400 mb-2" />
          <h3 className="font-display font-semibold mb-1">Saúde do sistema</h3>
          <p className="text-sm text-gray-500">Latência, custos de IA, erros recentes — Prompt 18.</p>
        </div>
      </div>
    </div>
  );
}
