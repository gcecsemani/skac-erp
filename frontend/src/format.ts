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

const PACK_UNIT: Record<string, string> = {
  mls: "ml", ml: "ml",
  ltrs: "L", ltr: "L", l: "L", litre: "L", liter: "L",
  kgs: "kg", kg: "kg",
  gms: "g", gm: "g", g: "g",
};

/** Turn packing tokens like 100MLS / 50KG into a short sale-unit label. */
export function prettyPack(raw: string): string {
  const spaced = String(raw || "").trim().replace(/\s+/g, " ");
  if (!spaced) return "";
  const compact = spaced.replace(/\s+/g, "");
  const m = compact.match(/^(\d+(?:\.\d+)?)(.*)$/i);
  if (!m) return spaced;
  const mapped = PACK_UNIT[m[2].toLowerCase()];
  return mapped ? `${m[1]}${mapped}` : spaced;
}

/**
 * Unit of the on-hand / billed quantity.
 * Stock is pack count (50 bottles of 100ml), not SI volume/weight.
 */
const WEIGHT_RE = /(\d+(?:\.\d+)?)\s*(kgs?|g(?:ms?)?)(?![a-z])/gi;
const LOOSE_ALIASES = new Set(["kg", "kgs", "kilogram", "kilograms", "g", "gm", "gms", "gram", "grams"]);

export function parseWeight(label: string | null | undefined): [number, "kg" | "g"] | null {
  const text = String(label || "");
  let last: [number, "kg" | "g"] | null = null;
  const re = new RegExp(WEIGHT_RE.source, "gi");
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    const qty = Number(m[1]);
    if (qty > 0) last = [qty, m[2].toLowerCase().startsWith("kg") ? "kg" : "g"];
  }
  if (last) return last;
  const compact = prettyPack(text).replace(/\s+/g, "");
  const exact = compact.match(/^(\d+(?:\.\d+)?)(kg|g)$/i);
  if (!exact) return null;
  const qty = Number(exact[1]);
  return qty > 0 ? [qty, exact[2].toLowerCase() as "kg" | "g"] : null;
}

function fmtQty(n: number): string {
  const s = String(Math.round(n * 1000) / 1000);
  return s.replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

export function localISODate(d = new Date()): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function saleUnit(p: any): string {
  return packInfo(p).saleUnit;
}

function rawSaleUnit(p: any): string {
  // Name suffix wins over dump attributes.packing (e.g. renamed UREA - 45KGS
  // while packing is still 50KGS).
  const fromName = String(p?.name || "").match(/\s[-–]\s*(\d[\w.\s]*)$/);
  if (fromName) {
    const pretty = prettyPack(fromName[1]);
    if (pretty) return pretty;
  }
  const named = parseWeight(p?.name);
  if (named) return `${fmtQty(named[0])}${named[1]}`;
  const pack = p?.packing || p?.attributes?.packing;
  if (pack && !/^(unit|units|packet|pcs|nos)$/i.test(String(pack).trim())) {
    return prettyPack(String(pack)) || String(pack).trim();
  }
  const labeled = String(p?.sale_unit || p?.base_unit || "").trim();
  if (labeled && !/^(litre|liter|kg|kilogram)$/i.test(labeled)) return labeled;
  return labeled || "pcs";
}

export type PackInfo = {
  saleUnit: string;
  packSize: number;
  looseUnit: string | null;
  allowsLoose: boolean;
};

/** Pack vs loose (kg) for fertilizer bags of any size. Stock stays in packs. */
export function packInfo(p: any): PackInfo {
  const sale = rawSaleUnit(p);
  const parsed = parseWeight(sale) || parseWeight(p?.packing || p?.attributes?.packing) || parseWeight(p?.name);
  let packSize = parsed ? parsed[0] : 1;
  let looseUnit: string | null = parsed ? parsed[1] : null;
  const sizeOverride = p?.attributes?.pack_size ?? p?.pack_size;
  if (sizeOverride != null && Number(sizeOverride) > 1) packSize = Number(sizeOverride);
  if (p?.loose_unit) looseUnit = String(p.loose_unit).toLowerCase();
  else if (p?.attributes?.loose_unit) looseUnit = String(p.attributes.loose_unit).toLowerCase();
  const flag = p?.sell_loose ?? p?.attributes?.sell_loose ?? (p?.allows_loose === true ? true : p?.allows_loose === false ? false : undefined);
  if (packSize > 1 && looseUnit !== "kg" && looseUnit !== "g" && flag !== false) looseUnit = "kg";
  let allows = packSize > 1 && (looseUnit === "kg" || looseUnit === "g");
  if (flag === false) allows = false;
  if (flag === true && packSize > 1) {
    looseUnit = looseUnit === "g" ? "g" : "kg";
    allows = true;
  }
  if (p?.allows_loose === true && packSize > 1) {
    looseUnit = looseUnit === "g" ? "g" : (looseUnit || "kg");
    allows = true;
  }
  const saleUnitLabel = allows && looseUnit ? `${fmtQty(packSize)}${looseUnit}` : sale;
  return { saleUnit: saleUnitLabel, packSize, looseUnit: allows ? looseUnit : null, allowsLoose: allows };
}

export function billedToStock(qty: number, unit: string | undefined, info: PackInfo): number {
  const billed = String(unit || "").toLowerCase().replace(/\s+/g, "");
  if (!info.allowsLoose || !info.looseUnit || !info.packSize) return qty;
  if (billed === info.saleUnit.toLowerCase().replace(/\s+/g, "")) return qty;
  if (billed === info.looseUnit || LOOSE_ALIASES.has(billed)) return qty / info.packSize;
  const parsed = parseWeight(unit);
  if (parsed && parsed[1] === info.looseUnit && (parsed[0] === 1 || LOOSE_ALIASES.has(billed))) {
    return qty / info.packSize;
  }
  return qty;
}

export function formatPackStock(stock: number, info: PackInfo): string {
  const packs = Math.round(stock * 1000) / 1000;
  if (!info.allowsLoose) return `${packs} ${info.saleUnit}`;
  const kg = Math.round(stock * info.packSize * 1000) / 1000;
  return `${packs} × ${info.saleUnit} (${kg} ${info.looseUnit})`;
}

export function loosePrice(packPrice: number, info: PackInfo): number {
  if (!info.packSize) return packPrice;
  return Math.round((packPrice / info.packSize + Number.EPSILON) * 100) / 100;
}
