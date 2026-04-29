import { useAuth } from "../store/auth";

export function PerfilPage() {
  const user = useAuth((s) => s.user);
  const signOut = useAuth((s) => s.signOut);

  if (!user) return null;

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-display font-semibold mb-4">Meu perfil</h1>
      <div className="card space-y-3 text-sm">
        <Field label="Nome" valor={user.nome_completo} />
        <Field label="Email" valor={user.email} />
        <Field label="Papel" valor={user.papel} />
        <Field label="ID" valor={user.id} mono />
      </div>
      <button onClick={signOut} className="btn-danger mt-4">Sair</button>
    </div>
  );
}

function Field({ label, valor, mono }: { label: string; valor: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className={mono ? "font-mono text-xs" : "font-medium"}>{valor}</span>
    </div>
  );
}
