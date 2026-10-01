import { useEffect, useMemo, useRef, useState } from "react";
import { Search, Trash2, Wifi, WifiOff, RefreshCw, CreditCard, CheckCircle2, User, X, UserPlus, Star, Printer, History } from "lucide-react";
import { api } from "../api";
import { CATEGORY_COLORS, billedToStock, formatPackStock, inr, khataText, lastBillLabel, loosePrice, num, packInfo, saleUnit } from "../format";
import { printThermalReceipt } from "../print";
import { Card, PageHeader, Badge, Modal, Field, Switch } from "../components/ui";
import { LocationFields } from "../components/configFields";
import { modesFor, useConfigBundle } from "../configBundle";
import { loadPosSession, newDraftId, savePosSession, type PosDraft } from "../posDraft";
import { getCachedCustomers, getCachedProducts, matchCustomer, pendingCount, queueInvoice, refreshCustomers, refreshProducts, syncOutbox, upsertCached } from "../offline";
import { getOpenPrintDialog, setOpenPrintDialog } from "../printPref";
import * as V from "../validate";

const emptyFarmer = { name: "", phone: "", aadhaar_no: "", village: "", district: "", credit_allowed: false, credit_limit: "" };
const POS_TILE_CAP = 80;
const FARMER_PICK_CAP = 12;

const r2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

interface Line { key: string; product_id: number; name: string; quantity: number; unit_price: number; gst_rate: number; discount: number; unit: string; }

const lineKey = (productId: number, unit: string) => `${productId}::${unit}`;

