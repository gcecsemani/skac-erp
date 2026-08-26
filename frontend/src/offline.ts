// Offline-first POS support: cache masters + queue invoices in IndexedDB.
// When connectivity resumes, the outbox is flushed to /sales/sync (idempotent
// by client_uuid on the server).
import { openDB, DBSchema, IDBPDatabase } from "idb";
import { api } from "./api";

interface SkacDB extends DBSchema {
  products: { key: number; value: any };
  outbox: { key: string; value: any };
}

let dbPromise: Promise<IDBPDatabase<SkacDB>> | null = null;

function db() {
  if (!dbPromise) {
    dbPromise = openDB<SkacDB>("skac-pos", 1, {
      upgrade(d) {
        if (!d.objectStoreNames.contains("products")) d.createObjectStore("products", { keyPath: "id" });
        if (!d.objectStoreNames.contains("outbox")) d.createObjectStore("outbox", { keyPath: "client_uuid" });
      },
    });
  }
  return dbPromise;
}

export async function cacheProducts(products: any[]) {
  const d = await db();
  const tx = d.transaction("products", "readwrite");
  for (const p of products) await tx.store.put(p);
  await tx.done;
}

export async function getCachedProducts(): Promise<any[]> {
  return (await db()).getAll("products");
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

// Flush queued invoices to the server; clears the outbox on success.
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
