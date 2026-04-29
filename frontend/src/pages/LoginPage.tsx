import { FormEvent, useState } from "react";
import { Navigate } from "react-router-dom";
import { Compass } from "lucide-react";

import { useAuth } from "../store/auth";

export function LoginPage() {
  const user = useAuth((s) => s.user);
  const signIn = useAuth((s) => s.signIn);
  const loading = useAuth((s) => s.loading);

  const [email, setEmail] = useState("admin@bussola.app");
  const [senha, setSenha] = useState("admin123");
  const [erro, setErro] = useState<string | null>(null);

  if (user) return <Navigate to="/nacional" replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    try {
      await signIn(email, senha);
    } catch (err: any) {
      setErro(err?.response?.data?.detail || "Falha no login");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-pt/10 mb-4">
            <Compass className="text-pt h-8 w-8" />
          </div>
          <h1 className="text-2xl font-display font-semibold text-gray-900">
            Bússola Eleitoral
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Plataforma de monitoramento eleitoral
          </p>
        </div>

        <div className="card">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
              />
            </div>

            <div>
              <label className="label" htmlFor="senha">
                Senha
              </label>
              <input
                id="senha"
                type="password"
                required
                className="input"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                autoComplete="current-password"
              />
            </div>

            {erro && (
              <div className="text-sm text-alerta bg-red-50 border border-red-200 rounded p-2">
                {erro}
              </div>
            )}

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? "Entrando…" : "Entrar"}
            </button>
          </form>

          <div className="mt-6 pt-4 border-t border-gray-100 text-xs text-gray-500">
            <p className="font-medium text-gray-700 mb-1">Credenciais de demo:</p>
            <p>
              <code className="font-mono">admin@bussola.app</code> /{" "}
              <code className="font-mono">admin123</code>
            </p>
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          v0.1.0 — instância local de desenvolvimento
        </p>
      </div>
    </div>
  );
}
