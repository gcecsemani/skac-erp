export const inr = (n: number | string | null | undefined) => {
  const v = Number(n ?? 0);
  return "₹" + v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
};

const ONES = [
  "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
  "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
  "Seventeen", "Eighteen", "Nineteen",
];
const TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

function chunkToWords(n: number): string {
  if (n <= 0) return "";
  if (n < 20) return ONES[n];
  if (n < 100) return `${TENS[Math.floor(n / 10)]}${n % 10 ? " " + ONES[n % 10] : ""}`.trim();
  return `${ONES[Math.floor(n / 100)]} Hundred${n % 100 ? " " + chunkToWords(n % 100) : ""}`.trim();
}

/** Indian numbering: rupees and paise in words. */
export function inrWords(n: number | string | null | undefined): string {
  const v = Math.abs(Number(n ?? 0));
  if (!Number.isFinite(v)) return "";
  const rupees = Math.floor(v + 1e-9);
  const paise = Math.round((v - rupees) * 100);
  if (rupees === 0 && paise === 0) return "INR Zero Only";
  const crore = Math.floor(rupees / 1e7);
  const lakh = Math.floor((rupees % 1e7) / 1e5);
  const thousand = Math.floor((rupees % 1e5) / 1e3);
  const rest = rupees % 1e3;
  const parts: string[] = [];
  if (crore) parts.push(`${chunkToWords(crore)} Crore`);
  if (lakh) parts.push(`${chunkToWords(lakh)} Lakh`);
  if (thousand) parts.push(`${chunkToWords(thousand)} Thousand`);
  if (rest) parts.push(chunkToWords(rest));
  let out = parts.join(" ").replace(/\s+/g, " ").trim() || "Zero";
  if (paise) out += ` and ${chunkToWords(paise)} Paise`;
  return `INR ${out} Only`;
}

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
