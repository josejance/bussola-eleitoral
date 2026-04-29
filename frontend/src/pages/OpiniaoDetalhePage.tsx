import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { format, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";
import { ArrowLeft, ChevronDown, ChevronRight, FileJson } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useState } from "react";

import { api } from "../lib/api";

interface QuestaoDetalhe {
  id: string;
  numero: number;
  titulo_questao: string | null;
  enunciado: string | null;
  tipo_resposta: string | null;
  dados_gerais: any;
  cruzamentos: any;
}

interface PesquisaDetalhe {
  id: string;
  titulo: string;
  subtitulo: string | null;
  tema: string;
  abrangencia: string;
  estado_sigla: string | null;
  estado_nome: string | null;
  data_inicio_campo: string | null;
  data_fim_campo: string | null;
  amostra: number | null;
  margem_erro: number | null;
  nivel_confianca: number | null;
  metodologia: string | null;
  contratante: string | null;
  instituto: { id: string; nome: string; sigla: string | null };
  publico_alvo: string | null;
  registro_eleitoral: string | null;
  observacao: string | null;
  questoes: QuestaoDetalhe[];
}

const CORES_BARRA = ["#2563EB", "#16A34A", "#DC2626", "#EA580C", "#7C3AED", "#0891B2", "#DB2777", "#65A30D"];

export function OpiniaoDetalhePage() {
  const { id } = useParams();

  const { data: p, isLoading } = useQuery({
    queryKey: ["opiniao", id],
    queryFn: async () => (await api.get<PesquisaDetalhe>(`/opiniao/pesquisas/${id}`)).data,
    enabled: !!id,
  });

  if (isLoading) return <div className="p-6 text-gray-400">Carregando…</div>;
  if (!p) return <div className="p-6 text-gray-500">Pesquisa não encontrada.</div>;

  return (
    <div className="p-6 max-w-6xl">
      <Link to="/opiniao" className="text-xs text-gray-500 hover:text-info inline-flex items-center gap-1 mb-2">
        <ArrowLeft className="h-3 w-3" /> Voltar para Opinião
      </Link>

      <header className="mb-4">
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          <span className="badge bg-blue-50 text-info capitalize">{p.tema.replace(/_/g, " ")}</span>
          <span className="badge bg-gray-100 text-gray-700">{p.instituto.nome}</span>
          {p.estado_sigla && (
            <span className="badge bg-purple-50 text-purple-700 font-mono">{p.estado_sigla}</span>
          )}
          <span className="badge bg-gray-100 text-gray-600 capitalize">{p.abrangencia}</span>
        </div>
        <h1 className="text-2xl font-display font-semibold text-gray-900">{p.titulo}</h1>
        {p.subtitulo && <p className="text-sm text-gray-600 mt-1">{p.subtitulo}</p>}
      </header>

      {/* Especificações técnicas */}
      <div className="card mb-4">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2">
          Especificações Técnicas
        </h2>
        <dl className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          <Item label="Período de campo">
            {p.data_inicio_campo && p.data_fim_campo
              ? `${format(parseISO(p.data_inicio_campo), "dd/MM/yyyy", { locale: ptBR })} a ${format(parseISO(p.data_fim_campo), "dd/MM/yyyy", { locale: ptBR })}`
              : p.data_fim_campo
                ? format(parseISO(p.data_fim_campo), "dd/MM/yyyy", { locale: ptBR })
                : "—"}
          </Item>
          <Item label="Amostra">{p.amostra?.toLocaleString("pt-BR") || "—"}</Item>
          <Item label="Margem de erro">{p.margem_erro ? `±${p.margem_erro}pp` : "—"}</Item>
          <Item label="Nível de confiança">{p.nivel_confianca ? `${p.nivel_confianca}%` : "—"}</Item>
          <Item label="Metodologia" className="capitalize">{p.metodologia || "—"}</Item>
          <Item label="Contratante">{p.contratante || "—"}</Item>
          {p.publico_alvo && (
            <Item label="Público-alvo" cols={3}>
              {p.publico_alvo}
            </Item>
          )}
          {p.registro_eleitoral && (
            <Item label="Registro Eleitoral">
              <span className="font-mono">{p.registro_eleitoral}</span>
            </Item>
          )}
        </dl>
      </div>

      {/* Questões */}
      <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
        {p.questoes.length} Questões
      </h2>

      <div className="space-y-3">
        {p.questoes.map((q) => (
          <CardQuestao key={q.id} questao={q} />
        ))}
      </div>
    </div>
  );
}

function Item({ label, children, className, cols }: { label: string; children: React.ReactNode; className?: string; cols?: number }) {
  return (
    <div className={cols ? `col-span-${cols}` : ""}>
      <dt className="text-xs text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className={`font-medium text-gray-900 ${className || ""}`}>{children}</dd>
    </div>
  );
}

