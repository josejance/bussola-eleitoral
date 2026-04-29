import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./store/auth";
import { AppLayout } from "./components/AppLayout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardNacional } from "./pages/DashboardNacional";
import { EstadosListPage } from "./pages/EstadosListPage";
import { FichaEstadual } from "./pages/FichaEstadual";
import { PesquisasPage } from "./pages/PesquisasPage";
import { PesquisaDetalhePage } from "./pages/PesquisaDetalhePage";
import { ImportarPesquisaPage } from "./pages/ImportarPesquisaPage";
import { OpiniaoPage } from "./pages/OpiniaoPage";
import { OpiniaoDetalhePage } from "./pages/OpiniaoDetalhePage";
import { AgregadorPage } from "./pages/AgregadorPage";
import { ComparadorPage } from "./pages/ComparadorPage";
import { PerfilPessoaPage } from "./pages/PerfilPessoaPage";
import { HistoricoEleitoralPage } from "./pages/HistoricoEleitoralPage";
import { EventosPage } from "./pages/EventosPage";
import { NotasPage } from "./pages/NotasPage";
import { MidiaPage } from "./pages/MidiaPage";
import { BancadasPage } from "./pages/BancadasPage";
import { GovernoPage } from "./pages/GovernoPage";
import { AlertasPage } from "./pages/AlertasPage";
import { SimuladorPage } from "./pages/SimuladorPage";
import { WarRoomPage } from "./pages/WarRoomPage";
import { AdminPage } from "./pages/AdminPage";
import { AdminIngestaoPage } from "./pages/AdminIngestaoPage";
import { AdminSaudePage } from "./pages/AdminSaudePage";
import { AtalhosTeclado } from "./components/AtalhosTeclado";
import { PerfilPage } from "./pages/PerfilPage";
import { TarefasPage } from "./pages/TarefasPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuth((s) => s.user);
  const initialized = useAuth((s) => s.initialized);
  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Carregando…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  const init = useAuth((s) => s.init);

  useEffect(() => {
    init();
  }, [init]);

  return (
    <>
    <AtalhosTeclado />
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/nacional" replace />} />
        <Route path="nacional" element={<DashboardNacional />} />
        <Route path="estados" element={<EstadosListPage />} />
        <Route path="estados/:uf" element={<FichaEstadual />}>
          <Route index element={<Navigate to="visao-geral" replace />} />
          <Route path=":aba" element={<FichaEstadual />} />
        </Route>
        <Route path="pesquisas" element={<PesquisasPage />} />
        <Route path="pesquisas/importar" element={<ImportarPesquisaPage />} />
        <Route path="pesquisas/agregador" element={<AgregadorPage />} />
        <Route path="pesquisas/comparador" element={<ComparadorPage />} />
        <Route path="pesquisas/:id" element={<PesquisaDetalhePage />} />
        <Route path="pessoas/:id" element={<PerfilPessoaPage />} />
        <Route path="historico-eleitoral" element={<HistoricoEleitoralPage />} />
        <Route path="bancadas" element={<BancadasPage />}>
          <Route index element={<Navigate to="camara" replace />} />
          <Route path=":casa" element={<BancadasPage />} />
        </Route>
        <Route path="governo" element={<GovernoPage />}>
          <Route index element={<Navigate to="base-aliada" replace />} />
          <Route path=":tab" element={<GovernoPage />} />
        </Route>
        <Route path="midia" element={<MidiaPage />} />
        <Route path="opiniao" element={<OpiniaoPage />} />
        <Route path="opiniao/:id" element={<OpiniaoDetalhePage />} />
        <Route path="eventos" element={<EventosPage />} />
        <Route path="notas" element={<NotasPage />} />
        <Route path="tarefas" element={<TarefasPage />} />
        <Route path="alertas" element={<AlertasPage />} />
        <Route path="simulador" element={<SimuladorPage />} />
        <Route path="war-room" element={<WarRoomPage />} />
        <Route path="admin" element={<AdminPage />} />
        <Route path="admin/ingestao" element={<AdminIngestaoPage />} />
        <Route path="admin/saude" element={<AdminSaudePage />} />
        <Route path="admin/*" element={<AdminPage />} />
        <Route path="perfil" element={<PerfilPage />} />
        <Route path="*" element={<PlaceholderPage titulo="404" descricao="Página não encontrada." />} />
      </Route>
    </Routes>
    </>
  );
}
