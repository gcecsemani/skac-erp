import { useEffect, useState } from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { IndianRupee, TrendingUp, Wallet, CalendarClock, AlertTriangle, Receipt, Landmark, Banknote } from "lucide-react";
import { api } from "../api";
import { CHART_COLORS, inr } from "../format";
import { Card, Loading, PageHeader, StatCard, Table, Badge } from "../components/ui";

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
    setD(null);
    api.dashboard({
      branchId: branchId || undefined,
      preset,
      start: preset === "custom" ? custom.start : undefined,
      end: preset === "custom" ? custom.end : undefined,
    }).then(setD).catch(() => setD({}));
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

          <div className="grid grid-2 mb-16">
            <Card title="Sales trend" >
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={d.sales_trend || []} margin={{ left: -8, right: 8, top: 8 }}>
                  <defs>
                    <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#16a34a" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#16a34a" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" vertical={false} />
                  <XAxis dataKey="date" tickFormatter={(v) => String(v).slice(5)} fontSize={11} stroke="#94a3b8" />
                  <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)} />
                  <Tooltip formatter={(v: any) => inr(v)} />
                  <Area type="monotone" dataKey="revenue" stroke="#16a34a" strokeWidth={2.5} fill="url(#g1)" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>

            <Card title={`Sales by category (${periodLabel})`}>
              {(d.category_split || []).length === 0 ? (
                <div className="empty">No sales in this period</div>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie data={d.category_split} dataKey="revenue" nameKey="category" cx="50%" cy="50%" outerRadius={90} innerRadius={55} paddingAngle={3}>
                      {d.category_split.map((_: any, i: number) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v: any) => inr(v)} />
                  </PieChart>
                </ResponsiveContainer>
              )}
              <div className="row" style={{ justifyContent: "center", marginTop: 8 }}>
                {(d.category_split || []).map((c: any, i: number) => (
                  <span key={c.category} className="row" style={{ gap: 6 }}>
                    <span className="cat-dot" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <span style={{ textTransform: "capitalize", fontSize: 12 }}>{c.category}</span>
                  </span>
                ))}
              </div>
            </Card>
          </div>

          <div className="grid grid-2">
            <Card title={`Branch comparison (${periodLabel})`}>
              {(d.branch_comparison || []).length === 0 ? (
                <div className="empty">No branch sales in this period</div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={d.branch_comparison || []} margin={{ left: -8, right: 8, top: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" vertical={false} />
                    <XAxis dataKey="branch" fontSize={11} stroke="#94a3b8" />
                    <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)} />
                    <Tooltip formatter={(v: any) => inr(v)} />
                    <Bar dataKey="revenue" fill="#0d9488" radius={[6, 6, 0, 0]} barSize={46} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>

            <Card title={`Expenses by category (${periodLabel})`}>
              {(d.expense_by_category || []).length === 0 ? (
                <div className="empty">No expenses in this period</div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={d.expense_by_category} margin={{ left: -8, right: 8, top: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" vertical={false} />
                    <XAxis dataKey="category" fontSize={11} stroke="#94a3b8" />
                    <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)} />
                    <Tooltip formatter={(v: any) => inr(v)} />
                    <Bar dataKey="amount" fill="#e11d48" radius={[6, 6, 0, 0]} barSize={46} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>

          <div className="grid grid-2" style={{ marginTop: 16 }}>
            <Card title={`Payment mix (${periodLabel})`}>
              {(d.payment_split || []).length === 0 ? (
                <div className="empty">No payments in this period</div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={d.payment_split} dataKey="revenue" nameKey="mode" cx="50%" cy="50%" outerRadius={80} innerRadius={48} paddingAngle={3}>
                      {(d.payment_split || []).map((_: any, i: number) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                    </Pie>
                    <Tooltip formatter={(v: any) => inr(v)} />
                  </PieChart>
                </ResponsiveContainer>
              )}
              <div className="row" style={{ justifyContent: "center", marginTop: 8 }}>
                {(d.payment_split || []).map((c: any, i: number) => (
                  <span key={c.mode} className="row" style={{ gap: 6 }}>
                    <span className="cat-dot" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <span style={{ textTransform: "capitalize", fontSize: 12 }}>{c.mode}</span>
                  </span>
                ))}
              </div>
            </Card>

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
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
