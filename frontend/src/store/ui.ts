import { create } from "zustand";

interface UIState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
  selectedEstadoSigla: string | null;
  selectEstado: (sigla: string | null) => void;
  mapLayer: "status" | "governador" | "senado";
  setMapLayer: (layer: "status" | "governador" | "senado") => void;
  darkMode: boolean;
  toggleDarkMode: () => void;
}

const darkModeInicial = typeof window !== "undefined" && localStorage.getItem("darkMode") === "1";
if (typeof window !== "undefined" && darkModeInicial) {
  document.documentElement.classList.add("dark");
}

export const useUI = create<UIState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  mobileMenuOpen: false,
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
  selectedEstadoSigla: null,
  selectEstado: (sigla) => set({ selectedEstadoSigla: sigla }),
  mapLayer: "status",
  setMapLayer: (layer) => set({ mapLayer: layer }),
  darkMode: darkModeInicial,
  toggleDarkMode: () =>
    set((s) => {
      const novo = !s.darkMode;
      if (typeof window !== "undefined") {
        localStorage.setItem("darkMode", novo ? "1" : "0");
        document.documentElement.classList.toggle("dark", novo);
      }
      return { darkMode: novo };
    }),
}));
