/**
 * Formatting helpers shared across the app.
 *
 * We rely on the browser's built-in ``Intl`` APIs rather than pulling in
 * ``date-fns`` — Next 16 + modern browsers ship robust locale support and the
 * candidate dashboard's formatting needs are shallow (dates, times, durations,
 * scores). Adding a whole date lib for these would be dead weight.
 */

/** Human-readable date, e.g. "Aug 12, 2026". Returns "—" for null. */
export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
}

/** Wall-clock time in the viewer's timezone, e.g. "3:15 PM". */
export function formatTime(value: string | Date | null | undefined): string {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

/** Compact "Aug 12, 2026 · 3:15 PM" for interview scheduling cells. */
export function formatDateTime(
  value: string | Date | null | undefined,
): string {
  if (!value) return "—";
  const d = formatDate(value);
  const t = formatTime(value);
  return `${d} · ${t}`;
}

/** "45 min" / "1 h 30 min" depending on length. */
export function formatDuration(minutes: number | null | undefined): string {
  if (!minutes || minutes <= 0) return "—";
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

/** Score formatted with one decimal on a /10 scale, or "—" when null. */
export function formatScore(
  value: string | number | null | undefined,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return "—";
  return `${num.toFixed(1)}/10`;
}

/**
 * Semantic color class for a 0-10 score, applied as a foreground text color.
 * Used sparingly (score cells) so the dashboard stays cohesive.
 */
export function scoreTone(
  value: string | number | null | undefined,
): "muted" | "danger" | "warn" | "ok" | "great" {
  if (value === null || value === undefined || value === "") return "muted";
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return "muted";
  if (num < 4) return "danger";
  if (num < 6) return "warn";
  if (num < 8) return "ok";
  return "great";
}
