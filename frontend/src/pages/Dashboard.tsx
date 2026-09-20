import { lazy, Suspense, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { IndianRupee, TrendingUp, Wallet, CalendarClock, AlertTriangle, Receipt, Landmark, Banknote } from "lucide-react";
import { api } from "../api";
import { inr } from "../format";
import { Card, Loading, PageHeader, StatCard, Table, Badge } from "../components/ui";

// Charts live in their own chunk so the stat cards and the alerts panel paint
// without waiting on recharts.
const DashboardCharts = lazy(() =>
  import("./DashboardCharts").then((m) => ({ default: m.DashboardCharts }))
);
const PaymentMix = lazy(() =>
  import("./DashboardCharts").then((m) => ({ default: m.PaymentMix }))
);

const ChartSkeleton = ({ height }: { height: number }) => (
  <div className="empty" style={{ height, display: "grid", placeItems: "center" }}>Loading chart…</div>
);

const PERIODS = [
  { id: "today", label: "Today" },
  { id: "7d", label: "Last 7 days" },
  { id: "mtd", label: "This month" },
  { id: "qtd", label: "This quarter" },
  { id: "fy", label: "This FY" },
  { id: "custom", label: "Custom" },
];

export default function Dashboard() {
  const [d, setD] = useState<any>(null);
  const [alerts, setAlerts] = useState<any>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState<number>(0);
  const [preset, setPreset] = useState("mtd");
  const [custom, setCustom] = useState({ start: "", end: "" });

  useEffect(() => {
    api.branches().then(setBranches).catch(() => setBranches([]));
    api.alerts().then(setAlerts).catch(() => setAlerts({ near_expiry: [], low_stock: [] }));
  }, []);

  useEffect(() => {
    if (preset === "custom" && (!custom.start || !custom.end)) return;
    const ac = new AbortController();
    api.dashboard({
      branchId: branchId || undefined,
      preset,
      start: preset === "custom" ? custom.start : undefined,
      end: preset === "custom" ? custom.end : undefined,
      signal: ac.signal,
    }).then(setD).catch((e) => {
      if (e?.name === "AbortError") return;
      setD((cur: any) => cur || {});
    });
    return () => ac.abort();
  }, [branchId, preset, custom.start, custom.end]);

  const periodLabel = PERIODS.find((p) => p.id === preset)?.label || "This month";
  const rangeLabel = d?.period_start && d?.period_end
    ? d.period_start === d.period_end ? d.period_start : `${d.period_start} → ${d.period_end}`
    : periodLabel;

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle={branchId ? `Branch view · ${rangeLabel}` : `All branches · ${rangeLabel}`}
        actions={
          <>
            <select value={branchId} onChange={(e) => setBranchId(Number(e.target.value))} style={{ width: "auto" }}>
              <option value={0}>All branches</option>
              {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
            <select value={preset} onChange={(e) => setPreset(e.target.value)} style={{ width: "auto" }}>
              {PERIODS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
            </select>
            {preset === "custom" && (
              <>
                <input type="date" value={custom.start} onChange={(e) => setCustom({ ...custom, start: e.target.value })} />
                <input type="date" value={custom.end} onChange={(e) => setCustom({ ...custom, end: e.target.value })} />
              </>
            )}
          </>
        }
      />

      {!d ? <Loading /> : (
        <>
          <div className="grid grid-4 mb-16">
            <StatCard label={`Sales (${periodLabel})`} value={inr(d.sales_period ?? d.sales_mtd)} sub={`${(d.invoice_count ?? d.invoice_count_today) || 0} invoices`} icon={<IndianRupee size={22} />} tone="bg-brand" />
            <StatCard label="Sales today" value={inr(d.sales_today)} sub={`FYTD ${inr(d.sales_ytd)}`} icon={<TrendingUp size={22} />} tone="bg-teal" />
            <StatCard label={`Gross profit (${periodLabel})`} value={inr(d.gross_profit ?? d.gross_profit_mtd)} icon={<Wallet size={22} />} tone="bg-violet" />
            <StatCard label={`Net after expenses`} value={inr(d.net_after_expenses ?? ((d.sales_period || 0) - (d.expenses_period || 0)))} sub={`Sales − expenses`} icon={<Banknote size={22} />} tone="bg-blue" />
          </div>
          <div className="grid grid-4 mb-16">
            <StatCard label={`Expenses (${periodLabel})`} value={inr(d.expenses_period)} sub={`${d.expense_count || 0} entries`} icon={<Receipt size={22} />} tone="bg-rose" />
            <StatCard label="Collected in period" value={inr(d.collections_period)} sub="Cash / UPI / card received" icon={<IndianRupee size={22} />} tone="bg-teal" />
            <StatCard label="Open receivables" value={inr(d.receivables_total)} sub={`${d.unpaid_invoice_count || 0} unpaid bills · ${d.khata_farmer_count || 0} khata farmers`} icon={<CalendarClock size={22} />} tone="bg-amber" />
            <StatCard label="Vendor payables" value={inr(d.payables_total)} sub={`${d.near_expiry_count || 0} batches near expiry`} icon={<Landmark size={22} />} tone="bg-violet" />
          </div>

          <Suspense
            fallback={
              <>
                <div className="grid grid-2 mb-16">
                  <Card title="Sales trend"><ChartSkeleton height={260} /></Card>
                  <Card title={`Sales by category (${periodLabel})`}><ChartSkeleton height={260} /></Card>
                </div>
                <div className="grid grid-2">
                  <Card title={`Branch comparison (${periodLabel})`}><ChartSkeleton height={240} /></Card>
                  <Card title={`Expenses by category (${periodLabel})`}><ChartSkeleton height={240} /></Card>
                </div>
              </>
            }
          >
            <DashboardCharts d={d} periodLabel={periodLabel} />
          </Suspense>

          <div className="grid grid-2" style={{ marginTop: 16 }}>
            <Suspense fallback={<Card title={`Payment mix (${periodLabel})`}><ChartSkeleton height={220} /></Card>}>
              <PaymentMix d={d} periodLabel={periodLabel} />
            </Suspense>

            <Card title="Alerts" icon={<AlertTriangle size={16} color="#d97706" />}>
              <Table
                columns={[
                  { key: "product", label: "Product" },
                  { key: "batch_no", label: "Batch" },
                  { key: "days_left", label: "Expiry", render: (r) => <Badge tone={r.days_left <= 15 ? "danger" : "warn"}>{r.days_left}d left</Badge> },
                  { key: "quantity", label: "Qty", num: true },
                ]}
                rows={alerts?.near_expiry || []}
                empty="No near-expiry batches"
              />
              {(alerts?.low_stock || []).length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Low stock</div>
                  <Table
                    columns={[
                      { key: "product", label: "Product" },
                      { key: "on_hand", label: "On hand", num: true },
                      { key: "reorder_level", label: "Reorder", num: true },
                    ]}
                    rows={alerts.low_stock}
                  />
                </div>
              )}
              {(alerts?.stock_cases || []).length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>
                    Stock mismatches ({alerts.stock_case_open} open){" "}
                    <Link to="/reports?report=stock_reconcile">open reconciliation</Link>
                  </div>
                  <Table
                    columns={[
                      { key: "product", label: "Product" },
                      { key: "branch", label: "Branch" },
                      { key: "variance", label: "Gap", num: true, render: (r) => (
                        <Badge tone={Number(r.variance) < 0 ? "danger" : "warn"}>{r.variance}</Badge>
                      ) },
                      { key: "status", label: "Case" },
                    ]}
                    rows={alerts.stock_cases}
                  />
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
