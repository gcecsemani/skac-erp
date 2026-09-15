import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { inr, localISODate } from "../format";
import { Card, ExportButtons, Loading, PageHeader, Table } from "../components/ui";

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
  { key: "gst", label: "GST", group: "accounts", needsDates: true,
    blurb: "Taxable value and tax by slab. Hand this to your CA for the return." },
  { key: "profit_loss", label: "Profit & loss", group: "accounts", needsDates: true,
    blurb: "Sales minus GST, product cost, and expenses. The number that says whether the shop made money." },
];

const monthStart = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
};
const today = () => localISODate();

export default function Reports() {
  const [group, setGroup] = useState("sales");
  const [key, setKey] = useState("daily_sales");
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState(0);
  const [start, setStart] = useState(monthStart);
  const [end, setEnd] = useState(today);
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const current = REPORTS.find((r) => r.key === key) || REPORTS[0];
  const inGroup = useMemo(() => REPORTS.filter((r) => r.group === group), [group]);

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
  };

  const columns = (data?.columns || []).map((c: any) => ({
    key: c.key,
    label: c.label,
    num: !!c.num,
    render: c.money ? (r: any) => inr(r[c.key]) : undefined,
  }));
  const exportCols = (data?.columns || []).map((c: any) => ({
    key: c.key, label: c.label, num: !!c.num, money: !!c.money,
  }));
  const subtitle = current.needsDates && data ? `${data.start} to ${data.end}` : "As of today";

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Fifteen reports that answer how the shops are doing — export any of them to Excel or PDF"
        actions={data ? <ExportButtons title={data.title} subtitle={subtitle} columns={exportCols} rows={data.rows || []} /> : undefined}
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
            <Table columns={columns} rows={data?.rows || []} empty="No rows for this period" pageSize={50} />
          </>
        )}
      </Card>
    </div>
  );
}
