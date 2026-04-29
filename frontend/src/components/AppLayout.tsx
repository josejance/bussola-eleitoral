import { useState } from "react";
import { Outlet, NavLink, useLocation, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";

import { api } from "../lib/api";
import {
  LayoutDashboard,
  Map,
  BarChart3,
  Users2,
  Shield,
  Newspaper,
  Activity,
  FileText,
  CheckSquare,
  Bell,
  FlaskConical,
  Radar,
  Settings,
  LogOut,
  Compass,
  ChevronLeft,
  ChevronRight,
  MessageSquare,
  Moon,
  Sun,
  Keyboard,
} from "lucide-react";
import clsx from "clsx";

import { useAuth } from "../store/auth";
import { useUI } from "../store/ui";

const navItems = [
  { to: "/nacional", label: "Visão Nacional", icon: LayoutDashboard },
  { to: "/estados", label: "Estados", icon: Map },
  { to: "/pesquisas", label: "Pesquisas", icon: BarChart3 },
  { to: "/pesquisas/agregador", label: "↳ Agregador", icon: BarChart3 },
  { to: "/opiniao", label: "Opinião", icon: MessageSquare },
  { to: "/bancadas", label: "Bancadas", icon: Users2 },
  { to: "/historico-eleitoral", label: "Histórico", icon: BarChart3 },
  { to: "/governo", label: "Governo", icon: Shield },
  { to: "/midia", label: "Mídia", icon: Newspaper },
  { to: "/eventos", label: "Eventos", icon: Activity },
  { to: "/notas", label: "Notas", icon: FileText },
  { to: "/tarefas", label: "Tarefas", icon: CheckSquare },
  { to: "/alertas", label: "Alertas", icon: Bell },
  { to: "/simulador", label: "Simulador", icon: FlaskConical, papelMin: ["admin", "editor_nacional", "editor_estadual"] },
  { to: "/war-room", label: "War Room", icon: Radar, papelMin: ["admin", "editor_nacional"] },
];

export function AppLayout() {
  const user = useAuth((s) => s.user);
  const signOut = useAuth((s) => s.signOut);
  const { sidebarCollapsed, toggleSidebar } = useUI();
  const location = useLocation();

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside
        className={clsx(
          "bg-white border-r border-gray-200 flex flex-col transition-all duration-200",
          sidebarCollapsed ? "w-16" : "w-60"
        )}
      >
        <div className="h-14 flex items-center px-4 border-b border-gray-200">
          <Compass className="text-pt h-6 w-6 flex-shrink-0" />
          {!sidebarCollapsed && (
            <span className="ml-2 font-display font-semibold text-gray-900">
              Bússola Eleitoral
            </span>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto py-3">
          {navItems.map((item) => {
            if (item.papelMin && user && !item.papelMin.includes(user.papel)) return null;
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-3 px-4 py-2 text-sm transition",
                    isActive
                      ? "bg-blue-50 text-info border-r-2 border-info font-medium"
                      : "text-gray-700 hover:bg-gray-50"
                  )
                }
                title={sidebarCollapsed ? item.label : undefined}
              >
                <Icon className="h-5 w-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>{item.label}</span>}
              </NavLink>
            );
          })}

          {user?.papel === "admin" && (
            <>
              <div className="my-3 border-t border-gray-200" />
              <NavLink
                to="/admin"
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-3 px-4 py-2 text-sm transition",
                    isActive
                      ? "bg-blue-50 text-info border-r-2 border-info font-medium"
                      : "text-gray-700 hover:bg-gray-50"
                  )
                }
              >
                <Settings className="h-5 w-5 flex-shrink-0" />
                {!sidebarCollapsed && <span>Admin</span>}
              </NavLink>
            </>
          )}
        </nav>

        <div className="border-t border-gray-200 p-2">
          <button
            onClick={toggleSidebar}
            className="w-full flex items-center justify-center gap-2 py-2 text-gray-500 hover:bg-gray-50 rounded text-xs"
          >
            {sidebarCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            {!sidebarCollapsed && <span>Recolher</span>}
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
          <div className="text-sm text-gray-600">
            <span className="font-mono text-xs text-gray-400">{location.pathname}</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => useUI.getState().toggleDarkMode()}
              className="p-2 hover:bg-gray-100 rounded-md text-gray-600"
              title="Alternar tema (claro/escuro)"
            >
              {useUI((s) => s.darkMode) ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <button
              onClick={() => {
                const e = new KeyboardEvent("keydown", { key: "?", shiftKey: true });
                window.dispatchEvent(e);
              }}
              className="p-2 hover:bg-gray-100 rounded-md text-gray-600"
              title="Atalhos de teclado (?)"
            >
              <Keyboard className="h-4 w-4" />
            </button>
            <SinoNotificacoes />
            <span className="text-xs text-gray-500">
              v0.3.0 · localhost
            </span>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-info text-white flex items-center justify-center text-xs font-semibold">
                {user?.nome_exibicao?.[0] || user?.nome_completo?.[0] || "U"}
              </div>
              <div className="text-sm">
                <div className="font-medium text-gray-900 leading-tight">
                  {user?.nome_exibicao || user?.nome_completo}
                </div>
                <div className="text-xs text-gray-500 leading-tight">{user?.papel}</div>
              </div>
              <button
                onClick={signOut}
                className="ml-2 p-2 text-gray-400 hover:text-alerta hover:bg-gray-50 rounded"
                title="Sair"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

interface Notificacao {
  id: string;
  titulo: string;
  mensagem: string | null;
  entidade_tipo: string | null;
  entidade_id: string | null;
  prioridade: string;
  lida: boolean;
  created_at: string;
}

function SinoNotificacoes() {
  const [aberto, setAberto] = useState(false);
  const queryClient = useQueryClient();

  const { data: contagem } = useQuery({
    queryKey: ["notificacoes-contagem"],
    queryFn: async () => (await api.get<{ nao_lidas: number }>("/notificacoes/contagem")).data,
    refetchInterval: 30_000,
  });

  const { data: notifs = [] } = useQuery({
    queryKey: ["notificacoes-recent"],
    queryFn: async () => (await api.get<Notificacao[]>("/notificacoes?limit=10")).data,
    enabled: aberto,
  });

  const marcarLidaMutation = useMutation({
    mutationFn: async (id: string) => (await api.post(`/notificacoes/${id}/marcar-lida`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notificacoes-contagem"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-recent"] });
    },
  });

  const marcarTodasMutation = useMutation({
    mutationFn: async () => (await api.post("/notificacoes/marcar-todas-lidas")).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notificacoes-contagem"] });
      queryClient.invalidateQueries({ queryKey: ["notificacoes-recent"] });
    },
  });

  const naoLidas = contagem?.nao_lidas || 0;

  return (
    <div className="relative">
      <button
        onClick={() => setAberto(!aberto)}
        className="relative p-2 hover:bg-gray-100 rounded-md"
        title="Notificações"
      >
        <Bell className="h-5 w-5 text-gray-600" />
        {naoLidas > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center text-[10px] font-bold w-4 h-4 bg-alerta text-white rounded-full">
            {naoLidas > 9 ? "9+" : naoLidas}
          </span>
        )}
      </button>
      {aberto && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setAberto(false)}
          />
          <div className="absolute top-full right-0 mt-1 w-96 max-h-[500px] overflow-y-auto bg-white rounded-lg shadow-xl border border-gray-200 z-50">
            <div className="px-3 py-2 border-b border-gray-200 flex items-center justify-between">
              <span className="font-semibold text-sm">Notificações</span>
              {naoLidas > 0 && (
                <button
                  onClick={() => marcarTodasMutation.mutate()}
                  className="text-xs text-info hover:underline"
                >
                  marcar todas como lidas
                </button>
              )}
            </div>
            {notifs.length === 0 ? (
              <div className="p-6 text-center text-sm text-gray-500">Nenhuma notificação</div>
            ) : (
              notifs.map((n) => (
                <div
                  key={n.id}
                  className={`px-3 py-2 border-b border-gray-100 last:border-0 hover:bg-gray-50 ${
                    !n.lida ? "bg-blue-50" : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm">{n.titulo}</div>
                      {n.mensagem && (
                        <div className="text-xs text-gray-600 line-clamp-2">{n.mensagem}</div>
                      )}
                      <div className="text-[10px] text-gray-400 mt-0.5">
                        {formatDistanceToNow(new Date(n.created_at), { locale: ptBR, addSuffix: true })}
                      </div>
                    </div>
                    {!n.lida && (
                      <button
                        onClick={() => marcarLidaMutation.mutate(n.id)}
                        className="text-[10px] text-info hover:underline flex-shrink-0"
                      >
                        marcar
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
            <div className="px-3 py-2 border-t border-gray-200">
              <Link to="/alertas" onClick={() => setAberto(false)} className="text-xs text-info hover:underline">
                Configurar alertas →
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
