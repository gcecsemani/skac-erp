// API client for the SKAC backend.
const BASE_URL =
  (import.meta as any).env?.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "skac_token";
const REFRESH_KEY = "skac_refresh";
export const AUTH_EXPIRED_EVENT = "skac:auth-expired";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}
export function setRefreshToken(token: string) {
  localStorage.setItem(REFRESH_KEY, token);
}
export function setSession(access: string, refresh?: string) {
  setToken(access);
  if (refresh) setRefreshToken(refresh);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  // The next user must not inherit this user's branch scope.
  clearBranchCache();
}

function tokenExpiresSoon(token: string, skewMs = 60_000): boolean {
  try {
    const part = token.split(".")[1];
    if (!part) return true;
    const padded = part.replace(/-/g, "+").replace(/_/g, "/") + "==".slice(0, (4 - (part.length % 4)) % 4);
    const payload = JSON.parse(atob(padded));
    if (typeof payload.exp !== "number") return false;
    return payload.exp * 1000 < Date.now() + skewMs;
  } catch {
    return true;
  }
}

function skipRefresh(path: string): boolean {
  return path.startsWith("/auth/login") || path.startsWith("/auth/refresh");
}

let refreshInFlight: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) return false;
    try {
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) return false;
      const body = await res.json();
      if (!body?.access_token) return false;
      setSession(body.access_token, body.refresh_token);
      return true;
    } catch {
      return false;
    }
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

function expireSession() {
  clearToken();
  window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

function formatApiError(body: any, fallback: string): string {
  const detail = body?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item: any) => {
      if (typeof item === "string") return item;
      const field = Array.isArray(item?.loc) ? String(item.loc[item.loc.length - 1]) : "";
      const msg = String(item?.msg || "Invalid value");
      const lower = msg.toLowerCase();
      if (field === "email" || lower.includes("email")) return "Please enter a valid email address.";
      if (field === "password") return "Please enter your password.";
      if (lower.includes("field required") || lower.includes("missing")) {
        return field ? `Please fill in ${field.replace(/_/g, " ")}.` : "Please fill in all required fields.";
      }
      return field ? `${field.replace(/_/g, " ")}: ${msg}` : msg;
    });
    return [...new Set(parts.filter(Boolean))].join(" ") || fallback;
  }
  if (detail && typeof detail === "object" && typeof detail.msg === "string") return detail.msg;
  return fallback || "Something went wrong. Please try again.";
}

