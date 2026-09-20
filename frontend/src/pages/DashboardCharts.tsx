/**
 * Dashboard charts, split out so recharts (~100 kB gzipped) loads as its own
 * chunk. The dashboard is the landing route, and the numbers and alerts a shop
 * owner actually reads first should not wait on the charting library.
 */
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { CHART_COLORS, inr } from "../format";
import { Card } from "../components/ui";

const rupeeTick = (v: any) => (v >= 1000 ? `${v / 1000}k` : v);

type Props = { d: any; periodLabel: string };

export function DashboardCharts({ d, periodLabel }: Props) {
  return (
    <>
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
              <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={rupeeTick} />
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
                <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={rupeeTick} />
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
                <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={rupeeTick} />
                <Tooltip formatter={(v: any) => inr(v)} />
                <Bar dataKey="amount" fill="#e11d48" radius={[6, 6, 0, 0]} barSize={46} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>
    </>
  );
}

export function PaymentMix({ d, periodLabel }: Props) {
  return (
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
  );
}
