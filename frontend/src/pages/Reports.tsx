import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { inr, localISODate, matchesQuery, monthStartISO, num, todayISO } from "../format";
import { Badge, Card, ExportButtons, Field, Loading, Modal, PageHeader, SearchInput, Table } from "../components/ui";
import * as V from "../validate";

type ReportDef = {
  key: string;
  label: string;
  group: string;
  needsDates: boolean;
  blurb: string;
};

const GROUPS = [
  { id: "sales", label: "Sales & margin" },
  { id: "collections", label: "Cash & khata" },
  { id: "buying", label: "Buying" },
  { id: "stock", label: "Stock" },
  { id: "accounts", label: "GST & P&L" },
];

const REPORTS: ReportDef[] = [
  { key: "daily_sales", label: "Sales by day", group: "sales", needsDates: true,
    blurb: "Bills, cash collected, and new khata each day. Use this to check a counter or a slow week." },
  { key: "monthly_sales", label: "Sales by month", group: "sales", needsDates: true,
    blurb: "Month-on-month sales. Fertilizer peaks around season — this shows whether this year is ahead or behind." },
  { key: "product_sales", label: "What sold", group: "sales", needsDates: true,
    blurb: "Which SKUs brought money. Push the winners; stop filling shelves with items nobody buys." },
  { key: "product_profit", label: "Product margin", group: "sales", needsDates: true,
    blurb: "Profit after cost, per product. High sales with thin or negative margin is a problem, not a win." },
  { key: "farmer_profit", label: "Top farmers", group: "sales", needsDates: true,
    blurb: "Who buys from you and how much margin those bills leave. Your best farmers to keep close." },
  { key: "customer_outstanding", label: "Khata outstanding", group: "collections", needsDates: false,
    blurb: "Everyone who still owes the shop. Call the top of this list first." },
  { key: "inactive_khata", label: "Khata not visiting", group: "collections", needsDates: false,
    blurb: "Farmers who owe money and have not billed in 30 days. These balances go stale unless you follow up." },
  { key: "payment_collection", label: "Money collected", group: "collections", needsDates: true,
    blurb: "Cash, UPI and khata receipts in the period. Match this to day close and the bank." },
  { key: "purchase", label: "Purchases", group: "buying", needsDates: true,
    blurb: "Goods received from suppliers. Check what came in versus what is selling." },
  { key: "supplier_outstanding", label: "Supplier payables", group: "buying", needsDates: false,
    blurb: "What the shop still owes vendors. Pay these before credit is blocked." },
  { key: "inventory", label: "Stock on hand", group: "stock", needsDates: false,
    blurb: "Quantity and rupee value sitting in each shop. Capital locked in bags and bottles." },
  { key: "expiry", label: "Expiry risk", group: "stock", needsDates: false,
    blurb: "Batches expiring in 60 days. Sell, return, or write off before they become unsaleable." },
  { key: "low_stock", label: "Reorder", group: "stock", needsDates: false,
    blurb: "Out of stock or below reorder level. These are lost sales if a farmer walks in tomorrow." },
  { key: "stock_reconcile", label: "Stock reconciliation", group: "stock", needsDates: true,
    blurb: "Opening + loaded − sold − returns − transfers should equal stock left. Log a shelf count when it does not, and keep the case open until you find the bags." },
  { key: "gst", label: "GST", group: "accounts", needsDates: true,
    blurb: "Taxable value and tax by slab. Hand this to your CA for the return." },
  { key: "profit_loss", label: "Profit & loss", group: "accounts", needsDates: true,
    blurb: "Sales minus GST, product cost, and expenses. The number that says whether the shop made money." },
];

function reportFromQuery() {
  const r = new URLSearchParams(window.location.search).get("report");
  const found = REPORTS.find((x) => x.key === r);
  return found ? { group: found.group, key: found.key } : { group: "sales", key: "daily_sales" };
}


const QTY_KEYS = new Set([
  "opening", "loaded", "sold", "sale_return", "purchase_return",
  "transfer_in", "transfer_out", "adjustment", "expected", "left",
  "ledger_gap", "counted", "gap",
]);

