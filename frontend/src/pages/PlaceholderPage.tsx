import { Construction } from "lucide-react";

export function PlaceholderPage({ titulo, descricao, fase }: { titulo: string; descricao: string; fase?: string }) {
  return (
    <div className="p-6">
      <div className="card max-w-3xl mx-auto mt-8 text-center !p-8">
        <Construction className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <h1 className="text-2xl font-display font-semibold text-gray-900 mb-2">{titulo}</h1>
        <p className="text-gray-600 max-w-2xl mx-auto">{descricao}</p>
        {fase && (
          <div className="inline-block mt-4 badge bg-blue-50 text-info">
            Implementação prevista — {fase}
          </div>
        )}
      </div>
    </div>
  );
}