async function request<T>(path: string, options: RequestInit = {}, didRefresh = false): Promise<T> {
  if (!didRefresh && !skipRefresh(path)) {
    const token = getToken();
    if ((token && tokenExpiresSoon(token)) || (!token && getRefreshToken())) {
      const ok = await tryRefresh();
      if (!ok && !token) {
        expireSession();
        throw new Error("Your session expired. Please sign in again.");
      }
    }
  }

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const isForm = typeof FormData !== "undefined" && options.body instanceof FormData;
  if (!isForm && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (res.status === 401 && !didRefresh && !skipRefresh(path)) {
    const ok = await tryRefresh();
    if (ok) return request<T>(path, options, true);
    expireSession();
    throw new Error("Your session expired. Please sign in again.");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(formatApiError(body, res.statusText));
  }
  if (res.status === 204) return undefined as T;
  const ctype = res.headers.get("content-type") || "";
  if (ctype.includes("application/json")) return res.json();
  return (await res.blob()) as T;
}

const get = <T,>(p: string, init?: RequestInit) => request<T>(p, init);
const post = <T,>(p: string, body?: any) =>
  request<T>(p, { method: "POST", body: JSON.stringify(body ?? {}) });
const put = <T,>(p: string, body?: any) =>
  request<T>(p, { method: "PUT", body: JSON.stringify(body ?? {}) });
const del = <T,>(p: string) => request<T>(p, { method: "DELETE" });

let branchCache: Promise<any[]> | null = null;
/** Drop the shared branch list so the next read refetches it. */
export function clearBranchCache() {
  branchCache = null;
}

export const api = {
  // auth
  login: (email: string, password: string, totp_code?: string) =>
    post<{ access_token: string; refresh_token: string; requires_2fa: boolean }>(
      "/auth/login", { email, password, totp_code }
    ),
  me: () => get<any>("/auth/me"),
  setup2fa: () => post<{ secret: string; provisioning_uri: string }>("/auth/2fa/setup"),
  verify2fa: (code: string) => post("/auth/2fa/verify", { code }),

  // masters
  // Nearly every page needs the branch list on mount. It changes only when an
  // owner edits a shop, so share one request instead of refetching per route.
  branches: () => {
    if (!branchCache) {
      branchCache = get<any[]>("/branches").catch((e) => {
        branchCache = null;
        throw e;
      });
    }
    return branchCache;
  },
  createBranch: (b: any) => post("/branches", b).finally(clearBranchCache),
  updateBranch: (id: number, b: any) => put(`/branches/${id}`, b).finally(clearBranchCache),
  deleteBranch: (id: number) => del(`/branches/${id}`).finally(clearBranchCache),
  products: (search?: string, category?: string, limit?: number, branchId?: number) => {
    const p = new URLSearchParams();
    if (search) p.set("search", search);
    if (category) p.set("category", category);
    if (limit) p.set("limit", String(limit));
    if (branchId) p.set("branch_id", String(branchId));
    const q = p.toString();
    return get<any[]>(`/products${q ? `?${q}` : ""}`);
  },
  createProduct: (p: any) => post<any>("/products", p),
  updateProduct: (id: number, p: any) => put<any>(`/products/${id}`, p),
  deleteProduct: (id: number) => del(`/products/${id}`),
  setFavorite: (id: number, is_favorite: boolean) => post<any>(`/products/${id}/favorite`, { is_favorite }),
  customers: (search?: string, limit?: number, outstandingOnly?: boolean) => {
    const p = new URLSearchParams();
    if (search) p.set("search", search);
    if (limit) p.set("limit", String(limit));
    if (outstandingOnly) p.set("outstanding_only", "true");
    const q = p.toString();
    return get<any[]>(`/customers${q ? `?${q}` : ""}`);
  },
  createCustomer: (c: any) => post<any>("/customers", c),
  updateCustomer: (id: number, c: any) => put<any>(`/customers/${id}`, c),
  deleteCustomer: (id: number) => del(`/customers/${id}`),

  // inventory
  stock: (branchId?: number) => get<any[]>(`/inventory/stock${branchId ? `?branch_id=${branchId}` : ""}`),
  receiveStock: (r: any) => post("/inventory/receive", r),
  adjustStock: (r: any) => post("/inventory/adjust", r),
  updateBatchCost: (batchId: number, purchase_price: number) =>
    put<any>(`/inventory/batches/${batchId}`, { purchase_price }),
  forecast: (onlyNeeding = false) => get<any[]>(`/inventory/forecast?only_needing_purchase=${onlyNeeding}`),
  logStockCount: (r: any) => post<any>("/inventory/discrepancies", r),
  investigateStockCase: (id: number) => post<any>(`/inventory/discrepancies/${id}/investigate`, {}),
  resolveStockCase: (id: number, resolution: string) =>
    post<any>(`/inventory/discrepancies/${id}/resolve`, { resolution }),
  stockTrail: (productId: number, branchId: number, start?: string, end?: string) => {
    const p = new URLSearchParams({ product_id: String(productId), branch_id: String(branchId) });
    if (start) p.set("start", start);
    if (end) p.set("end", end);
    return get<any>(`/inventory/trail?${p.toString()}`);
  },

  // sales
  createInvoice: (payload: any) => post<any>("/sales/invoices", payload),
  invoices: (opts?: number | {
    branchId?: number; start?: string; end?: string; search?: string;
    paymentMode?: string; unpaidOnly?: boolean; limit?: number; signal?: AbortSignal;
  }) => {
    const o = typeof opts === "number" ? { branchId: opts } : (opts || {});
    const p = new URLSearchParams();
    if (o.branchId) p.set("branch_id", String(o.branchId));
    if (o.start) p.set("start", o.start);
    if (o.end) p.set("end", o.end);
    if (o.search) p.set("search", o.search);
    if (o.paymentMode) p.set("payment_mode", o.paymentMode);
    if (o.unpaidOnly) p.set("unpaid_only", "true");
    if (o.limit) p.set("limit", String(o.limit));
    const q = p.toString();
    return get<any[]>(`/sales/invoices${q ? `?${q}` : ""}`, o.signal ? { signal: o.signal } : undefined);
  },
  invoice: (id: number) => get<any>(`/sales/invoices/${id}`),
  findInvoices: (q?: string, signal?: AbortSignal) =>
    get<any[]>(`/sales/invoices/find${q ? `?q=${encodeURIComponent(q)}` : ""}`, signal ? { signal } : undefined),
  syncInvoices: (invoices: any[]) => post<any[]>("/sales/sync", { invoices }),

  // returns
  creditNotes: () => get<any[]>("/returns"),
  createCreditNote: (c: any) => post("/returns", c),

  // purchasing
  vendors: (search?: string) =>
    get<any[]>(`/purchasing/vendors${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createVendor: (v: any) => post("/purchasing/vendors", v),
  updateVendor: (id: number, v: any) => put(`/purchasing/vendors/${id}`, v),
  deleteVendor: (id: number) => del(`/purchasing/vendors/${id}`),
  vendorLedger: (id: number) => get<any>(`/purchasing/vendors/${id}/ledger`),
  purchaseOrders: (search?: string) =>
    get<any[]>(`/purchasing/orders${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createPO: (p: any) => post("/purchasing/orders", p),
  grns: (search?: string) =>
    get<any[]>(`/purchasing/grn${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createGRN: (g: any) => post("/purchasing/grn", g),
  grn: (id: number) => get<any>(`/purchasing/grn/${id}`),
  purchaseReturns: (search?: string) =>
    get<any[]>(`/purchasing/returns${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createPurchaseReturn: (p: any) => post<any>("/purchasing/returns", p),
  reverseGRN: (id: number, p: any) => post<any>(`/purchasing/grn/${id}/reverse`, p),
  vendorPayment: (p: any) => post("/purchasing/payments", p),
  reverseVendorPayment: (id: number, p: any) => post<any>(`/purchasing/payments/${id}/reverse`, p),

  expenses: (opts?: { branchId?: number; start?: string; end?: string; category?: string }) => {
    const p = new URLSearchParams();
    if (opts?.branchId) p.set("branch_id", String(opts.branchId));
    if (opts?.start) p.set("start", opts.start);
    if (opts?.end) p.set("end", opts.end);
    if (opts?.category) p.set("category", opts.category);
    const q = p.toString();
    return get<any[]>(`/expenses${q ? `?${q}` : ""}`);
  },
  expenseCategories: () => get<any[]>("/expenses/categories"),
  createExpense: (e: any) => post("/expenses", e),

  dayClosePreview: (branchId: number, closeDate?: string) => {
    const p = new URLSearchParams({ branch_id: String(branchId) });
    if (closeDate) p.set("close_date", closeDate);
    return get<any>(`/day-close/preview?${p}`);
  },
  dayCloses: (branchId?: number) =>
    get<any[]>(`/day-close${branchId ? `?branch_id=${branchId}` : ""}`),
  saveDayClose: (body: any) => post<any>("/day-close", body),

  // field visits
  fieldVisits: (opts?: { status?: string; branchId?: number; search?: string }) => {
    const p = new URLSearchParams();
    if (opts?.status) p.set("status", opts.status);
    if (opts?.branchId) p.set("branch_id", String(opts.branchId));
    if (opts?.search) p.set("search", opts.search);
    const q = p.toString();
    return get<any[]>(`/field-visits${q ? `?${q}` : ""}`);
  },
  fieldVisit: (id: number) => get<any>(`/field-visits/${id}`),
  fieldVisitStaff: () => get<any[]>("/field-visits/staff"),
  createFieldVisit: (v: any) => post<any>("/field-visits", v),
  uploadVisitPhotos: (id: number, files: File[]) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("photos", f));
    return request<any>(`/field-visits/${id}/photos`, { method: "POST", body: fd });
  },
  visitPhotoBlob: (visitId: number, photoId: number) =>
    request<Blob>(`/field-visits/${visitId}/photos/${photoId}`),
  deleteVisitPhoto: (visitId: number, photoId: number) =>
    del<any>(`/field-visits/${visitId}/photos/${photoId}`),
  deleteVisitPhotos: (visitId: number) =>
    del<any>(`/field-visits/${visitId}/photos`),
  completeFieldVisit: (id: number, note?: string) =>
    post<any>(`/field-visits/${id}/complete`, { note: note || null }),
  cancelFieldVisit: (id: number, note?: string) =>
    post<any>(`/field-visits/${id}/cancel`, { note: note || null }),

  // transfers
  transfers: () => get<any[]>("/transfers"),
  transfer: (id: number) => get<any>(`/transfers/${id}`),
  createTransfer: (t: any) => post<any>("/transfers", t),
  approveTransfer: (id: number) => post(`/transfers/${id}/approve`),
  rejectTransfer: (id: number) => post(`/transfers/${id}/reject`),

  // accounting
  accounts: () => get<any[]>("/accounting/accounts"),
  daybook: (start?: string, end?: string) => get<any[]>(`/accounting/daybook?${new URLSearchParams({ ...(start ? { start } : {}), ...(end ? { end } : {}) })}`),
  pnl: (start?: string, end?: string) => get<any>(`/accounting/pnl?${new URLSearchParams({ ...(start ? { start } : {}), ...(end ? { end } : {}) })}`),
  gstSummary: (start?: string, end?: string) => get<any>(`/accounting/gst-summary?${new URLSearchParams({ ...(start ? { start } : {}), ...(end ? { end } : {}) })}`),
  receivablesAging: () => get<any>("/accounting/receivables-aging"),
  payables: () => get<any>("/accounting/payables"),

  // reports
  dashboard: (opts?: { branchId?: number; preset?: string; start?: string; end?: string; signal?: AbortSignal }) => {
    const p = new URLSearchParams();
    if (opts?.branchId) p.set("branch_id", String(opts.branchId));
    if (opts?.preset && opts.preset !== "custom") p.set("preset", opts.preset);
    if (opts?.start) p.set("start", opts.start);
    if (opts?.end) p.set("end", opts.end);
    const q = p.toString();
    return get<any>(`/reports/dashboard${q ? `?${q}` : ""}`, opts?.signal ? { signal: opts.signal } : undefined);
  },
  runReport: (type: string, opts?: { branchId?: number; start?: string; end?: string; signal?: AbortSignal }) => {
    const p = new URLSearchParams({ type });
    if (opts?.branchId) p.set("branch_id", String(opts.branchId));
    if (opts?.start) p.set("start", opts.start);
    if (opts?.end) p.set("end", opts.end);
    return get<any>(`/reports/table?${p}`, opts?.signal ? { signal: opts.signal } : undefined);
  },
  customerPayment: (id: number, p: any) => post<any>(`/customers/${id}/payments`, p),
  reverseCustomerPayment: (customerId: number, paymentId: number, p: any) =>
    post<any>(`/customers/${customerId}/payments/${paymentId}/reverse`, p),
  customerLedger: (id: number) => get<any>(`/customers/${id}/ledger`),
  customerBills: (id: number, limit?: number) =>
    get<any[]>(`/customers/${id}/bills${limit ? `?limit=${limit}` : ""}`),
  remindCustomer: (id: number, send = true) =>
    post<any>(`/customers/${id}/remind?send=${send}`),

  configBundle: () => get<any>("/config/bundle"),
  configItems: (kind: string, parentId?: number, includeInactive = false) => {
    const p = new URLSearchParams({ kind });
    if (parentId != null) p.set("parent_id", String(parentId));
    if (includeInactive) p.set("include_inactive", "true");
    return get<any[]>(`/config/items?${p}`);
  },
  createConfigItem: (item: any) => post<any>("/config/items", item),
  updateConfigItem: (id: number, item: any) => put<any>(`/config/items/${id}`, item),
  deleteConfigItem: (id: number) => del<any>(`/config/items/${id}`),

  // admin & compliance
  users: () => get<any[]>("/admin/users"),
  roles: () => get<any[]>("/admin/roles"),
  createUser: (u: any) => post("/admin/users", u),
  updateUser: (id: number, u: any) => put(`/admin/users/${id}`, u),
  deleteUser: (id: number) => del(`/admin/users/${id}`),
  audit: () => get<any[]>("/admin/audit"),
  alerts: () => get<any>("/admin/alerts"),
  licenses: () => get<any[]>("/admin/licenses"),
  traceability: (batchNo: string) => get<any>(`/admin/traceability?batch_no=${encodeURIComponent(batchNo)}`),

  // ai
  ask: (question: string, branch_id?: number) => post<any>("/ai/ask", { question, branch_id }),
};
