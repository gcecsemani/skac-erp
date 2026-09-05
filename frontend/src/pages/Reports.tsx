import { useEffect, useState } from "react";
import { api } from "../api";
import { inr } from "../format";
import { Card, ExportButtons, Loading, PageHeader, Table } from "../components/ui";

const REPORTS = [
  { key: "daily_sales", label: "Daily sales" },
  { key: "monthly_sales", label: "Monthly sales" },
  { key: "purchase", label: "Purchase" },
  { key: "product_sales", label: "Product sales" },
  { key: "category_sales", label: "Category sales" },
  { key: "profit_loss", label: "Profit & Loss" },
  { key: "inventory", label: "Inventory" },
  { key: "stock_movement", label: "Stock movement" },
  { key: "expiry", label: "Expiry" },
  { key: "low_stock", label: "Low stock" },
  { key: "customer_outstanding", label: "Customer outstanding" },
  { key: "supplier_outstanding", label: "Supplier outstanding" },
  { key: "gst", label: "GST" },
  { key: "payment_collection", label: "Payment collection" },
  { key: "vendor_stock", label: "Vendor stock" },
  { key: "field_visits", label: "Field visits" },
  { key: "product_profit", label: "Product profit" },
  { key: "product_loss", label: "Product loss" },
  { key: "farmer_profit", label: "Farmer profit" },
  { key: "farmer_loss", label: "Farmer loss" },
];

const monthStart = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
};
const today = () => new Date().toISOString().slice(0, 10);

export default function Reports() {
  const [key, setKey] = useState("daily_sales");
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState(0);
  const [start, setStart] = useState(monthStart);
  const [end, setEnd] = useState(today);
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => { api.branches().then(setBranches).catch(() => setBranches([])); }, []);

  const load = async (report = key) => {
    setBusy(true); setErr("");
    try {
      setData(await api.runReport(report, {
        branchId: branchId || undefined,
        start, end,
      }));
    } catch (e: any) {
      setData(null);
      setErr(e.message || "Could not load this report.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { load(key); }, [key, branchId, start, end]);

  const columns = (data?.columns || []).map((c: any) => ({
    key: c.key,
    label: c.label,
    num: !!c.num,
    render: c.money ? (r: any) => inr(r[c.key]) : undefined,
  }));
  const exportCols = (data?.columns || []).map((c: any) => ({
    key: c.key, label: c.label, num: !!c.num, money: !!c.money,
  }));
  const subtitle = data ? `${data.start} to ${data.end}` : "";

  return (
    <div>
      <PageHeader
        title="Reports"
        subtitle="Sales, stock, GST, outstanding and P&L — export to Excel or PDF"
        actions={data ? <ExportButtons title={data.title} subtitle={subtitle} columns={exportCols} rows={data.rows || []} /> : undefined}
      />

      <div className="report-nav">
        {REPORTS.map((r) => (
          <button key={r.key} className={key === r.key ? "on" : ""} onClick={() => setKey(r.key)}>{r.label}</button>
        ))}
      </div>

      <Card>
        <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
          <select value={branchId} onChange={(e) => setBranchId(Number(e.target.value))} style={{ width: "auto" }}>
            <option value={0}>All branches</option>
            {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ width: "auto" }} />
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ width: "auto" }} />
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
