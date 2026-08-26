import { useEffect, useState } from "react";
import { ShieldCheck, Search, AlertTriangle, PackageSearch } from "lucide-react";
import { api } from "../api";
import { num } from "../format";
import { Badge, Card, Field, Loading, PageHeader, Table } from "../components/ui";

export default function Compliance() {
  const [tab, setTab] = useState("licenses");
  const [licenses, setLicenses] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any>(null);
  const [ready, setReady] = useState(false);
  const [batch, setBatch] = useState("");
  const [trace, setTrace] = useState<any>(null);

  useEffect(() => {
    Promise.all([api.licenses().then(setLicenses), api.alerts().then(setAlerts)]).finally(() => setReady(true));
  }, []);

  const lookup = async () => { try { setTrace(await api.traceability(batch)); } catch { setTrace(null); } };
  if (!ready) return <Loading />;
  const tone = (s: string) => (s === "expired" ? "danger" : s === "expiring" ? "warn" : "success");

  return (
    <div>
      <PageHeader title="Compliance & Statutory" subtitle="License tracking, alerts and batch traceability for recalls" />
      <div className="tabs">
        {[["licenses", "Licenses"], ["alerts", "Alerts"], ["trace", "Batch Traceability"]].map(([k, l]) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>

      {tab === "licenses" && (
        <Card title="License Expiry Tracking" icon={<ShieldCheck size={16} />}>
          <Table
            columns={[
              { key: "branch", label: "Branch" },
              { key: "license_type", label: "License" },
              { key: "license_no", label: "Number" },
              { key: "valid_to", label: "Valid To", render: (r) => r.valid_to || "—" },
              { key: "days_to_expiry", label: "Days Left", num: true, render: (r) => r.days_to_expiry ?? "—" },
              { key: "status", label: "Status", render: (r) => <Badge tone={tone(r.status)}>{r.status}</Badge> },
            ]}
            rows={licenses}
            empty="No licenses recorded"
          />
        </Card>
      )}

      {tab === "alerts" && (
        <div className="grid grid-2">
          <Card title="Near Expiry (30 days)" icon={<AlertTriangle size={16} color="#d97706" />}>
            <Table columns={[
              { key: "product", label: "Product" }, { key: "batch_no", label: "Batch" },
              { key: "days_left", label: "Days", num: true, render: (r) => <Badge tone={r.days_left <= 15 ? "danger" : "warn"}>{r.days_left}</Badge> },
              { key: "quantity", label: "Qty", num: true, render: (r) => num(r.quantity) },
            ]} rows={alerts?.near_expiry || []} empty="Nothing near expiry" />
          </Card>
          <Card title="Low Stock" icon={<AlertTriangle size={16} color="#dc2626" />}>
            <Table columns={[
              { key: "product", label: "Product" },
              { key: "on_hand", label: "On hand", num: true, render: (r) => num(r.on_hand) },
              { key: "reorder_level", label: "Reorder", num: true, render: (r) => num(r.reorder_level) },
            ]} rows={alerts?.low_stock || []} empty="All stock healthy" />
          </Card>
        </div>
      )}

      {tab === "trace" && (
        <Card title="Batch Traceability" icon={<PackageSearch size={16} />}>
          <div className="row" style={{ alignItems: "flex-end", maxWidth: 360 }}>
            <div style={{ flex: 1 }}><Field label="Batch number"><input value={batch} onChange={(e) => setBatch(e.target.value)} placeholder="e.g. UREA-B1" /></Field></div>
            <button className="btn btn-primary" style={{ marginBottom: 14 }} onClick={lookup}><Search size={16} /> Trace</button>
          </div>
          {trace && (
            <Table
              columns={[
                { key: "invoice_no", label: "Invoice #" }, { key: "date", label: "Date" },
                { key: "customer_id", label: "Customer ID", render: (r) => r.customer_id ?? "Walk-in" },
                { key: "product", label: "Product" }, { key: "quantity", label: "Qty", num: true },
              ]}
              rows={trace.sales || []}
              empty="No sales found for this batch"
            />
          )}
        </Card>
      )}
    </div>
  );
}
