import { useEffect, useState } from "react";
import { Eye, Printer, Search } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { inr } from "../format";
import { printThermalReceipt } from "../print";
import { Badge, Card, ExportButtons, Loading, Modal, PageHeader, Table, BranchSelect } from "../components/ui";
import { PaymentSelect } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
import { useAuth } from "../auth";
import { seesAllBranches } from "../roles";

const monthStart = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
};
const today = () => new Date().toISOString().slice(0, 10);

export default function Invoices() {
  const { user } = useAuth();
  const { bundle } = useConfigBundle();
  const allBranches = seesAllBranches(user);
  const [rows, setRows] = useState<any[] | null>(null);
  const [sel, setSel] = useState<any>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState<number>(0);
  const [start, setStart] = useState(monthStart);
  const [end, setEnd] = useState(today);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [unpaidOnly, setUnpaidOnly] = useState(false);
  const [paymentMode, setPaymentMode] = useState("");
  const [limit, setLimit] = useState(50);

  const load = () => {
    setRows(null);
    api.invoices({
      branchId: branchId || undefined,
      start, end,
      search: q.trim() || undefined,
      unpaidOnly: unpaidOnly || undefined,
      paymentMode: paymentMode || undefined,
      limit,
    }).then(setRows).catch(() => setRows([]));
  };

  useEffect(() => {
    api.branches().then((b) => {
      setBranches(b);
      if (!allBranches && b[0]) setBranchId(b[0].id);
    }).catch(() => setBranches([]));
  }, []);
  useEffect(() => { load(); }, [branchId, start, end, q, unpaidOnly, paymentMode, limit]);

  if (!rows) return <Loading />;

  const statusTone = (s: string) => (s === "finalized" ? "success" : s === "cancelled" ? "danger" : "neutral");

  return (
    <div>
      <PageHeader
        title="Invoices"
        subtitle="Finalized GST tax invoices — view only. Corrections go through Sales Returns."
        actions={<ExportButtons title="Invoices" columns={[
          { key: "invoice_no", label: "Invoice #" }, { key: "invoice_date", label: "Date" },
          { key: "branch_name", label: "Branch" },           { key: "customer_name", label: "Farmer" },
          { key: "customer_village", label: "Village" }, { key: "customer_phone", label: "Phone" },
          { key: "payment_mode", label: "Payment" },
          { key: "grand_total", label: "Total", num: true, money: true },
          { key: "amount_paid", label: "Paid", num: true, money: true },
        ]} rows={(rows || []).map((r) => ({ ...r, customer_name: r.customer_name || "Walk-in" }))} />}
      />
      <p className="muted" style={{ marginTop: -8, marginBottom: 14, fontSize: 13 }}>
        GST invoices are locked after finalization (no edit/delete). To reverse a bill, raise a credit note on{" "}
        <Link to="/returns">Sales Returns</Link>.
      </p>
      <Card>
        <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
          <div style={{ position: "relative", flex: "1 1 220px", minWidth: 180 }}>
            <Search size={16} style={{ position: "absolute", left: 10, top: 11, color: "#94a3b8" }} />
            <input placeholder="Invoice # or farmer…" value={search} onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") setQ(search); }} style={{ paddingLeft: 32 }} />
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => setQ(search)}>Search</button>
          <BranchSelect value={branchId} onChange={setBranchId} branches={branches} allowAll={allBranches} />
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ width: "auto" }} />
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ width: "auto" }} />
          <PaymentSelect
            value={paymentMode}
            onChange={setPaymentMode}
            use="invoice_filter"
            bundle={bundle}
            allowEmpty
            style={{ width: "auto" }}
          />
          <label className="row" style={{ gap: 6, cursor: "pointer", width: "auto" }}>
            <input type="checkbox" style={{ width: "auto" }} checked={unpaidOnly} onChange={(e) => setUnpaidOnly(e.target.checked)} />
            Unpaid only
          </label>
          <select value={limit} onChange={(e) => setLimit(Number(e.target.value))} style={{ width: "auto" }} title="How many invoices to load from the server">
            <option value={25}>Load 25</option>
            <option value={50}>Load 50</option>
            <option value={100}>Load 100</option>
            <option value={200}>Load 200</option>
            <option value={500}>Load 500</option>
            <option value={1000}>Load 1000</option>
          </select>
        </div>
        <Table
          columns={[
            { key: "invoice_no", label: "Invoice #" },
            { key: "invoice_date", label: "Date" },
            { key: "branch_name", label: "Branch", render: (r) => r.branch_name || "—" },
            { key: "customer_name", label: "Farmer", render: (r) => r.customer_name || <span className="muted">Walk-in</span> },
            { key: "customer_village", label: "Village", render: (r) => r.customer_village || "—" },
            { key: "customer_phone", label: "Phone", render: (r) => r.customer_phone || "—" },
            { key: "payment_mode", label: "Payment", render: (r) => <span style={{ textTransform: "capitalize" }}>{r.payment_mode}</span> },
            { key: "status", label: "Status", render: (r) => <Badge tone={statusTone(r.status)}>{r.status}</Badge> },
            { key: "discount_total", label: "Discount", num: true, render: (r) => Number(r.discount_total) > 0 ? inr(r.discount_total) : "—" },
            { key: "grand_total", label: "Total", num: true, render: (r) => <strong>{inr(r.grand_total)}</strong> },
            { key: "amount_paid", label: "Paid", num: true, render: (r) => inr(r.amount_paid) },
            { key: "balance", label: "Balance", num: true, render: (r) => {
              const due = Number(r.grand_total) - Number(r.amount_paid);
              return due > 0 ? <strong style={{ color: "var(--danger)" }}>{inr(due)}</strong> : <Badge tone="success">Paid</Badge>;
            }},
            { key: "view", label: "", render: (r) => (
              <div className="row" style={{ gap: 4, justifyContent: "flex-end" }}>
                <button className="btn btn-ghost btn-sm" title="Print" onClick={() => printThermalReceipt(r)}><Printer size={15} /></button>
                <button className="btn btn-ghost btn-sm" onClick={() => setSel(r)}><Eye size={15} /></button>
              </div>
            ) },
          ]}
          rows={rows}
          empty="No invoices in this period"
          pageSize={50}
        />
      </Card>

      {sel && (
        <Modal title={`Invoice ${sel.invoice_no}`} onClose={() => setSel(null)} wide
          footer={<button className="btn btn-primary" onClick={() => printThermalReceipt(sel)}><Printer size={16} /> Print receipt</button>}>
          <div className="row mb-16" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div><div className="muted">Date</div><strong>{sel.invoice_date}</strong></div>
            <div><div className="muted">Branch</div><strong>{sel.branch_name || "—"}</strong></div>
            <div><div className="muted">Farmer</div><strong>{sel.customer_name || "Walk-in"}</strong>
              {(sel.customer_village || sel.customer_phone) && (
                <div className="muted" style={{ fontSize: 12 }}>{[sel.customer_village, sel.customer_phone].filter(Boolean).join(" · ")}</div>
              )}
            </div>
            <div><div className="muted">Payment</div><strong style={{ textTransform: "capitalize" }}>{sel.payment_mode}</strong></div>
            <div><div className="muted">Discount</div><strong>{inr(sel.discount_total)}</strong></div>
            <div><div className="muted">Total</div><strong>{inr(sel.grand_total)}</strong></div>
            <div><div className="muted">Paid</div><strong>{inr(sel.amount_paid)}</strong></div>
            <div><div className="muted">Balance</div><strong style={{ color: Number(sel.grand_total) - Number(sel.amount_paid) > 0 ? "var(--danger)" : "inherit" }}>{inr(Number(sel.grand_total) - Number(sel.amount_paid))}</strong></div>
          </div>
          <Table
            columns={[
              { key: "product_name", label: "Product" },
              { key: "batch_no", label: "Batch" },
              { key: "expiry_date", label: "Expiry" },
              { key: "quantity", label: "Qty", num: true },
              { key: "unit_price", label: "Rate", num: true, render: (r) => inr(r.unit_price) },
              { key: "discount", label: "Disc", num: true, render: (r) => Number(r.discount) > 0 ? inr(r.discount) : "—" },
              { key: "line_total", label: "Total", num: true, render: (r) => inr(r.line_total) },
            ]}
            rows={sel.items || []}
          />
        </Modal>
      )}
    </div>
  );
}
