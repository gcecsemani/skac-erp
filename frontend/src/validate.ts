/** Shared client-side form checks. Return an error string, or null when valid. */

export function required(v: unknown, label: string): string | null {
  if (v == null || String(v).trim() === "") return `${label} is required.`;
  return null;
}

export function email(v: string): string | null {
  const s = (v || "").trim();
  if (!s) return "Email is required.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(s)) return "Enter a valid email address.";
  return null;
}

export function phone(v: string | null | undefined, opts?: { required?: boolean }): string | null {
  const s = (v || "").trim();
  if (!s) return opts?.required ? "Phone number is required." : null;
  const digits = s.replace(/\D/g, "");
  if (digits.length !== 10) return "Enter a 10-digit mobile number.";
  return null;
}

export function aadhaar(v: string | null | undefined): string | null {
  const s = (v || "").trim();
  if (!s) return null;
  if (!/^\d{12}$/.test(s)) return "Aadhaar must be exactly 12 digits.";
  return null;
}

export function gstin(v: string | null | undefined): string | null {
  const s = (v || "").trim();
  if (!s) return null;
  if (!/^[0-9A-Z]{15}$/i.test(s)) return "GSTIN must be 15 characters.";
  return null;
}

export function pincode(v: string | null | undefined): string | null {
  const s = (v || "").trim();
  if (!s) return null;
  if (!/^\d{6}$/.test(s)) return "Pincode must be 6 digits.";
  return null;
}

export function password(v: string, opts?: { required?: boolean; min?: number }): string | null {
  const min = opts?.min ?? 6;
  if (!v) return opts?.required === false ? null : "Password is required.";
  if (v.length < min) return `Password must be at least ${min} characters.`;
  return null;
}

export function positive(v: unknown, label: string): string | null {
  const n = Number(v);
  if (!Number.isFinite(n) || n <= 0) return `${label} must be greater than zero.`;
  return null;
}

export function nonNegative(v: unknown, label: string): string | null {
  const n = Number(v);
  if (!Number.isFinite(n) || n < 0) return `${label} cannot be negative.`;
  return null;
}

export function gstRate(v: unknown): string | null {
  const n = Number(v);
  if (!Number.isFinite(n) || n < 0 || n > 28) return "GST rate must be between 0 and 28.";
  return null;
}

export function minLen(v: unknown, label: string, n: number): string | null {
  if (String(v ?? "").trim().length < n) return `${label} must be at least ${n} characters.`;
  return null;
}

export function firstError(...msgs: Array<string | null | undefined>): string | null {
  return msgs.find((m) => !!m) ?? null;
}
