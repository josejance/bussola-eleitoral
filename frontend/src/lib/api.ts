import axios, { AxiosInstance } from "axios";

const baseURL = (import.meta.env.VITE_API_BASE_URL ?? "") + "/api/v1";

export const api: AxiosInstance = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("auth_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      // Token expirado / inválido — limpa e redireciona
      const isLoginRequest = err.config?.url?.includes("/auth/login");
      if (!isLoginRequest) {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
        if (window.location.pathname !== "/login") {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(err);
  }
);
