import { format, formatDistanceToNow, parseISO } from "date-fns";
import { ptBR } from "date-fns/locale";

/**
 * Parse uma string ISO assumindo UTC quando não houver timezone explícita.
 * Resolve o bug clássico em que o backend salva datetime UTC naive
 * (sem "Z") e o `new Date(...)`/`parseISO(...)` do JS interpreta como
 * horário local — fazendo timestamps aparecerem com offset errado.
 *
 * - "2026-04-29T15:30:00"     → tratado como UTC → exibido em local
 * - "2026-04-29T15:30:00Z"    → respeitado
 * - "2026-04-29T15:30:00-03:00" → respeitado
 */
export function parseUtc(s: string | null | undefined): Date | null {
  if (!s) return null;
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(s);
  return parseISO(hasTz ? s : s + "Z");
}

/** Formata um timestamp UTC do backend convertendo para horário local. */
export function formatLocalDateTime(
  s: string | null | undefined,
  fmt: string
): string {
  const d = parseUtc(s);
  return d ? format(d, fmt, { locale: ptBR }) : "";
}

/** Versão "há X minutos atrás" assumindo backend em UTC. */
export function formatRelativeUtc(s: string | null | undefined): string {
  const d = parseUtc(s);
  return d ? formatDistanceToNow(d, { locale: ptBR, addSuffix: true }) : "";
}
