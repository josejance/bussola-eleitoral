import { create } from "zustand";
import { api } from "../lib/api";
import { User } from "../lib/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  init: () => Promise<void>;
  signIn: (email: string, senha: string) => Promise<void>;
  signOut: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  init: async () => {
    const token = localStorage.getItem("auth_token");
    const cachedUser = localStorage.getItem("auth_user");
    if (!token) {
      set({ initialized: true });
      return;
    }
    if (cachedUser) {
      set({ user: JSON.parse(cachedUser) });
    }
    try {
      const { data } = await api.get<User>("/auth/me");
      localStorage.setItem("auth_user", JSON.stringify(data));
      set({ user: data, initialized: true });
    } catch {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("auth_user");
      set({ user: null, initialized: true });
    }
  },

  signIn: async (email, senha) => {
    set({ loading: true });
    try {
      const { data } = await api.post<{ access_token: string; user: User }>(
        "/auth/login",
        { email, senha }
      );
      localStorage.setItem("auth_token", data.access_token);
      localStorage.setItem("auth_user", JSON.stringify(data.user));
      set({ user: data.user });
    } finally {
      set({ loading: false });
    }
  },

  signOut: () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    set({ user: null });
    window.location.href = "/login";
  },
}));