function qtyCell(v: any) {
  if (v === null || v === undefined || v === "") return "—";
  return num(v);
}

function gapTone(v: any): "success" | "danger" | "neutral" {
  const n = Number(v);
  if (!Number.isFinite(n) || n === 0) return "neutral";
  return n < 0 ? "danger" : "success";
}

function caseTone(s: string): "danger" | "warn" | "success" | "neutral" {
  if (s === "open") return "danger";
  if (s === "investigating") return "warn";
  if (s === "resolved") return "success";
  return "neutral";
}

export default function Reports() {
  const initial = reportFromQuery();
  const [group, setGroup] = useState(initial.group);
  const [key, setKey] = useState(initial.key);
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState(0);
  const [start, setStart] = useState(monthStartISO);
  const [end, setEnd] = useState(todayISO);
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("all");
  const [view, setView] = useState("all");
  const [countRow, setCountRow] = useState<any | null>(null);
  const [countForm, setCountForm] = useState({ counted: "", note: "" });
  const [countErr, setCountErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [resolveRow, setResolveRow] = useState<any | null>(null);
  const [resolution, setResolution] = useState("");
  const [resolveErr, setResolveErr] = useState("");
  const [traceRow, setTraceRow] = useState<any | null>(null);
  const [trail, setTrail] = useState<any | null>(null);
  const [trailBusy, setTrailBusy] = useState(false);

  const current = REPORTS.find((r) => r.key === key) || REPORTS[0];
  const inGroup = useMemo(() => REPORTS.filter((r) => r.group === group), [group]);
  const isRecon = key === "stock_reconcile";

  const reload = () => api.runReport(key, {
    branchId: branchId || undefined, start, end,
  }).then(setData);

  useEffect(() => { api.branches().then(setBranches).catch(() => setBranches([])); }, []);

  useEffect(() => {
    const ac = new AbortController();
    setBusy(true); setErr("");
    api.runReport(key, {
      branchId: branchId || undefined,
      start, end,
      signal: ac.signal,
    }).then(setData).catch((e) => {
      if (e?.name === "AbortError") return;
      setData(null);
      setErr(e.message || "Could not load this report.");
    }).finally(() => setBusy(false));
    return () => ac.abort();
  }, [key, branchId, start, end]);

  const pickGroup = (id: string) => {
    setGroup(id);
    const first = REPORTS.find((r) => r.group === id);
    if (first) setKey(first.key);
    setQ(""); setCategory("all"); setView("all");
  };

  const rows = useMemo(() => {
    const src = data?.rows || [];
    if (!isRecon) return src;
    return src.filter((r: any) => {
      if (category !== "all" && String(r.category || "").toLowerCase() !== category) return false;
      if (!matchesQuery(q, r.product, r.sku, r.branch, r.case_note)) return false;
      const ledger = Math.abs(Number(r.ledger_gap) || 0) >= 0.001;
      const countGap = r.gap != null && Math.abs(Number(r.gap)) >= 0.001;
      const open = r.case_status === "open" || r.case_status === "investigating";
      if (view === "mismatches") return ledger || countGap || open;
      if (view === "open") return open;
      if (view === "short") return Number(r.gap) < 0 || (r.gap == null && Number(r.ledger_gap) < 0);
      return true;
    });
  }, [data, isRecon, q, category, view]);

  const columns = (data?.columns || []).map((c: any) => {
    const col: any = { key: c.key, label: c.label, num: !!c.num };
    if (c.money) col.render = (r: any) => inr(r[c.key]);
    else if (c.key === "ledger_gap" || c.key === "gap") {
      col.render = (r: any) => {
        const v = r[c.key];
        if (v === null || v === undefined) return "—";
        return <Badge tone={gapTone(v)}>{num(v)}</Badge>;
      };
    } else if (c.key === "case_status") {
      col.render = (r: any) => <Badge tone={caseTone(r.case_status)}>{r.case_status || "—"}</Badge>;
    } else if (QTY_KEYS.has(c.key)) {
      col.render = (r: any) => qtyCell(r[c.key]);
    }
    return col;
  });
  if (isRecon) {
    columns.push({
      key: "actions",
      label: "",
      render: (r: any) => (
        <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
          <button className="btn btn-ghost btn-sm" onClick={() => {
            setCountErr("");
            setCountRow(r);
            setCountForm({ counted: r.counted != null ? String(r.counted) : String(r.on_hand_now ?? r.left ?? ""), note: r.case_note && r.case_note !== "—" ? r.case_note : "" });
          }}>Log count</button>
          <button className="btn btn-ghost btn-sm" onClick={async () => {
            setTraceRow(r);
            setTrail(null);
            setTrailBusy(true);
            try {
              if (r.case_id && r.case_status === "open") {
                await api.investigateStockCase(r.case_id);
                reload();
              }
              setTrail(await api.stockTrail(r.product_id, r.branch_id, start, end));
            } catch (e: any) { setErr(e.message); setTraceRow(null); }
            finally { setTrailBusy(false); }
          }}>Trace</button>
          {r.case_id && r.case_status !== "resolved" && (
            <button className="btn btn-ghost btn-sm" onClick={() => { setResolveRow(r); setResolution(""); setResolveErr(""); }}>Resolve</button>
          )}
        </div>
      ),
    });
  }
  const exportCols = (data?.columns || []).map((c: any) => ({
    key: c.key, label: c.label, num: !!c.num, money: !!c.money,
  }));
  const subtitle = current.needsDates && data ? `${data.start} to ${data.end}` : "As of today";

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle={`${REPORTS.length} reports that answer how the shops are doing — export any of them to Excel or PDF`}
        actions={data ? <ExportButtons title={data.title} subtitle={subtitle} columns={exportCols} rows={rows} /> : undefined}
      />

      <div className="tabs">
        {GROUPS.map((g) => (
          <button key={g.id} className={`tab ${group === g.id ? "active" : ""}`} onClick={() => pickGroup(g.id)}>
            {g.label}
          </button>
        ))}
      </div>

      <div className="report-nav">
        {inGroup.map((r) => (
          <button key={r.key} className={key === r.key ? "on" : ""} onClick={() => setKey(r.key)}>{r.label}</button>
        ))}
      </div>

      <p className="muted" style={{ marginTop: -8, marginBottom: 16, maxWidth: 720 }}>{current.blurb}</p>

      <Card>
        <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10, alignItems: "center" }}>
          <select value={branchId} onChange={(e) => setBranchId(Number(e.target.value))} style={{ width: "auto" }}>
            <option value={0}>All branches</option>
            {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          {current.needsDates ? (
            <>
              <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ width: "auto" }} />
              <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ width: "auto" }} />
            </>
          ) : (
            <span className="muted" style={{ fontSize: 13 }}>Snapshot as of today — date range does not apply</span>
          )}
          {isRecon && (
            <>
              <SearchInput value={q} onChange={setQ} placeholder="Search product / SKU…" />
              <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ width: "auto" }}>
                <option value="all">All categories</option>
                <option value="fertilizer">Fertilizer</option>
                <option value="pesticide">Pesticide</option>
                <option value="seed">Seed</option>
              </select>
              <select value={view} onChange={(e) => setView(e.target.value)} style={{ width: "auto" }}>
                <option value="all">All activity</option>
                <option value="mismatches">Mismatches only</option>
                <option value="open">Open cases</option>
                <option value="short">Counted short</option>
              </select>
            </>
          )}
        </div>
        {err && <div className="error">{err}</div>}
        {busy && !data ? <Loading /> : (
          <>
            {data?.summary?.length > 0 && (
              <div className="row mb-16" style={{ flexWrap: "wrap", gap: 18 }}>
                {data.summary.map((s: any) => (
                  <div key={s.label}>
                    <div className="muted" style={{ fontSize: 12 }}>{s.label}</div>
                    <strong>{s.money ? inr(s.value) : s.value}</strong>
                  </div>
                ))}
              </div>
            )}
            <Table columns={columns} rows={rows} empty="No rows for this period" pageSize={50} />
          </>
        )}
      </Card>

      {countRow && (
        <Modal title="Log shelf count" onClose={() => setCountRow(null)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setCountRow(null)} disabled={saving}>Cancel</button>
            <button className="btn btn-primary" disabled={saving} onClick={async () => {
              setCountErr("");
              const msg = V.firstError(
                V.nonNegative(countForm.counted, "Counted qty"),
                V.minLen(countForm.note, "Note", 3),
              );
              if (msg) { setCountErr(msg); return; }
              setSaving(true);
              try {
                await api.logStockCount({
                  branch_id: countRow.branch_id,
                  product_id: countRow.product_id,
                  counted_qty: Number(countForm.counted),
                  note: countForm.note.trim(),
                  count_date: localISODate(),
                });
                setCountRow(null);
                await reload();
              } catch (e: any) { setCountErr(e.message); }
              finally { setSaving(false); }
            }}>{saving ? "Saving…" : "Save count"}</button>
          </>}>
          {countErr && <div className="error">{countErr}</div>}
          <p className="muted" style={{ marginTop: 0 }}>
            {countRow.product} · {countRow.branch} · book on hand now <strong>{num(countRow.on_hand_now)}</strong>
          </p>
          <p className="muted" style={{ fontSize: 12 }}>
            Count the bags on the shelf. If this is short of book, a case stays open until you find the movement (bill, transfer, return) or write the reason and resolve it.
          </p>
          <div className="grid grid-2">
            <Field label="Counted qty (packs)" required>
              <input type="number" min={0} step="0.001" value={countForm.counted}
                onChange={(e) => setCountForm({ ...countForm, counted: e.target.value })} />
            </Field>
            <Field label="What looks wrong" required>
              <input value={countForm.note} onChange={(e) => setCountForm({ ...countForm, note: e.target.value })}
                placeholder="Short 3 bags vs book / found extra" />
            </Field>
          </div>
        </Modal>
      )}

      {resolveRow && (
        <Modal title="Resolve stock case" onClose={() => setResolveRow(null)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setResolveRow(null)} disabled={saving}>Cancel</button>
            <button className="btn btn-primary" disabled={saving} onClick={async () => {
              setResolveErr("");
              const msg = V.minLen(resolution, "Resolution", 3);
              if (msg) { setResolveErr(msg); return; }
              setSaving(true);
              try {
                await api.resolveStockCase(resolveRow.case_id, resolution.trim());
                setResolveRow(null);
                await reload();
              } catch (e: any) { setResolveErr(e.message); }
              finally { setSaving(false); }
            }}>{saving ? "Saving…" : "Close case"}</button>
          </>}>
          {resolveErr && <div className="error">{resolveErr}</div>}
          <p className="muted" style={{ marginTop: 0 }}>
            {resolveRow.product} · gap {num(resolveRow.gap)} · {resolveRow.case_note}
          </p>
          <Field label="How it was found / fixed" required>
            <input value={resolution} onChange={(e) => setResolution(e.target.value)}
              placeholder="Found in godown / billed on wrong SKU / shrinkage" />
          </Field>
        </Modal>
      )}

      {traceRow && (
        <Modal title={`Trace · ${traceRow.product}`} onClose={() => { setTraceRow(null); setTrail(null); }} wide>
          {trailBusy && !trail ? <Loading /> : (
            <>
              <p className="muted" style={{ marginTop: 0 }}>
                {traceRow.branch} · {trail?.start} to {trail?.end} · opening {num(trail?.opening)} → book left {num(trail?.closing)} · on hand now {num(trail?.on_hand_now)}
              </p>
              {traceRow.case_note && traceRow.case_note !== "—" && (
                <p className="muted" style={{ fontSize: 12 }}>Case note: {traceRow.case_note}</p>
              )}
              <Table
                columns={[
                  { key: "when", label: "When" },
                  { key: "type", label: "Type" },
                  { key: "batch", label: "Batch" },
                  { key: "qty", label: "Qty", num: true, render: (r: any) => num(r.qty) },
                  { key: "running", label: "Running", num: true, render: (r: any) => num(r.running) },
                  { key: "note", label: "Note" },
                ]}
                rows={trail?.rows || []}
                empty="No movements in this period — the gap is before this range or never entered the ledger"
                pageSize={30}
              />
            </>
          )}
        </Modal>
      )}
    </div>
  );
}
