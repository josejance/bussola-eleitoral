import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Keyboard, X } from "lucide-react";

const ATALHOS = [
  { tecla: "g + n", acao: "Visão Nacional", path: "/nacional" },
  { tecla: "g + e", acao: "Estados", path: "/estados" },
  { tecla: "g + p", acao: "Pesquisas", path: "/pesquisas" },
  { tecla: "g + a", acao: "Agregador", path: "/pesquisas/agregador" },
  { tecla: "g + o", acao: "Opinião", path: "/opiniao" },
  { tecla: "g + b", acao: "Bancadas", path: "/bancadas" },
  { tecla: "g + g", acao: "Governo", path: "/governo" },
  { tecla: "g + m", acao: "Mídia", path: "/midia" },
  { tecla: "g + s", acao: "Simulador", path: "/simulador" },
  { tecla: "g + w", acao: "War Room", path: "/war-room" },
  { tecla: "g + h", acao: "Histórico Eleitoral", path: "/historico-eleitoral" },
  { tecla: "?", acao: "Mostrar atalhos" },
  { tecla: "Esc", acao: "Fechar modal/drawer" },
];

export function AtalhosTeclado() {
  const navigate = useNavigate();
  const [showHelp, setShowHelp] = useState(false);

  useEffect(() => {
    let waiting_g = false;
    let timer: any = null;

    function handler(e: KeyboardEvent) {
      // Não interfere em inputs
      const target = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) || target.isContentEditable) return;

      if (e.key === "?" && e.shiftKey) {
        e.preventDefault();
        setShowHelp(true);
        return;
      }

      if (e.key === "Escape") {
        setShowHelp(false);
        return;
      }

      if (e.key === "g" && !waiting_g) {
        waiting_g = true;
        timer = setTimeout(() => { waiting_g = false; }, 1500);
        return;
      }

      if (waiting_g) {
        const map: Record<string, string> = {
          n: "/nacional",
          e: "/estados",
          p: "/pesquisas",
          a: "/pesquisas/agregador",
          o: "/opiniao",
          b: "/bancadas",
          g: "/governo",
          m: "/midia",
          s: "/simulador",
          w: "/war-room",
          h: "/historico-eleitoral",
        };
        const path = map[e.key.toLowerCase()];
        if (path) {
          e.preventDefault();
          navigate(path);
        }
        waiting_g = false;
        if (timer) clearTimeout(timer);
      }
    }

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [navigate]);

  if (!showHelp) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center"
      onClick={() => setShowHelp(false)}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-semibold text-lg flex items-center gap-2">
            <Keyboard className="h-5 w-5 text-info" /> Atalhos de teclado
          </h2>
          <button onClick={() => setShowHelp(false)} className="text-gray-400 hover:text-gray-700">
            <X className="h-4 w-4" />
          </button>
        </div>
        <table className="w-full text-sm">
          <tbody>
            {ATALHOS.map((a) => (
              <tr key={a.tecla} className="border-b border-gray-100 last:border-0">
                <td className="py-2">
                  <kbd className="font-mono text-xs px-2 py-0.5 bg-gray-100 rounded border border-gray-300">
                    {a.tecla}
                  </kbd>
                </td>
                <td className="py-2 text-gray-700">{a.acao}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-gray-500 mt-3">
          Pressione <kbd className="font-mono px-1 bg-gray-100 rounded">?</kbd> a qualquer momento para abrir.
        </p>
      </div>
    </div>
  );
}