function CardQuestao({ questao }: { questao: QuestaoDetalhe }) {
  const [expandido, setExpandido] = useState(false);
  const [cruzExpandido, setCruzExpandido] = useState<string | null>(null);

  const dados = normalizarDados(questao.dados_gerais);
  const titulo = questao.titulo_questao || `Questão ${questao.numero}`;

  return (
    <div className="card">
      <button
        onClick={() => setExpandido(!expandido)}
        className="w-full flex items-start gap-2 text-left"
      >
        <span className="text-xs text-gray-400 font-mono mt-1">#{questao.numero}</span>
        <div className="flex-1 min-w-0">
          <h3 className="font-display font-semibold text-gray-900">{titulo}</h3>
          {questao.enunciado && questao.enunciado !== titulo && (
            <p className="text-sm text-gray-600 mt-0.5">{questao.enunciado}</p>
          )}
        </div>
        {expandido ? <ChevronDown className="h-4 w-4 text-gray-400 mt-1" /> : <ChevronRight className="h-4 w-4 text-gray-400 mt-1" />}
      </button>

      {expandido && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          {dados.length > 0 ? (
            <>
              <GraficoDados dados={dados} />
              <TabelaDados dados={dados} />
            </>
          ) : (
            <div className="text-xs text-gray-400 italic">Sem dados gerais disponíveis nesta questão.</div>
          )}

          {questao.cruzamentos && Object.keys(questao.cruzamentos).length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">
                Cruzamentos ({Object.keys(questao.cruzamentos).length})
              </div>
              <div className="space-y-1">
                {Object.keys(questao.cruzamentos).map((nomeCruz) => (
                  <button
                    key={nomeCruz}
                    onClick={() => setCruzExpandido(cruzExpandido === nomeCruz ? null : nomeCruz)}
                    className="w-full text-left text-xs text-info hover:underline px-2 py-1 rounded hover:bg-blue-50 flex items-center justify-between"
                  >
                    <span>{nomeCruz}</span>
                    <span className="text-gray-400">
                      {cruzExpandido === nomeCruz ? "esconder" : "ver"}
                    </span>
                  </button>
                ))}
              </div>
              {cruzExpandido && (
                <div className="mt-2 bg-gray-50 rounded p-2 text-xs">
                  <pre className="whitespace-pre-wrap break-words font-mono text-[10px] max-h-60 overflow-y-auto">
                    {JSON.stringify(questao.cruzamentos[cruzExpandido], null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function normalizarDados(dadosGerais: any): { opcao: string; percentual: number }[] {
  if (!dadosGerais) return [];
  if (!Array.isArray(dadosGerais)) {
    // Pode ser objeto {opcao1: pct, opcao2: pct}
    if (typeof dadosGerais === "object") {
      return Object.entries(dadosGerais)
        .filter(([_, v]) => typeof v === "number" || (typeof v === "string" && !isNaN(parseFloat(v as string))))
        .map(([k, v]) => ({ opcao: k, percentual: typeof v === "number" ? v : parseFloat(v as string) }));
    }
    return [];
  }
  return dadosGerais
    .filter((d: any) => d && typeof d === "object")
    .map((d: any) => ({
      opcao: d.opcao || d.alternativa || d.resposta || d.categoria || "—",
      percentual: parseFloat(d.percentual || d.pct || d.valor || 0),
    }))
    .filter((d: any) => !isNaN(d.percentual) && d.percentual > 0);
}

function GraficoDados({ dados }: { dados: { opcao: string; percentual: number }[] }) {
  if (dados.length === 0 || dados.length > 12) return null;
  return (
    <div className="h-48 mb-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={dados} layout="vertical" margin={{ left: 100, right: 30 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fontSize: 10, fill: "#6B7280" }}
            tickFormatter={(v) => `${v}%`}
          />
          <YAxis
            type="category"
            dataKey="opcao"
            tick={{ fontSize: 10, fill: "#374151" }}
            width={150}
          />
          <Tooltip formatter={(v: any) => [`${v}%`, ""]} />
          <Bar dataKey="percentual" radius={[0, 4, 4, 0]}>
            {dados.map((_, i) => (
              <Cell key={i} fill={CORES_BARRA[i % CORES_BARRA.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function TabelaDados({ dados }: { dados: { opcao: string; percentual: number }[] }) {
  if (dados.length === 0) return null;
  return (
    <table className="w-full text-xs">
      <tbody>
        {dados.map((d, i) => (
          <tr key={i} className="border-b border-gray-100 last:border-0">
            <td className="py-1.5 text-gray-700">{d.opcao}</td>
            <td className="py-1.5 text-right font-mono font-bold">{d.percentual}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
