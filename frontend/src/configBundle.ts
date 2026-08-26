import { useEffect, useState } from "react";
import { api } from "./api";

export type ConfigItem = {
  id: number;
  kind: string;
  parent_id: number | null;
  code: string;
  name: string;
  extra: Record<string, any>;
  is_active: boolean;
  sort_order: number;
  villages?: ConfigItem[];
};

export type ConfigBundle = {
  districts: Array<ConfigItem & { villages: ConfigItem[] }>;
  units: ConfigItem[];
  gst_rates: ConfigItem[];
  hsn: ConfigItem[];
  expense_categories: Array<ConfigItem & { key: string; label: string; account: string }>;
  toxicity_classes: ConfigItem[];
  payment_modes: ConfigItem[];
  states: ConfigItem[];
};

export const EMPTY_BUNDLE: ConfigBundle = {
  districts: [],
  units: [],
  gst_rates: [],
  hsn: [],
  expense_categories: [],
  toxicity_classes: [],
  payment_modes: [],
  states: [],
};

const FALLBACK_MODES: Record<string, { code: string; name: string }[]> = {
  pos: [
    { code: "cash", name: "Cash" },
    { code: "upi", name: "UPI" },
    { code: "card", name: "Card" },
    { code: "credit", name: "Credit (Khata) — pay later" },
  ],
  khata: [
    { code: "cash", name: "Cash" },
    { code: "upi", name: "UPI" },
    { code: "card", name: "Card" },
  ],
  expense: [
    { code: "cash", name: "Cash" },
    { code: "bank", name: "Bank" },
    { code: "upi", name: "UPI" },
  ],
  purchase: [
    { code: "cash", name: "Cash" },
    { code: "bank", name: "Bank" },
    { code: "upi", name: "UPI" },
  ],
  invoice_filter: [
    { code: "cash", name: "Cash" },
    { code: "upi", name: "UPI" },
    { code: "card", name: "Card" },
    { code: "credit", name: "Credit" },
  ],
};

let cache: ConfigBundle | null = null;
const listeners = new Set<() => void>();

export function invalidateConfigBundle() {
  cache = null;
  listeners.forEach((fn) => fn());
}

export function useConfigBundle(): { bundle: ConfigBundle; ready: boolean } {
  const [data, setData] = useState<ConfigBundle>(cache || EMPTY_BUNDLE);
  const [ready, setReady] = useState(cache !== null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ping = () => setTick((t) => t + 1);
    listeners.add(ping);
    return () => { listeners.delete(ping); };
  }, []);

  useEffect(() => {
    let cancelled = false;
    api.configBundle()
      .then((b) => {
        if (cancelled) return;
        cache = b;
        setData(b);
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) setReady(true);
      });
    return () => { cancelled = true; };
  }, [tick]);

  return { bundle: data, ready };
}

export function modesFor(bundle: ConfigBundle, use: string): { code: string; name: string }[] {
  const list = (bundle.payment_modes || []).filter((m) => {
    const uses = m.extra?.use_in;
    return !Array.isArray(uses) || uses.includes(use);
  });
  if (list.length) return list.map((m) => ({ code: m.code, name: m.name }));
  return FALLBACK_MODES[use] || FALLBACK_MODES.pos;
}

export function gstValue(item: ConfigItem): string {
  const rate = item.extra?.rate;
  return rate == null || rate === "" ? item.code : String(rate);
}
