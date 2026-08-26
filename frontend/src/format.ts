export const inr = (n: number | string | null | undefined) => {
  const v = Number(n ?? 0);
  return "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
};

export const num = (n: number | string | null | undefined) =>
  Number(n ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 3 });

export const CATEGORY_COLORS: Record<string, string> = {
  fertilizer: "#16a34a",
  pesticide: "#d97706",
  seed: "#7c3aed",
};

export const CHART_COLORS = ["#16a34a", "#0d9488", "#2563eb", "#d97706", "#7c3aed", "#e11d48"];

export function matchesQuery(q: string, ...vals: unknown[]): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return vals.some((v) => String(v ?? "").toLowerCase().includes(needle));
}
