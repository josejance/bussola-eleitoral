import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, NavLink, useParams } from "react-router-dom";
import clsx from "clsx";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { api } from "../lib/api";
import { Estado, Partido } from "../lib/types";

interface Candidatura {
  id: string;
  cargo: string;
  status_registro: string;
  eh_titular: boolean;
  observacao: string | null;
  pessoa: { id: string; nome_completo: string; nome_urna: string; foto_url: string | null } | null;
  partido: { id: string; sigla: string; nome_completo: string; cor_hex: string | null; espectro: string | null } | null;
  estado_id: string | null;
}

const BASE_LULA_PARTIDOS = ["PT", "PCdoB", "PV", "PSB", "PSOL", "REDE", "PDT", "MDB", "UNIAO", "SOLIDARIEDADE", "AVANTE"];

export function BancadasPage() {
  const { casa = "camara" } = useParams();

  const { data: candidaturas = [] } = useQuery({
    queryKey: ["candidaturas", "all"],
    queryFn: async () => (await api.get<Candidatura[]>("/candidaturas")).data,
  });

  const { data: estados = [] } = useQuery({
    queryKey: ["estados"],
    queryFn: async () => (await api.get<Estado[]>("/estados")).data,
  });

  const { data: partidos = [] } = useQuery({
    queryKey: ["partidos"],
    queryFn: async () => (await api.get<Partido[]>("/partidos")).data,
  });

  // Filtra candidaturas pela casa
  const filtered = useMemo(() => {
    const cargo = casa === "senado" ? "senador" : "governador";
    return candidaturas.filter((c) => c.cargo === cargo);
  }, [candidaturas, casa]);

  // Agrupa por partido
  const porPartido = useMemo(() => {
    const map = new Map<string, { sigla: string; cor: string; total: number; candidatos: Candidatura[] }>();
    for (const c of filtered) {
      const sigla = c.partido?.sigla || "?";
      const cor = c.partido?.cor_hex || "#6B7280";
      if (!map.has(sigla)) {
        map.set(sigla, { sigla, cor, total: 0, candidatos: [] });
      }
      const e = map.get(sigla)!;
      e.total += 1;
      e.candidatos.push(c);
    }
    return Array.from(map.values()).sort((a, b) => b.total - a.total);
  }, [filtered]);

  // Indicadores
  const totalAliados = porPartido
    .filter((p) => BASE_LULA_PARTIDOS.includes(p.sigla))
    .reduce((s, p) => s + p.total, 0);

  // Por estado
  const porEstado = useMemo(() => {
    const map = new Map<string, Candidatura[]>();
    for (const c of filtered) {
      if (!c.estado_id) continue;
      if (!map.has(c.estado_id)) map.set(c.estado_id, []);
      map.get(c.estado_id)!.push(c);
    }
    return map;
  }, [filtered]);

  return (
    <div className="p-6 max-w-7xl">
      <header className="mb-4">
        <h1 className="text-2xl font-display font-semibold text-gray-900">Bancadas — Eleição 2026</h1>
        <p className="text-sm text-gray-500 mt-1">
          Pré-candidaturas cadastradas (GTE 17/04/2026) e projeção de bancada baseada em pesquisas e histórico.
        </p>
      </header>

      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {[
          { key: "camara", label: `Câmara dos Deputados (513)` },
          { key: "senado", label: `Senado Federal (81 — 54 vagas em 2026)` },
        ].map((tab) => (
          <NavLink
            key={tab.key}
            to={`/bancadas/${tab.key}`}
            className={({ isActive }) =>
              clsx(
                "px-4 py-2 text-sm font-medium border-b-2 transition",
                isActive ? "border-info text-info" : "border-transparent text-gray-600 hover:text-gray-900"
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      {/* Indicadores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
        <div className="card !p-3">
          <div className="text-xs text-gray-500 uppercase">Pré-candidatos cadastrados</div>
          <div className="text-3xl font-bold font-mono text-info">{filtered.length}</div>
          <div className="text-xs text-gray-500">cargo {casa === "senado" ? "senador" : "governador"}</div>
        </div>
        <div className="card !p-3">
          <div className="text-xs text-gray-500 uppercase">Partidos representados</div>
          <div className="text-3xl font-bold font-mono text-info">{porPartido.length}</div>
        </div>
        <div className="card !p-3">
          <div className="text-xs text-gray-500 uppercase">Da base aliada</div>
          <div className="text-3xl font-bold font-mono text-sucesso">{totalAliados}</div>
          <div className="text-xs text-gray-500">PT/PCdoB/PV/PSB/PDT/+</div>
        </div>
        <div className="card !p-3">
          <div className="text-xs text-gray-500 uppercase">Estados com cobertura</div>
          <div className="text-3xl font-bold font-mono text-info">{porEstado.size}/27</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Donut */}
        <div className="card lg:col-span-1">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-2">
            Distribuição partidária
          </h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={porPartido}
                  dataKey="total"
                  nameKey="sigla"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={2}
                  label={(entry) => entry.sigla}
                  labelLine={false}
                >
                  {porPartido.map((p) => (
                    <Cell key={p.sigla} fill={p.cor} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: any) => [`${v} candidatos`, ""]} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-1 mt-3 max-h-40 overflow-y-auto">
            {porPartido.map((p) => (
              <div key={p.sigla} className="flex items-center gap-2 text-xs">
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ backgroundColor: p.cor }}
                />
                <span className="font-mono font-bold w-12">{p.sigla}</span>
                <span className="text-gray-500 flex-1 truncate">
                  {partidos.find((pp) => pp.sigla === p.sigla)?.nome_completo || ""}
                </span>
                <span className="font-mono font-bold">{p.total}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Lista por estado */}
        <div className="card lg:col-span-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-700 mb-3">
            Pré-candidatos por estado
          </h2>
          <div className="space-y-3 max-h-[600px] overflow-y-auto">
            {estados
              .sort((a, b) => a.nome.localeCompare(b.nome))
              .map((e) => {
                const cands = porEstado.get(e.id) || [];
                if (cands.length === 0) return null;
                return (
                  <div key={e.id} className="border-b border-gray-100 pb-2 last:border-0">
                    <Link
                      to={`/estados/${e.sigla}/candidaturas`}
                      className="flex items-center gap-2 mb-1 hover:text-info"
                    >
                      <span className="font-mono text-xs px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 font-bold">
                        {e.sigla}
                      </span>
                      <span className="font-medium text-sm">{e.nome}</span>
                      <span className="text-xs text-gray-400 ml-auto">
                        {cands.length} candidato{cands.length > 1 ? "s" : ""}
                      </span>
                    </Link>
                    <div className="ml-12 space-y-0.5">
                      {cands.map((c) => (
                        <Link
                          key={c.id}
                          to={c.pessoa ? `/pessoas/${c.pessoa.id}` : "#"}
                          className="flex items-center gap-2 text-xs hover:text-info"
                        >
                          <span
                            className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                            style={{ backgroundColor: c.partido?.cor_hex || "#6B7280" }}
                          />
                          <span className="font-medium">{c.pessoa?.nome_urna || c.pessoa?.nome_completo || "?"}</span>
                          <span className="text-gray-500 font-mono">({c.partido?.sigla})</span>
                          {c.observacao && (
                            <span className="text-gray-400 italic truncate">— {c.observacao}</span>
                          )}
                        </Link>
                      ))}
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      {casa === "senado" && (
        <div className="mt-4 card !p-3 bg-blue-50 border-blue-200 text-xs text-blue-900">
          <strong>Ciclo 2026:</strong> serão renovadas 54 cadeiras (2 por estado), referentes aos senadores
          eleitos em 2018. Os 27 senadores eleitos em 2022 (1 por estado) seguem com mandato até 2030.
        </div>
      )}
    </div>
  );
}
