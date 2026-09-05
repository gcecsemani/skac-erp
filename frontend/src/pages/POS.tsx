import { useEffect, useMemo, useRef, useState } from "react";
import { Search, Trash2, Wifi, WifiOff, RefreshCw, CreditCard, CheckCircle2, User, X, UserPlus, Star, Printer } from "lucide-react";
import { api } from "../api";
import { CATEGORY_COLORS, inr } from "../format";
import { printThermalReceipt } from "../print";
import { Card, PageHeader, Badge, Modal, Field, Switch } from "../components/ui";
import { LocationFields, PaymentSelect } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
import { getCachedCustomers, getCachedProducts, matchCustomer, pendingCount, queueInvoice, refreshCustomers, refreshProducts, syncOutbox, upsertCached } from "../offline";
import { getOpenPrintDialog, setOpenPrintDialog } from "../printPref";
import * as V from "../validate";

const emptyFarmer = { name: "", phone: "", aadhaar_no: "", village: "", district: "", credit_allowed: false, credit_limit: "" };
const POS_TILE_CAP = 80;
const FARMER_PICK_CAP = 12;

const r2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

interface Line { product_id: number; name: string; quantity: number; unit_price: number; gst_rate: number; discount: number; }

export default function POS() {
  const { bundle, ready } = useConfigBundle();
  const [products, setProducts] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState<number>(0);
  const [lines, setLines] = useState<Line[]>([]);
  const [search, setSearch] = useState("");
  const [payment, setPayment] = useState("cash");
  const [online, setOnline] = useState(navigator.onLine);
  const [pending, setPending] = useState(0);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);

  const [farmerBook, setFarmerBook] = useState<any[]>([]);
  const [customer, setCustomer] = useState<any | null>(null);
  const [custQuery, setCustQuery] = useState("");
  const [custOpen, setCustOpen] = useState(false);
  const [addFarmer, setAddFarmer] = useState<any | null>(null);
  const [farmerErr, setFarmerErr] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshingFarmers, setRefreshingFarmers] = useState(false);
  const farmerBox = useRef<HTMLDivElement>(null);

  const [discMode, setDiscMode] = useState<"inr" | "pct">("inr");
  const [billDiscount, setBillDiscount] = useState("");
  const [amountPaid, setAmountPaid] = useState("0");
  const [lastInv, setLastInv] = useState<any | null>(null);
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
    api.branches().then((b) => { setBranches(b); if (b[0]) setBranchId(b[0].id); }).catch(() => {});
    getCachedProducts().then((cached) => { if (cached.length) setProducts(cached); }).catch(() => {});
    getCachedCustomers().then((cached) => { if (cached.length) setFarmerBook(cached); }).catch(() => {});
    refreshCustomers().then(setFarmerBook).catch(() => {});
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

  const farmerHits = useMemo(() => {
    const q = custQuery.trim();
    if (!q) return [];
    return farmerBook.filter((c) => matchCustomer(c, q)).slice(0, FARMER_PICK_CAP);
  }, [farmerBook, custQuery]);

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
      setFarmerBook(await refreshCustomers());
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
  const unitOf = (p: any) => p.base_unit || "units";

  const add = (p: any) => {
    const stock = stockOf(p);
    const inCart = lines.find((l) => l.product_id === p.id)?.quantity || 0;
    if (stock != null && stock <= 0) {
      setMsg({ text: `${p.name} is out of stock at this branch. Receive stock before billing it.`, ok: false });
      return;
    }
    if (stock != null && inCart + 1 > stock) {
      setMsg({ text: `Only ${stock} ${unitOf(p)} of ${p.name} left. You already have ${inCart} on this bill.`, ok: false });
      return;
    }
    setMsg(null);
    setLines((cur) => {
      const ex = cur.find((l) => l.product_id === p.id);
      if (ex) return cur.map((l) => l.product_id === p.id ? { ...l, quantity: l.quantity + 1 } : l);
      return [...cur, { product_id: p.id, name: p.name, quantity: 1, unit_price: Number(p.sale_price), gst_rate: Number(p.gst_rate), discount: 0 }];
    });
  };
  const setQty = (id: number, q: number) => setLines((cur) => cur.map((l) => {
    if (l.product_id !== id) return l;
    const p = products.find((x) => x.id === id);
    const stock = p ? stockOf(p) : null;
    const next = Math.max(1, q);
    if (stock != null && next > stock) {
      setMsg({ text: `Only ${stock} ${p ? unitOf(p) : "units"} of ${l.name} available at this branch.`, ok: false });
      return { ...l, quantity: Math.max(1, stock) };
    }
    return { ...l, quantity: next };
  }));
  const setLineDisc = (id: number, d: number) => setLines((cur) => cur.map((l) => {
    if (l.product_id !== id) return l;
    const cap = r2(l.quantity * l.unit_price);
    return { ...l, discount: Math.min(Math.max(0, d), cap) };
  }));
  const remove = (id: number) => setLines((cur) => cur.filter((l) => l.product_id !== id));

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

  useEffect(() => {
    if (payment === "credit") setAmountPaid("0");
    else setAmountPaid(String(totals.grand));
  }, [payment, totals.grand]);

  const paid = Math.min(Math.max(Number(amountPaid) || 0, 0), totals.grand);
  const due = r2(totals.grand - paid);
  const projectedKhata = Number(customer?.outstanding_balance || 0) + due;
  const overLimit = !!customer && Number(customer.credit_limit) > 0 && projectedKhata > Number(customer.credit_limit);

  const selectCustomer = (c: any | null) => {
    setCustomer(c); setCustQuery(c ? c.name : ""); setCustOpen(false);
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

  const setPayMode = (mode: string) => setPayment(mode);

  const checkout = async () => {
    if (lines.length === 0) {
      setMsg({ text: "Add at least one product before finalizing.", ok: false });
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
    const payload = {
      branch_id: branchId,
      customer_id: customer?.id ?? null,
      payment_mode: paid === 0 ? "credit" : payment === "credit" ? "cash" : payment,
      amount_paid: r2(paid),
      lines: totals.lines.map((l) => ({
        product_id: l.product_id,
        quantity: l.quantity,
        unit_price: l.unit_price,
        discount: l.discount,
      })),
    };
    try {
      if (online) {
        const inv = await api.createInvoice(payload);
        const bal = r2(Number(inv.grand_total) - Number(inv.amount_paid));
        setLastInv(inv);
        setMsg({
          text: bal > 0
            ? `Invoice ${inv.invoice_no} · paid ${inr(inv.amount_paid)} · balance ${inr(bal)} on khata`
            : `Invoice ${inv.invoice_no} finalized — ${inr(inv.grand_total)} paid`,
          ok: true,
        });
        if (openPrint) printThermalReceipt(inv);
      } else {
        await queueInvoice(payload); setPending(await pendingCount());
        setMsg({ text: "Saved offline — will sync when back online.", ok: true });
      }
      setLines([]); selectCustomer(null); setBillDiscount(""); setDiscMode("inr"); setPayment("cash");
      setProducts((cur) => cur.map((p) => {
        const sold = payload.lines.find((l) => l.product_id === p.id);
        if (!sold || p.stock_qty == null) return p;
        const next = { ...p, stock_qty: Math.max(0, Number(p.stock_qty) - Number(sold.quantity)) };
        upsertCached("products", next);
        return next;
      }));
      if (customer && due > 0) {
        const next = { ...customer, outstanding_balance: Number(customer.outstanding_balance || 0) + due };
        upsertCached("customers", next);
        setFarmerBook((cur) => cur.map((x) => x.id === next.id ? next : x));
      }
      loadProducts(branchId);
      refreshCustomers().then(setFarmerBook).catch(() => {});
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
        subtitle="Fast keyboard-first counter billing with offline resilience"
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
              const out = stock != null && stock <= 0;
              const low = stock != null && stock > 0 && stock <= Number(p.reorder_level || 0);
              return (
              <div key={p.id} className="product-tile-wrap">
                <button type="button" className={`fav-star ${p.is_favorite ? "on" : ""}`} title={p.is_favorite ? "Unpin favorite" : "Pin as favorite"}
                  onClick={() => toggleFav(p)}>
                  <Star size={14} fill={p.is_favorite ? "currentColor" : "none"} />
                </button>
                <button className={`product-tile ${p.is_favorite ? "fav" : ""} ${out ? "out" : ""}`} onClick={() => add(p)} disabled={out}>
                  <span className="cat-dot" style={{ background: CATEGORY_COLORS[p.category] || "#64748b" }} />
                  <span className="p-name">{p.name}</span>
                  <span className="p-price">{inr(p.sale_price)}</span>
                  <span className={`p-stock ${out ? "out" : low ? "low" : "ok"}`}>
                    {out ? "Out of stock" : stock == null ? "Stock: —" : `Stock: ${stock} ${p.base_unit || ""}`}
                  </span>
                  <span className="muted" style={{ fontSize: 11, textTransform: "capitalize" }}>{p.category} · {p.gst_rate}% GST</span>
                </button>
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
              <thead><tr><th>Item</th><th className="num">Qty</th><th className="num">Price</th><th className="num">Disc ₹</th><th className="num">Total</th><th></th></tr></thead>
              <tbody>
                {lines.length === 0 && <tr><td colSpan={6} className="muted" style={{ textAlign: "center", padding: 24 }}>Tap products to add</td></tr>}
                {lines.map((l) => {
                  const priced = totals.lines.find((x) => x.product_id === l.product_id);
                  return (
                    <tr key={l.product_id}>
                      <td>{l.name}</td>
                      <td className="num"><input type="number" min={1} value={l.quantity} onChange={(e) => setQty(l.product_id, Number(e.target.value))} style={{ width: 56, padding: 6, textAlign: "right" }} /></td>
                      <td className="num">{inr(l.unit_price)}</td>
                      <td className="num"><input type="number" min={0} step="0.01" value={l.discount || ""} placeholder="0" onChange={(e) => setLineDisc(l.product_id, Number(e.target.value))} style={{ width: 64, padding: 6, textAlign: "right" }} /></td>
                      <td className="num">{inr(priced?.lineTotal ?? l.quantity * l.unit_price)}</td>
                      <td><button className="icon-btn" style={{ width: 30, height: 30 }} onClick={() => remove(l.product_id)}><Trash2 size={14} /></button></td>
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
          {totals.discountTotal > 0 && <div className="totals-row"><span>Total discount</span><span>− {inr(totals.discountTotal)}</span></div>}
          <div className="totals-row"><span>Taxable</span><span>{inr(totals.sub)}</span></div>
          <div className="totals-row"><span>GST</span><span>{inr(totals.tax)}</span></div>
          <div className="totals-grand"><span>Total</span><span>{inr(totals.grand)}</span></div>

          <div className="field mt-8">
            <label>Farmer {due > 0 ? "(required — unpaid balance goes to khata)" : "(optional — walk-in if empty)"}</label>
            {customer ? (
              <div className="row" style={{ justifyContent: "space-between", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", padding: "8px 10px" }}>
                <span className="row" style={{ gap: 8 }}>
                  <User size={15} color="var(--brand-600)" />
                  <span style={{ fontWeight: 600 }}>{customer.name}</span>
                  {customer.village && <span className="muted" style={{ fontSize: 12 }}>· {customer.village}</span>}
                  {customer.credit_allowed && <Badge tone="info">Khata: {inr(customer.outstanding_balance)}</Badge>}
                </span>
                <button className="icon-btn" style={{ width: 30, height: 30 }} onClick={() => selectCustomer(null)}><X size={14} /></button>
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
                        </span>
                        {c.credit_allowed && <Badge tone="info">Khata {inr(c.outstanding_balance)}</Badge>}
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
            <label>Payment mode</label>
            <PaymentSelect value={payment} onChange={setPayMode} use="pos" bundle={bundle} />
          </div>
          <div className="field">
            <label>Amount received now</label>
            <div className="row" style={{ gap: 8 }}>
              <input type="number" min={0} step="0.01" value={amountPaid} onChange={(e) => setAmountPaid(e.target.value)} />
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setPayment("cash"); setAmountPaid(String(totals.grand)); }}>Full</button>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setPayment("credit"); setAmountPaid("0"); }}>None</button>
            </div>
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
          <button className="btn btn-primary btn-block" disabled={lines.length === 0 || !branchId} onClick={checkout} style={{ marginTop: 12 }}>
            <CheckCircle2 size={18} /> Finalize Invoice
          </button>
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
    </div>
  );
}
