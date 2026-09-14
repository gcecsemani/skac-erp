// Offline-first POS: IndexedDB cache for products/farmers + invoice outbox.
// Screens paint cached rows immediately, then refresh from the API (stale-while-revalidate).
// After a save/delete the in-memory + IDB copy is patched so other pages see the change.
import { openDB, DBSchema, IDBPDatabase } from "idb";
import { api } from "./api";

interface SkacDB extends DBSchema {
  products: { key: number; value: any };
  customers: { key: number; value: any };
  outbox: { key: string; value: any };
}

type Catalog = "products" | "customers";

let dbPromise: Promise<IDBPDatabase<SkacDB>> | null = null;
const mem: Record<Catalog, any[] | null> = { products: null, customers: null };
const listeners = new Set<() => void>();

function db() {
  if (!dbPromise) {
    dbPromise = openDB<SkacDB>("skac-pos", 2, {
      upgrade(d) {
        if (!d.objectStoreNames.contains("products")) d.createObjectStore("products", { keyPath: "id" });
        if (!d.objectStoreNames.contains("customers")) d.createObjectStore("customers", { keyPath: "id" });
        if (!d.objectStoreNames.contains("outbox")) d.createObjectStore("outbox", { keyPath: "client_uuid" });
      },
    });
  }
  return dbPromise;
}

function notify() {
  listeners.forEach((fn) => fn());
}

export function subscribeCatalog(fn: () => void) {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

async function replaceStore(store: Catalog, rows: any[]) {
  mem[store] = rows;
  notify();
  const d = await db();
  const tx = d.transaction(store, "readwrite");
  await tx.store.clear();
  for (const row of rows) tx.store.put(row);
  await tx.done;
}

export async function getCachedProducts(): Promise<any[]> {
  if (mem.products) return mem.products;
  const rows = await (await db()).getAll("products");
  mem.products = rows;
  return rows;
}

export async function getCachedCustomers(): Promise<any[]> {
  if (mem.customers) return mem.customers;
  const rows = await (await db()).getAll("customers");
  mem.customers = rows;
  return rows;
}

export async function cacheProducts(products: any[]) {
  await replaceStore("products", products);
}

export async function cacheCustomers(customers: any[]) {
  await replaceStore("customers", customers);
}

export function upsertCached(store: Catalog, row: any) {
  const cur = mem[store] || [];
  const i = cur.findIndex((x) => x.id === row.id);
  const next = i >= 0 ? cur.map((x) => (x.id === row.id ? { ...x, ...row } : x)) : [...cur, row];
  mem[store] = next;
  notify();
  db().then((d) => d.put(store, next.find((x) => x.id === row.id) || row)).catch(() => {});
}

export function removeCached(store: Catalog, id: number) {
  mem[store] = (mem[store] || []).filter((x) => x.id !== id);
  notify();
  db().then((d) => d.delete(store, id)).catch(() => {});
}

export async function clearCatalogs() {
  mem.products = null;
  mem.customers = null;
  const d = await db();
  await d.clear("products");
  await d.clear("customers");
  notify();
}

export function matchCustomer(c: any, q: string) {
  const s = q.trim().toLowerCase();
  if (!s) return true;
  const digits = s.replace(/\D/g, "");
  return (
    String(c.name || "").toLowerCase().includes(s) ||
    String(c.phone || "").toLowerCase().includes(s) ||
    String(c.village || "").toLowerCase().includes(s) ||
    String(c.district || "").toLowerCase().includes(s) ||
    (!!digits && String(c.phone || "").includes(digits)) ||
    (!!digits && String(c.aadhaar_no || "").includes(digits))
  );
}

export function matchProduct(p: any, q: string, category?: string) {
  if (category && p.category !== category) return false;
  const s = q.trim().toLowerCase();
  if (!s) return true;
  return (
    String(p.name || "").toLowerCase().includes(s) ||
    String(p.sku || "").toLowerCase().includes(s) ||
    String(p.barcode || "").toLowerCase().includes(s)
  );
}

/** Warm IndexedDB after login so POS / Farmers / Products open instantly next visit. */
export async function prefetchMasters() {
  const existing = await getCachedProducts();
  const jobs: Promise<unknown>[] = [refreshCustomers({ outstandingOnly: true, limit: 400 })];
  // Do not overwrite a stocked POS catalog with a master-only fetch.
  if (!existing.length) jobs.push(api.products().then(cacheProducts));
  await Promise.all(jobs);
}

export async function refreshProducts(branchId?: number) {
  const rows = await api.products(undefined, undefined, undefined, branchId);
  if (!branchId) {
    const prev = mem.products || [];
    const stock = new Map(prev.map((p) => [p.id, p.stock_qty]));
    const merged = rows.map((p) =>
      p.stock_qty == null && stock.has(p.id) ? { ...p, stock_qty: stock.get(p.id) } : p,
    );
    await cacheProducts(merged);
    return merged;
  }
  await cacheProducts(rows);
  return rows;
}

export async function refreshCustomers(opts?: { search?: string; limit?: number; outstandingOnly?: boolean }) {
  const rows = await api.customers(opts?.search, opts?.limit ?? 400, opts?.outstandingOnly);
  if (!opts?.search) await cacheCustomers(rows);
  else rows.forEach((row) => upsertCached("customers", row));
  return rows;
}

// Queue an invoice locally (offline) with a client-generated UUID.
export async function queueInvoice(invoice: any): Promise<string> {
  const client_uuid = crypto.randomUUID();
  const record = { ...invoice, client_uuid, queued_at: Date.now() };
  await (await db()).put("outbox", record);
  return client_uuid;
}

export async function pendingCount(): Promise<number> {
  return (await db()).count("outbox");
}

export async function syncOutbox(): Promise<number> {
  const d = await db();
  const pending = await d.getAll("outbox");
  if (pending.length === 0) return 0;
  await api.syncInvoices(pending);
  const tx = d.transaction("outbox", "readwrite");
  await tx.store.clear();
  await tx.done;
  return pending.length;
}