export default function POS() {
  const [boot] = useState(loadPosSession);
  const { bundle, ready } = useConfigBundle();
  const [products, setProducts] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState<number>(boot.active?.branchId || 0);
  const [lines, setLines] = useState<Line[]>(boot.active?.lines || []);
  const [search, setSearch] = useState("");
  const [tenders, setTenders] = useState<Record<string, string>>(boot.active?.tenders || {});
  const [online, setOnline] = useState(navigator.onLine);
  const [pending, setPending] = useState(0);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

  const [farmerBook, setFarmerBook] = useState<any[]>([]);
  const [remoteFarmers, setRemoteFarmers] = useState<any[] | null>(null);
  const [customer, setCustomer] = useState<any | null>(boot.active?.customer || null);
  const [custQuery, setCustQuery] = useState(boot.active?.customer?.name || "");
  const [custOpen, setCustOpen] = useState(false);
  const [addFarmer, setAddFarmer] = useState<any | null>(null);
  const [farmerErr, setFarmerErr] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshingFarmers, setRefreshingFarmers] = useState(false);
  const farmerBox = useRef<HTMLDivElement>(null);

  const [discMode, setDiscMode] = useState<"inr" | "pct">(boot.active?.discMode || "inr");
  const [billDiscount, setBillDiscount] = useState(boot.active?.billDiscount || "");
  const [activeId, setActiveId] = useState(boot.active?.id || newDraftId());
  const [held, setHeld] = useState<PosDraft[]>(boot.held || []);
  const [lastInv, setLastInv] = useState<any | null>(null);
  const [bills, setBills] = useState<any[] | null>(null);
  const [billsBusy, setBillsBusy] = useState(false);
  const [openPrint, setOpenPrint] = useState(getOpenPrintDialog);
  const branchIdRef = useRef(0);
  const loadSeq = useRef(0);
  branchIdRef.current = branchId;

  const loadProducts = async (bid?: number) => {
    const id = bid || branchIdRef.current;
    if (!id) return;
    const seq = ++loadSeq.current;
    try {
      const p = await refreshProducts(id);
      if (seq !== loadSeq.current) return;
      setProducts(p);
    } catch {
      if (seq !== loadSeq.current) return;
      setProducts(await getCachedProducts());
    }
  };

  useEffect(() => {
    api.branches().then((b) => { setBranches(b); if (b[0]) setBranchId((cur) => cur || b[0].id); }).catch(() => {});
    getCachedProducts().then((cached) => { if (cached.length) setProducts(cached); }).catch(() => {});
    getCachedCustomers().then((cached) => { if (cached.length) setFarmerBook(cached); }).catch(() => {});
    refreshCustomers({ outstandingOnly: true, limit: 400 }).then(setFarmerBook).catch(() => {});
    const on = () => setOnline(true), off = () => setOnline(false);
    window.addEventListener("online", on); window.addEventListener("offline", off);
    pendingCount().then(setPending);
    return () => {
      window.removeEventListener("online", on); window.removeEventListener("offline", off);
    };
  }, []);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (farmerBox.current && !farmerBox.current.contains(e.target as Node)) setCustOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  useEffect(() => {
    if (branchId) loadProducts(branchId);
  }, [branchId]);

  const filteredAll = useMemo(() => {
    const q = search.toLowerCase();
    const rows = products.filter((p) => !q || p.name.toLowerCase().includes(q) || p.sku?.toLowerCase().includes(q) || p.barcode?.toLowerCase().includes(q));
    return rows.sort((a, b) => Number(!!b.is_favorite) - Number(!!a.is_favorite) || String(a.name).localeCompare(String(b.name)));
  }, [products, search]);
  const favorites = useMemo(
    () => products.filter((p) => p.is_favorite).sort((a, b) => String(a.name).localeCompare(String(b.name))),
    [products],
  );
  const searching = search.trim().length > 0;
  const filtered = searching ? filteredAll.slice(0, POS_TILE_CAP) : favorites;

  useEffect(() => {
    const q = custQuery.trim();
    if (!online || q.length < 2) {
      setRemoteFarmers(null);
      return;
    }
    const t = window.setTimeout(() => {
      api.customers(q, 12).then((rows) => {
        setRemoteFarmers(rows);
        rows.forEach((r) => upsertCached("customers", r));
      }).catch(() => setRemoteFarmers(null));
    }, 180);
    return () => window.clearTimeout(t);
  }, [custQuery, online]);

  const farmerHits = useMemo(() => {
    const q = custQuery.trim();
    if (!q) return [];
    if (remoteFarmers) return remoteFarmers.slice(0, FARMER_PICK_CAP);
    return farmerBook.filter((c) => matchCustomer(c, q)).slice(0, FARMER_PICK_CAP);
  }, [farmerBook, custQuery, remoteFarmers]);

  const toggleFav = async (p: any) => {
    const next = !p.is_favorite;
    const updated = { ...p, is_favorite: next };
    setProducts((cur) => cur.map((x) => x.id === p.id ? updated : x));
    upsertCached("products", updated);
    try {
      await api.setFavorite(p.id, next);
    } catch {
      setProducts((cur) => cur.map((x) => x.id === p.id ? { ...x, is_favorite: p.is_favorite } : x));
      upsertCached("products", p);
    }
  };

  const refreshCatalog = async () => {
    setRefreshing(true);
    await loadProducts();
    setRefreshing(false);
    setMsg({ text: "Product list refreshed.", ok: true });
  };

  const refreshFarmerBook = async () => {
    setRefreshingFarmers(true);
    try {
      setFarmerBook(await refreshCustomers({ outstandingOnly: true, limit: 400 }));
      setMsg({ text: "Farmer list refreshed.", ok: true });
    } catch (e: any) {
      setMsg({ text: e.message || "Could not refresh farmers.", ok: false });
    } finally {
      setRefreshingFarmers(false);
    }
  };

  const stockOf = (p: any): number | null => {
    if (p?.stock_qty == null || p.stock_qty === "") return null;
    const n = Number(p.stock_qty);
    return Number.isFinite(n) ? n : null;
  };
  const unitOf = (p: any) => saleUnit(p);
  const stockUsed = (productId: number) => lines
    .filter((l) => l.product_id === productId)
    .reduce((sum, l) => {
      const p = products.find((x) => x.id === productId);
      return sum + billedToStock(l.quantity, l.unit, packInfo(p || { name: l.name, sale_unit: l.unit }));
    }, 0);

  const add = (p: any, loose = false) => {
    const info = packInfo(p);
    const unit = loose && info.allowsLoose ? (info.looseUnit || "kg") : unitOf(p);
    const key = lineKey(p.id, unit);
    const addQty = 1;
    const need = billedToStock(addQty, unit, info);
    const stock = stockOf(p);
    const used = stockUsed(p.id);
    if (stock != null && stock <= 0) {
      setMsg({ text: `${p.name} is out of stock at this branch. Receive stock before billing it.`, ok: false });
      return;
    }
    if (!loose && stock != null && stock - used > 0 && stock - used < 1 && info.allowsLoose) {
      const left = Math.round((stock - used) * info.packSize * 1000) / 1000;
      setMsg({ text: `Opened pack: ${left} ${info.looseUnit} of ${p.name} left. Add as ${info.looseUnit}.`, ok: false });
      return;
    }
    if (stock != null && used + need > stock + 1e-9) {
      const left = Math.max(0, stock - used);
      if (loose && info.allowsLoose) {
        setMsg({ text: `Only ${Math.round(left * info.packSize * 1000) / 1000} ${info.looseUnit} of ${p.name} left.`, ok: false });
      } else {
        setMsg({ text: `Only ${Math.round(left * 1000) / 1000} ${unitOf(p)} of ${p.name} left.`, ok: false });
      }
      return;
    }
    const price = loose && info.allowsLoose ? loosePrice(Number(p.sale_price), info) : Number(p.sale_price);
    setMsg(null);
    setLines((cur) => {
      const ex = cur.find((l) => l.key === key);
      if (ex) return cur.map((l) => l.key === key ? { ...l, quantity: l.quantity + addQty } : l);
      return [...cur, { key, product_id: p.id, name: p.name, quantity: addQty, unit_price: price, gst_rate: Number(p.gst_rate), discount: 0, unit }];
    });
  };
  const setQty = (key: string, q: number) => setLines((cur) => cur.map((l) => {
    if (l.key !== key) return l;
    const p = products.find((x) => x.id === l.product_id);
    const info = packInfo(p || { name: l.name, sale_unit: l.unit });
    const loose = info.allowsLoose && l.unit === info.looseUnit;
    const min = loose ? 0.01 : 1;
    let next = Number.isFinite(q) ? Math.max(min, q) : min;
    if (!loose) next = Math.max(1, Math.round(next));
    else next = Math.round(next * 1000) / 1000;
    const stock = p ? stockOf(p) : null;
    const others = stockUsed(l.product_id) - billedToStock(l.quantity, l.unit, info);
    const need = billedToStock(next, l.unit, info);
    if (stock != null && others + need > stock + 1e-9) {
      const leftPacks = Math.max(0, stock - others);
      if (loose) {
        const maxBilled = Math.round(leftPacks * info.packSize * 1000) / 1000;
        setMsg({ text: `Only ${maxBilled} ${l.unit} of ${l.name} left.`, ok: false });
        return { ...l, quantity: Math.max(min, maxBilled) };
      }
      const whole = Math.floor(leftPacks + 1e-9);
      const leftoverKg = Math.round((leftPacks - whole) * info.packSize * 1000) / 1000;
      setMsg({
        text: leftoverKg > 0 && info.allowsLoose
          ? `Only ${whole} ${l.unit} left as whole packs. ${leftoverKg} ${info.looseUnit} is an opened pack — add as ${info.looseUnit}.`
          : `Only ${whole} ${l.unit} of ${l.name} left.`,
        ok: false,
      });
      return { ...l, quantity: whole >= 1 ? whole : l.quantity };
    }
    setMsg(null);
    return { ...l, quantity: next };
  }));
  const setLineUnit = (key: string, nextUnit: string) => setLines((cur) => {
    const l = cur.find((x) => x.key === key);
    if (!l || l.unit === nextUnit) return cur;
    const p = products.find((x) => x.id === l.product_id);
    const info = packInfo(p || { name: l.name, sale_unit: l.unit });
    const stockQty = billedToStock(l.quantity, l.unit, info);
    const toLoose = info.allowsLoose && nextUnit === info.looseUnit;
    const nextBilled = toLoose ? stockQty * info.packSize : stockQty;
    const nextPrice = toLoose ? loosePrice(Number(p?.sale_price || 0), info) : Number(p?.sale_price || l.unit_price);
    const nextKey = lineKey(l.product_id, nextUnit);
    const rest = cur.filter((x) => x.key !== key);
    const ex = rest.find((x) => x.key === nextKey);
    if (ex) {
      return rest.map((x) => x.key === nextKey ? { ...x, quantity: x.quantity + nextBilled, discount: 0 } : x);
    }
    return [...rest, { ...l, key: nextKey, unit: nextUnit, quantity: Math.round(nextBilled * 1000) / 1000, unit_price: nextPrice, discount: 0 }];
  });
  const setLineDisc = (key: string, d: number) => setLines((cur) => cur.map((l) => {
    if (l.key !== key) return l;
    const cap = r2(l.quantity * l.unit_price);
    return { ...l, discount: Math.min(Math.max(0, d), cap) };
  }));
  const remove = (key: string) => setLines((cur) => cur.filter((l) => l.key !== key));

  const totals = useMemo(() => {
    const grossLines = lines.map((l) => {
      const gross = r2(l.quantity * l.unit_price);
      const lineDisc = Math.min(Math.max(l.discount || 0, 0), gross);
      return { ...l, gross, lineDisc, afterLine: r2(gross - lineDisc) };
    });
    const afterLineSum = grossLines.reduce((s, l) => s + l.afterLine, 0);
    const rawBill = discMode === "pct"
      ? r2(afterLineSum * (Number(billDiscount) || 0) / 100)
      : Math.max(Number(billDiscount) || 0, 0);
    const billDisc = Math.min(r2(rawBill), afterLineSum);

    let allocated = 0;
    const priced = grossLines.map((l, i) => {
      const isLast = i === grossLines.length - 1;
      const share = isLast
        ? r2(billDisc - allocated)
        : (afterLineSum > 0 ? r2(billDisc * (l.afterLine / afterLineSum)) : 0);
      if (!isLast) allocated += share;
      const discount = r2(l.lineDisc + share);
      const taxable = r2(l.gross - discount);
      const tax = r2(taxable * l.gst_rate / 100);
      return { ...l, discount, taxable, tax, lineTotal: r2(taxable + tax) };
    });
    const gross = priced.reduce((s, l) => s + l.gross, 0);
    const discountTotal = priced.reduce((s, l) => s + l.discount, 0);
    const sub = priced.reduce((s, l) => s + l.taxable, 0);
    const tax = priced.reduce((s, l) => s + l.tax, 0);
    return { lines: priced, gross, discountTotal, billDisc, sub, tax, grand: r2(sub + tax) };
  }, [lines, billDiscount, discMode]);

  // The cart re-renders on every keystroke; index these so each row is a
  // lookup instead of a scan over the whole catalogue.
  const productById = useMemo(
    () => new Map<number, any>(products.map((p) => [p.id, p])),
    [products],
  );
  const pricedByKey = useMemo(
    () => new Map<string, any>(totals.lines.map((l: any) => [l.key, l])),
    [totals],
  );

  const tenderModes = useMemo(() => {
    const order = ["cash", "upi", "card"];
    const rank = (code: string) => {
      const i = order.indexOf(code);
      return i === -1 ? order.length : i;
    };
    return modesFor(bundle, "pos")
      .filter((m) => m.code !== "credit")
      .sort((a, b) => rank(a.code) - rank(b.code));
  }, [bundle]);
  const received = r2(tenderModes.reduce((sum, m) => sum + Math.max(0, Number(tenders[m.code]) || 0), 0));
  const overReceived = received - totals.grand > 0.009;
  const paid = overReceived ? totals.grand : received;
  const due = overReceived ? 0 : r2(totals.grand - paid);

  const snapshot = (): PosDraft => ({
    id: activeId,
    branchId,
    customer,
    lines,
    tenders,
    billDiscount,
    discMode,
    savedAt: Date.now(),
  });

  useEffect(() => {
    const active = lines.length || customer ? snapshot() : null;
    savePosSession({ active, held });
  }, [lines, customer, tenders, billDiscount, discMode, branchId, held, activeId]);

  const clearActive = () => {
    setLines([]);
    setCustomer(null);
    setCustQuery("");
    setBillDiscount("");
    setDiscMode("inr");
    setTenders({});
    setActiveId(newDraftId());
    setBills(null);
  };

  const holdCurrent = () => {
    if (!lines.length && !customer) return;
    const draft = snapshot();
    setHeld((cur) => [draft, ...cur.filter((h) => h.id !== draft.id)].slice(0, 12));
    clearActive();
    setMsg({ text: `Held ${draft.customer?.name || "walk-in"}'s bill. Start the next farmer.`, ok: true });
  };

  const resumeHeld = (id: string) => {
    const target = held.find((h) => h.id === id);
    if (!target) return;
    const current = lines.length || customer ? snapshot() : null;
    setHeld((cur) => {
      const rest = cur.filter((h) => h.id !== id);
      return current ? [current, ...rest].slice(0, 12) : rest;
    });
    setActiveId(target.id);
    setBranchId(target.branchId || branchId);
    setLines(target.lines || []);
    setCustomer(target.customer || null);
    setCustQuery(target.customer?.name || "");
    setTenders(target.tenders || {});
    setBillDiscount(target.billDiscount || "");
    setDiscMode(target.discMode || "inr");
    setBills(null);
    setMsg(null);
  };

  const discardHeld = (id: string) => setHeld((cur) => cur.filter((h) => h.id !== id));
  const projectedKhata = Number(customer?.outstanding_balance || 0) + due;
  const overLimit = !!customer && Number(customer.credit_limit) > 0 && projectedKhata > Number(customer.credit_limit);

  const selectCustomer = (c: any | null) => {
    setCustomer(c); setCustQuery(c ? c.name : ""); setCustOpen(false);
    if (!c) setBills(null);
  };

  const openBills = async () => {
    if (!customer) return;
    setBillsBusy(true);
    try {
      setBills(await api.customerBills(customer.id, 12));
    } catch (e: any) {
      setMsg({ text: e.message || "Could not load previous bills.", ok: false });
    } finally {
      setBillsBusy(false);
    }
  };

  const createFarmer = async () => {
    setFarmerErr("");
    const err = V.firstError(
      V.minLen(addFarmer.name, "Name", 2),
      V.phone(addFarmer.phone, { required: true }),
      V.required(addFarmer.district, "District"),
      V.required(addFarmer.village, "Village"),
      V.aadhaar(addFarmer.aadhaar_no),
      addFarmer.credit_limit ? V.nonNegative(addFarmer.credit_limit, "Credit limit") : null,
    );
    if (err) { setFarmerErr(err); return; }
    try {
      const created = await api.createCustomer({
        ...addFarmer,
        aadhaar_no: addFarmer.aadhaar_no || null,
        land_holding_acres: null,
        credit_limit: addFarmer.credit_limit ? Number(addFarmer.credit_limit) : 0,
      });
      upsertCached("customers", created);
      setFarmerBook((cur) => [created, ...cur.filter((x) => x.id !== created.id)]);
      selectCustomer(created);
      setAddFarmer(null);
    } catch (e: any) { setFarmerErr(e.message); }
  };

  const setTenderAmt = (code: string, value: string) => setTenders((cur) => ({ ...cur, [code]: value }));
  const fillTender = (code: string | null) => {
    const next: Record<string, string> = {};
    if (code) next[code] = String(totals.grand);
    setTenders(next);
  };

  const checkout = async () => {
    if (lines.length === 0) {
      setMsg({ text: "Add at least one product before finalizing.", ok: false });
      return;
    }
    if (overReceived) {
      setMsg({ text: "Amount received cannot be more than the bill total.", ok: false });
      return;
    }
    if (!branchId) {
      setMsg({ text: "Select a branch.", ok: false });
      return;
    }
    if (due > 0 && !customer) {
      setMsg({ text: "Select a farmer to capture the unpaid balance on khata.", ok: false });
      return;
    }
    if (due > 0 && customer && !customer.credit_allowed) {
      setMsg({ text: "This farmer is not allowed credit. Collect the full amount or enable khata.", ok: false });
      return;
    }
    if (overLimit) {
      setMsg({ text: `Balance would exceed ${customer.name}'s khata limit of ${inr(customer.credit_limit)}.`, ok: false });
      return;
    }
    const parts = tenderModes
      .map((m) => ({ mode: m.code, amount: r2(Math.max(0, Number(tenders[m.code]) || 0)) }))
      .filter((p) => p.amount > 0);
    const payload = {
      branch_id: branchId,
      customer_id: customer?.id ?? null,
      payment_mode: parts.length === 0 ? "credit" : parts.length === 1 ? parts[0].mode : "mixed",
      amount_paid: r2(paid),
      tenders: parts,
      lines: totals.lines.map((l) => ({
        product_id: l.product_id,
        quantity: l.quantity,
        unit_price: l.unit_price,
        discount: l.discount,
        unit: l.unit,
      })),
    };
    try {
      if (online) {
        const inv = await api.createInvoice(payload);
        const bal = r2(Number(inv.grand_total) - Number(inv.amount_paid));
        setLastInv(inv);
        const paidBits = parts.length
          ? parts.map((p) => `${p.mode} ${inr(p.amount)}`).join(" + ")
          : "all on credit";
        setMsg({
          text: bal > 0
            ? `Invoice ${inv.invoice_no} · ${paidBits} · balance ${inr(bal)} on khata`
            : `Invoice ${inv.invoice_no} finalized — ${paidBits}`,
          ok: true,
        });
        if (openPrint) printThermalReceipt(inv);
      } else {
        await queueInvoice(payload); setPending(await pendingCount());
        setMsg({ text: "Saved offline — will sync when back online.", ok: true });
      }
      clearActive();
      setProducts((cur) => cur.map((p) => {
        const sold = payload.lines.filter((l) => l.product_id === p.id);
        if (!sold.length || p.stock_qty == null) return p;
        const info = packInfo(p);
        const deduct = sold.reduce((s, l) => s + billedToStock(Number(l.quantity), l.unit, info), 0);
        const next = { ...p, stock_qty: Math.max(0, Number(p.stock_qty) - deduct) };
        upsertCached("products", next);
        return next;
      }));
      if (customer) {
        const t = new Date();
        const today = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
        const next = {
          ...customer,
          last_bill_date: today,
          outstanding_balance: due > 0 ? Number(customer.outstanding_balance || 0) + due : customer.outstanding_balance,
        };
        upsertCached("customers", next);
        setFarmerBook((cur) => [next, ...cur.filter((x) => x.id !== next.id)]);
      }
      loadProducts(branchId);
    } catch (e: any) { setMsg({ text: e.message, ok: false }); }
  };

  const doSync = async () => {
    try { const n = await syncOutbox(); setPending(await pendingCount()); setMsg({ text: `Synced ${n} offline invoice(s).`, ok: true }); }
    catch (e: any) { setMsg({ text: e.message, ok: false }); }
  };

  return (
    <div>
      <PageHeader
        title="Point of Sale"
        subtitle="Credit is the default. Hold a bill to serve the next farmer without losing this one."
        actions={
          <>
            <Badge tone={online ? "success" : "warn"}>{online ? <><Wifi size={13} /> Online</> : <><WifiOff size={13} /> Offline</>}</Badge>
            {pending > 0 && <button className="btn btn-ghost btn-sm" onClick={doSync}><RefreshCw size={15} /> Sync {pending}</button>}
            <button className="btn btn-ghost btn-sm" onClick={refreshCatalog} title="Reload products from server">
              <RefreshCw size={15} className={refreshing ? "spin" : undefined} /> Refresh products
            </button>
            <button className="btn btn-ghost btn-sm" onClick={refreshFarmerBook} title="Reload farmers added recently">
              <RefreshCw size={15} className={refreshingFarmers ? "spin" : undefined} /> Refresh farmers
            </button>
            <select value={branchId} disabled={branches.length <= 1} onChange={(e) => setBranchId(Number(e.target.value))} style={{ width: "auto" }}>
              {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </>
        }
      />

      {(held.length > 0 || (lines.length > 0 || customer)) && (
        <div className="held-bar">
          <span className="muted" style={{ fontSize: 12, fontWeight: 700 }}>
            {held.length ? "Held bills — tap to resume" : "This bill stays if you open another page"}
          </span>
          {held.map((h) => (
            <span key={h.id} className="held-chip">
              <button type="button" onClick={() => resumeHeld(h.id)}>
                {h.customer?.name || "Walk-in"} · {h.lines?.length || 0} {h.lines?.length === 1 ? "line" : "lines"}
              </button>
              <button type="button" className="x" title="Discard held bill" onClick={() => discardHeld(h.id)}><X size={12} /></button>
            </span>
          ))}
        </div>
      )}

      <div className="pos-grid">
        <Card>
          <div className="row" style={{ position: "relative" }}>
            <Search size={17} style={{ position: "absolute", left: 12, color: "#94a3b8" }} />
            <input placeholder="Search product or scan barcode…" value={search} onChange={(e) => setSearch(e.target.value)} style={{ paddingLeft: 36 }} />
          </div>
          {!searching && (
            <p className="muted" style={{ fontSize: 12, margin: "8px 0 0" }}>
              Favorites only — star a product on the Products page, or type to search the full catalog
              {favorites.length === 0 ? " (none pinned yet)" : ` · ${favorites.length} pinned`}
            </p>
          )}
          {searching && filteredAll.length > POS_TILE_CAP && (
            <p className="muted" style={{ fontSize: 12, margin: "8px 0 0" }}>
              Showing {POS_TILE_CAP} of {filteredAll.length} — keep typing to narrow
            </p>
          )}
          <div className="product-panel">
          <div className="product-grid">
            {filtered.map((p) => {
              const stock = stockOf(p);
              const info = packInfo(p);
              const out = stock != null && stock <= 0;
              const low = stock != null && stock > 0 && stock <= Number(p.reorder_level || 0);
              const stockLabel = out
                ? "Out of stock"
                : stock == null
                  ? "Stock: —"
                  : `Stock: ${formatPackStock(stock, info)}`;
              return (
              <div key={p.id} className="product-tile-wrap">
                <button type="button" className={`fav-star ${p.is_favorite ? "on" : ""}`} title={p.is_favorite ? "Unpin favorite" : "Pin as favorite"}
                  onClick={() => toggleFav(p)}>
                  <Star size={14} fill={p.is_favorite ? "currentColor" : "none"} />
                </button>
                <button className={`product-tile ${p.is_favorite ? "fav" : ""} ${out ? "out" : ""}`} onClick={() => add(p)} disabled={out}>
                  <span className="cat-dot" style={{ background: CATEGORY_COLORS[p.category] || "#64748b" }} />
                  <span className="p-name">{p.name}</span>
                  <span className="p-price">{inr(p.sale_price)}{info.allowsLoose ? <span className="muted" style={{ fontWeight: 500, fontSize: 11 }}> / {info.saleUnit}</span> : null}</span>
                  <span className={`p-stock ${out ? "out" : low ? "low" : "ok"}`}>
                    {stockLabel}
                  </span>
                  <span className="muted" style={{ fontSize: 11, textTransform: "capitalize" }}>{p.category} · {p.gst_rate}% GST</span>
                </button>
                {info.allowsLoose && (
                  <button type="button" className="loose-chip" disabled={out} title={`Add 1 ${info.looseUnit} loose`}
                    onClick={() => add(p, true)}>
                    + {info.looseUnit}
                  </button>
                )}
              </div>
              );
            })}
          </div>
          {!searching && favorites.length === 0 && (
            <p className="muted" style={{ textAlign: "center", padding: "28px 8px" }}>
              No favorite products yet. Search above, or pin products with the star on the Products page.
            </p>
          )}
          {searching && filtered.length === 0 && (
            <p className="muted" style={{ textAlign: "center", padding: "28px 8px" }}>No products match “{search.trim()}”.</p>
          )}
          </div>
        </Card>

        <Card title="Current Bill" icon={<CreditCard size={16} />}>
          <div className="table-wrap" style={{ marginBottom: 12 }}>
            <table>
              <thead><tr><th>Item</th><th>Unit</th><th className="num">Qty</th><th className="num">Rate</th><th className="num">Disc ₹</th><th className="num">Total</th><th></th></tr></thead>
              <tbody>
                {lines.length === 0 && <tr><td colSpan={7} className="muted" style={{ textAlign: "center", padding: 24 }}>Tap products to add a bag, or +kg for loose</td></tr>}
                {lines.map((l) => {
                  const priced = pricedByKey.get(l.key);
                  const p = productById.get(l.product_id);
                  const info = packInfo(p || { name: l.name, sale_unit: l.unit });
                  const loose = info.allowsLoose && l.unit === info.looseUnit;
                  return (
                    <tr key={l.key}>
                      <td>{l.name}</td>
                      <td>
                        {info.allowsLoose ? (
                          <select value={l.unit} onChange={(e) => setLineUnit(l.key, e.target.value)} style={{ width: 76, padding: 6 }}>
                            <option value={info.saleUnit}>{info.saleUnit}</option>
                            <option value={info.looseUnit || "kg"}>{info.looseUnit}</option>
                          </select>
                        ) : l.unit}
                      </td>
                      <td className="num"><input type="number" min={loose ? 0.01 : 1} step={loose ? 0.01 : 1} value={l.quantity} onChange={(e) => setQty(l.key, Number(e.target.value))} style={{ width: 64, padding: 6, textAlign: "right" }} /></td>
                      <td className="num">
                        {inr(l.unit_price)}
                        {priced && priced.discount > 0 && l.quantity > 0 && (
                          <div className="muted" style={{ fontSize: 11 }}>net {inr(priced.taxable / l.quantity)}</div>
                        )}
                      </td>
                      <td className="num"><input type="number" min={0} step="0.01" value={l.discount || ""} placeholder="0" onChange={(e) => setLineDisc(l.key, Number(e.target.value))} style={{ width: 64, padding: 6, textAlign: "right" }} /></td>
                      <td className="num">{inr(priced?.lineTotal ?? l.quantity * l.unit_price)}</td>
                      <td><button className="icon-btn" style={{ width: 30, height: 30 }} onClick={() => remove(l.key)}><Trash2 size={14} /></button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="totals-row"><span>Gross</span><span>{inr(totals.gross)}</span></div>
          <div className="totals-row" style={{ alignItems: "center", gap: 8 }}>
            <span>Bill discount</span>
            <span className="row" style={{ gap: 6 }}>
              <span className="seg">
                <button type="button" className={discMode === "inr" ? "on" : ""} onClick={() => setDiscMode("inr")}>₹</button>
                <button type="button" className={discMode === "pct" ? "on" : ""} onClick={() => setDiscMode("pct")}>%</button>
              </span>
              <input type="number" min={0} step="0.01" value={billDiscount} placeholder="0" onChange={(e) => setBillDiscount(e.target.value)} style={{ width: 88, padding: 6, textAlign: "right" }} />
            </span>
          </div>
          {totals.discountTotal > 0 && (
            <>
              <div className="totals-row"><span>Total discount</span><span>− {inr(totals.discountTotal)}</span></div>
              <p className="muted" style={{ fontSize: 12, margin: "0 0 8px" }}>
                Discount does not change the product rate. Margin reports use net sales after discount.
              </p>
            </>
          )}
          <div className="totals-row"><span>Taxable</span><span>{inr(totals.sub)}</span></div>
          <div className="totals-row"><span>GST</span><span>{inr(totals.tax)}</span></div>
          <div className="totals-grand"><span>Total</span><span>{inr(totals.grand)}</span></div>

          <div className="field mt-8">
            <label>Farmer {due > 0 ? "(required — unpaid balance goes to khata)" : "(optional — walk-in if empty)"}</label>
            {customer ? (
              <div className="row" style={{ justifyContent: "space-between", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "8px 10px" }}>
                <span className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                  <User size={15} color="var(--brand-600)" />
                  <span style={{ fontWeight: 600 }}>{customer.name}</span>
                  {customer.village && <span className="muted" style={{ fontSize: 12 }}>· {customer.village}</span>}
                  {(() => {
                    const last = lastBillLabel(customer.last_bill_date);
                    return (
                      <Badge tone={last.days == null ? "neutral" : last.days > 90 ? "warn" : "info"}>
                        {last.text}
                      </Badge>
                    );
                  })()}
                  {customer.credit_allowed && <Badge tone="info">Khata: {khataText(customer.outstanding_balance)}</Badge>}
                </span>
                <span className="row" style={{ gap: 6 }}>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={openBills} disabled={billsBusy} title="Previous bills and items">
                    <History size={14} /> {billsBusy ? "…" : "Bills"}
                  </button>
                  <button className="icon-btn" style={{ width: 30, height: 30 }} onClick={() => selectCustomer(null)}><X size={14} /></button>
                </span>
              </div>
            ) : (
              <div ref={farmerBox} style={{ position: "relative" }}>
                <div className="row" style={{ position: "relative" }}>
                  <User size={16} style={{ position: "absolute", left: 11, color: "#94a3b8" }} />
                  <input
                    placeholder="Search name, phone or Aadhaar…"
                    value={custQuery}
                    onChange={(e) => { setCustQuery(e.target.value); setCustOpen(true); }}
                    onFocus={() => setCustOpen(true)}
                    style={{ paddingLeft: 34 }}
                  />
                </div>
                {custOpen && (
                  <div style={{ position: "absolute", zIndex: 10, top: "100%", left: 0, right: 0, marginTop: 4, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", boxShadow: "var(--shadow-lg)", overflow: "hidden" }}>
                    {farmerHits.map((c) => (
                      <button key={c.id} className="row" onMouseDown={(e) => e.preventDefault()} onClick={() => selectCustomer(c)}
                        style={{ width: "100%", textAlign: "left", background: "none", border: "none", padding: "9px 12px", cursor: "pointer", justifyContent: "space-between" }}>
                        <span>
                          <strong>{c.name}</strong>{" "}
                          <span className="muted" style={{ fontSize: 12 }}>{c.phone || ""}{c.aadhaar_no ? ` · ${c.aadhaar_no}` : ""}</span>
                          <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>
                            {[c.village, lastBillLabel(c.last_bill_date).text].filter(Boolean).join(" · ")}
                          </div>
                        </span>
                        {c.credit_allowed && <Badge tone="info">Khata {khataText(c.outstanding_balance)}</Badge>}
                      </button>
                    ))}
                    {farmerHits.length === 0 && <div className="muted" style={{ padding: "9px 12px", fontSize: 13 }}>{custQuery.trim() ? "No matching farmer" : "Type name, phone or Aadhaar — search stays fast at 10,000+ farmers"}</div>}
                    <button className="row" onMouseDown={(e) => e.preventDefault()}
                      onClick={() => { setFarmerErr(""); setAddFarmer({ ...emptyFarmer, name: custQuery }); setCustOpen(false); }}
                      style={{ width: "100%", textAlign: "left", background: "var(--surface-2)", border: "none", borderTop: "1px solid var(--border)", padding: "9px 12px", cursor: "pointer", color: "var(--brand-600)", fontWeight: 600, gap: 8 }}>
                      <UserPlus size={15} /> Add new farmer{custQuery ? ` "${custQuery}"` : ""}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="field">
            <label>Received now</label>
            <p className="muted" style={{ fontSize: 12, margin: "0 0 8px" }}>
              Leave these blank to put the whole bill on credit (khata). Fill more than one to split the payment.
            </p>
            <div className="tender-row" style={{ gridTemplateColumns: `repeat(${Math.max(tenderModes.length, 1)}, minmax(0, 1fr))` }}>
              {tenderModes.map((m) => {
                const label = m.code === "upi" ? "UPI" : m.code === "cash" ? "Cash" : m.code === "card" ? "Card" : m.name.replace(/\(.*\)/, "").trim();
                return (
                  <div key={m.code} className="tender-cell">
                    <span>{label}</span>
                    <input type="number" min={0} step="0.01" placeholder="0" value={tenders[m.code] ?? ""}
                      onChange={(e) => setTenderAmt(m.code, e.target.value)} />
                    <button type="button" className="btn btn-ghost btn-sm" onClick={() => fillTender(m.code)}>All</button>
                  </div>
                );
              })}
            </div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => fillTender(null)}>All on credit</button>
            {overReceived && <div className="error" style={{ marginTop: 8 }}>Received {inr(received)} is more than the bill total.</div>}
          </div>
          <div className={`totals-row ${due > 0 ? "balance-due" : ""}`}>
            <span>Balance due</span>
            <span>{inr(due)}</span>
          </div>
          {due > 0 && (
            <div className="pay-hint">
              {customer
                ? <>{inr(due)} will be added to <strong>{customer.name}</strong>'s khata (new outstanding {inr(projectedKhata)}{customer.credit_limit > 0 ? ` / limit ${inr(customer.credit_limit)}` : ""}).</>
                : "Select a farmer so the unpaid amount can be posted to their khata."}
              {overLimit && <div className="error" style={{ marginTop: 8 }}>This exceeds the farmer's credit limit.</div>}
            </div>
          )}
          <div style={{ marginTop: 12 }}>
            <Switch
              checked={openPrint}
              onChange={(v) => { setOpenPrint(v); setOpenPrintDialog(v); }}
              label="Open print dialog after billing"
            />
          </div>
          <div className="row" style={{ gap: 8, marginTop: 12 }}>
            <button type="button" className="btn btn-ghost" disabled={!lines.length && !customer} onClick={holdCurrent} title="Park this bill and start another farmer">
              Hold bill
            </button>
            <button className="btn btn-primary" style={{ flex: 1 }} disabled={lines.length === 0 || !branchId || overReceived} onClick={checkout}>
              <CheckCircle2 size={18} /> Finalize Invoice
            </button>
          </div>
          {msg && <div className={msg.ok ? "" : "error"} style={{ marginTop: 12, color: msg.ok ? "var(--brand-600)" : undefined, fontWeight: 600, fontSize: 13 }}>{msg.text}</div>}
          {lastInv && msg?.ok && (
            <button type="button" className="btn btn-ghost btn-block" style={{ marginTop: 8 }} onClick={() => printThermalReceipt(lastInv)}>
              <Printer size={16} /> Reprint {lastInv.invoice_no}
              {lastInv.printer_name ? ` · ${lastInv.printer_name}` : ""}
            </button>
          )}
        </Card>
      </div>

      {addFarmer && (
        <Modal
          title="Add New Farmer"
          onClose={() => setAddFarmer(null)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setAddFarmer(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={createFarmer}><UserPlus size={16} /> Save & Select</button>
          </>}
        >
          {farmerErr && <div className="error">{farmerErr}</div>}
          <div className="grid grid-2">
            <Field label="Name" required><input value={addFarmer.name} onChange={(e) => setAddFarmer({ ...addFarmer, name: e.target.value })} /></Field>
            <Field label="Phone" required><input value={addFarmer.phone} onChange={(e) => setAddFarmer({ ...addFarmer, phone: e.target.value })} /></Field>
            <Field label="Aadhaar (12 digits)"><input value={addFarmer.aadhaar_no} maxLength={12} onChange={(e) => setAddFarmer({ ...addFarmer, aadhaar_no: e.target.value.replace(/\D/g, "").slice(0, 12) })} /></Field>
            <LocationFields
              district={addFarmer.district || ""}
              village={addFarmer.village || ""}
              bundle={bundle}
              ready={ready}
              required
              onChange={(next) => setAddFarmer((f: any) => ({ ...f, ...next }))}
            />
            <Field label="Credit limit (₹)"><input type="number" value={addFarmer.credit_limit} onChange={(e) => setAddFarmer({ ...addFarmer, credit_limit: e.target.value, credit_allowed: Number(e.target.value) > 0 })} /></Field>
          </div>
          <label className="row" style={{ gap: 8, cursor: "pointer" }}>
            <input type="checkbox" style={{ width: "auto" }} checked={addFarmer.credit_allowed} onChange={(e) => setAddFarmer({ ...addFarmer, credit_allowed: e.target.checked })} />
            Allow credit (khata) account
          </label>
        </Modal>
      )}

      {bills && customer && (
        <Modal title={`Previous bills — ${customer.name}`} onClose={() => setBills(null)} wide
          footer={<button className="btn btn-ghost" onClick={() => setBills(null)}>Close</button>}>
          {customer.village && <p className="muted" style={{ marginTop: 0 }}>{customer.village}{customer.phone ? ` · ${customer.phone}` : ""}</p>}
          {bills.length === 0 && (
            <p className="muted">No invoices in this ERP for this farmer. Opening khata can still show outstanding.</p>
          )}
          {bills.map((inv) => {
            const due = Math.max(0, Number(inv.grand_total) - Number(inv.amount_paid));
            return (
              <div key={inv.id} style={{ borderTop: "1px solid var(--border)", padding: "12px 0" }}>
                <div className="row" style={{ justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                  <span>
                    <strong>{inv.invoice_no || `#${inv.id}`}</strong>
                    <span className="muted" style={{ marginLeft: 8 }}>{inv.date} · {String(inv.payment_mode || "").replace("_", " ")}</span>
                  </span>
                  <span>
                    {inr(inv.grand_total)}
                    {due > 0 ? <span className="muted"> · due {inr(due)}</span> : <span className="muted"> · paid</span>}
                  </span>
                </div>
                <div className="table-wrap" style={{ marginTop: 8 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Item</th>
                        <th>Unit</th>
                        <th className="num">Qty</th>
                        <th className="num">Rate</th>
                        <th className="num">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(inv.items || []).map((it: any, i: number) => (
                        <tr key={`${inv.id}-${i}`}>
                          <td>{it.product_name}{Number(it.discount) > 0 ? <span className="muted"> · disc {inr(it.discount)}</span> : null}</td>
                          <td>{it.unit}</td>
                          <td className="num">{num(it.quantity)}</td>
                          <td className="num">{inr(it.unit_price)}</td>
                          <td className="num">{inr(it.line_total)}</td>
                        </tr>
                      ))}
                      {!(inv.items || []).length && (
                        <tr><td colSpan={5} className="muted">No line items stored on this bill</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </Modal>
      )}
    </div>
  );
}
