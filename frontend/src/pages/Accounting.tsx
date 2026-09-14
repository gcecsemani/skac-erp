import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { TrendingUp, TrendingDown, Wallet } from "lucide-react";
import { api } from "../api";
import { CHART_COLORS, inr, matchesQuery } from "../format";
import { Card, ExportButtons, Loading, PageHeader, SearchInput, StatCard, Table } from "../components/ui";

export default function Accounting() {
  const [tab, setTab] = useState("pnl");
  const [q, setQ] = useState("");
  const [acctType, setAcctType] = useState("");
  const [pnl, setPnl] = useState<any>(null);
  const [gst, setGst] = useState<any>(null);
  const [aging, setAging] = useState<any>(null);
  const [payables, setPayables] = useState<any>(null);
  const [accounts, setAccounts] = useState<any[] | null>(null);
  const [daybook, setDaybook] = useState<any[] | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api.pnl().then(setPnl).catch(() => setPnl({})).finally(() => setReady(true));
  }, []);

  useEffect(() => {
    if (tab === "gst" && gst === null) api.gstSummary().then(setGst).catch(() => setGst({ slabs: [] }));
    if (tab === "aging" && aging === null) api.receivablesAging().then(setAging).catch(() => setAging({ buckets: {}, total: 0 }));
    if (tab === "payables" && payables === null) api.payables().then(setPayables).catch(() => setPayables({ vendors: [] }));
    if (tab === "accounts" && accounts === null) api.accounts().then(setAccounts).catch(() => setAccounts([]));
    if (tab === "daybook" && daybook === null) api.daybook().then(setDaybook).catch(() => setDaybook([]));
  }, [tab]);

  const gstRows = useMemo(
    () => (gst?.slabs || []).filter((r: any) => matchesQuery(q, r.gst_rate, r.taxable_value, r.cgst, r.sgst, r.total_tax)),
    [gst, q],
  );
  const payableRows = useMemo(
    () => (payables?.vendors || []).filter((r: any) => matchesQuery(q, r.name, r.outstanding)),
    [payables, q],
  );
  const accountTypes = useMemo(
    () => [...new Set((accounts || []).map((r) => r.type).filter(Boolean))],
    [accounts],
  );
  const accountRows = useMemo(
    () => (accounts || []).filter((r) => (!acctType || r.type === acctType) && matchesQuery(q, r.code, r.name, r.type)),
    [accounts, q, acctType],
  );
  const daybookRows = useMemo(
    () => (daybook || []).filter((e) => matchesQuery(
      q, e.narration, e.date, e.ref_type, e.ref_id,
      ...(e.lines || []).flatMap((l: any) => [l.code, l.account]),
    )),
    [daybook, q],
  );

  if (!ready) return <Loading />;
  const agingData = aging ? Object.entries(aging.buckets).map(([k, v]) => ({ bucket: k, amount: Number(v) })) : [];

  return (
    <div>
      <PageHeader title="Accounting & Finance" subtitle="Double-entry ledger, GST summaries and outstanding reports"
        actions={tab === "pnl" ? <ExportButtons title="Profit & Loss" columns={[{ key: "k", label: "Line" }, { key: "v", label: "Amount", num: true, money: true }]} rows={[{ k: "Income", v: pnl?.income }, { k: "Expense", v: pnl?.expense }, { k: "Net Profit", v: pnl?.net_profit }]} /> :
          tab === "gst" ? <ExportButtons title="GST summary" columns={[{ key: "gst_rate", label: "GST %" }, { key: "taxable_value", label: "Taxable", num: true, money: true }, { key: "total_tax", label: "Tax", num: true, money: true }]} rows={gstRows} /> :
          tab === "payables" ? <ExportButtons title="Payables" columns={[{ key: "name", label: "Vendor" }, { key: "outstanding", label: "Payable", num: true, money: true }]} rows={payableRows} /> :
          tab === "accounts" ? <ExportButtons title="Chart of accounts" columns={[{ key: "code", label: "Code" }, { key: "name", label: "Account" }, { key: "type", label: "Type" }]} rows={accountRows} /> :
          undefined}
      />
      <div className="grid grid-3 mb-16">
        <StatCard label="Income (MTD)" value={inr(pnl?.income)} icon={<TrendingUp size={22} />} tone="bg-brand" />
        <StatCard label="Expense (MTD)" value={inr(pnl?.expense)} icon={<TrendingDown size={22} />} tone="bg-rose" />
        <StatCard label="Net Profit (MTD)" value={inr(pnl?.net_profit)} icon={<Wallet size={22} />} tone="bg-teal" />
      </div>

      <div className="tabs">
        {[["pnl", "P&L"], ["gst", "GST Summary"], ["aging", "Receivables"], ["payables", "Payables"], ["accounts", "Chart of Accounts"], ["daybook", "Day-book"]].map(([k, l]) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => { setTab(k); setQ(""); setAcctType(""); }}>{l}</button>
        ))}
      </div>

      {tab === "pnl" && (
        <Card title="Profit & Loss (Month to date)">
          <Table columns={[{ key: "k", label: "Line" }, { key: "v", label: "Amount", num: true, render: (r) => <strong>{inr(r.v)}</strong> }]}
            rows={[{ k: "Income", v: pnl.income }, { k: "Expense", v: pnl.expense }, { k: "Net Profit", v: pnl.net_profit }]} />
        </Card>
      )}

      {tab === "gst" && (gst === null ? <Loading /> : (
        <Card title="GSTR-1 / 3B Outward Supply Summary">
          <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
            <SearchInput value={q} onChange={setQ} placeholder="Search GST rate or amount…" />
          </div>
          <Table
            columns={[
              { key: "gst_rate", label: "GST Rate %", num: true },
              { key: "taxable_value", label: "Taxable Value", num: true, render: (r) => inr(r.taxable_value) },
              { key: "cgst", label: "CGST", num: true, render: (r) => inr(r.cgst) },
              { key: "sgst", label: "SGST", num: true, render: (r) => inr(r.sgst) },
              { key: "total_tax", label: "Total Tax", num: true, render: (r) => <strong>{inr(r.total_tax)}</strong> },
            ]}
            rows={gstRows} empty={gst?.slabs?.length ? "No slabs match the search" : "No taxable sales in period"}
          />
          <div className="row mt-8" style={{ justifyContent: "flex-end", gap: 24, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
            <span>Taxable: <strong>{inr(gst?.total_taxable)}</strong></span>
            <span>Total tax: <strong>{inr(gst?.total_tax)}</strong></span>
          </div>
        </Card>
      ))}

      {tab === "aging" && (aging === null ? <Loading /> : (
        <div className="grid grid-2">
          <Card title="Receivables Aging">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={agingData} margin={{ left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f6" vertical={false} />
                <XAxis dataKey="bucket" fontSize={11} stroke="#94a3b8" />
                <YAxis fontSize={11} stroke="#94a3b8" tickFormatter={(v) => (v >= 1000 ? `${v / 1000}k` : v)} />
                <Tooltip formatter={(v: any) => inr(v)} />
                <Bar dataKey="amount" radius={[6, 6, 0, 0]} barSize={54}>
                  {agingData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
          <Card title="Aging Buckets">
            <Table columns={[{ key: "bucket", label: "Age (days)" }, { key: "amount", label: "Outstanding", num: true, render: (r) => inr(r.amount) }]} rows={agingData} />
            <div className="row mt-8" style={{ justifyContent: "flex-end", paddingTop: 12, borderTop: "1px solid var(--border)" }}>Total: <strong>&nbsp;{inr(aging?.total)}</strong></div>
          </Card>
        </div>
      ))}

      {tab === "payables" && (payables === null ? <Loading /> : (
        <Card title="Vendor Payables">
          <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
            <SearchInput value={q} onChange={setQ} placeholder="Search vendor…" />
          </div>
          <Table columns={[{ key: "name", label: "Vendor" }, { key: "outstanding", label: "Payable", num: true, render: (r) => <strong>{inr(r.outstanding)}</strong> }]} rows={payableRows} empty={payables?.vendors?.length ? "No vendors match the search" : "No payables"} />
        </Card>
      ))}

      {tab === "accounts" && (accounts === null ? <Loading /> : (
        <Card title="Chart of Accounts">
          <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
            <SearchInput value={q} onChange={setQ} placeholder="Search code or account…" />
            {accountTypes.length > 0 && (
              <select value={acctType} onChange={(e) => setAcctType(e.target.value)} style={{ width: "auto" }}>
                <option value="">All types</option>
                {accountTypes.map((t) => <option key={t} value={t}>{String(t)[0].toUpperCase() + String(t).slice(1)}</option>)}
              </select>
            )}
          </div>
          <Table columns={[{ key: "code", label: "Code" }, { key: "name", label: "Account" }, { key: "type", label: "Type", render: (r) => <span style={{ textTransform: "capitalize" }}>{r.type}</span> }]} rows={accountRows} empty={(accounts || []).length ? "No accounts match the filters" : "No accounts"} />
        </Card>
      ))}

      {tab === "daybook" && (
        <Card title="Day-book (Journal Entries)">
          <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
            <SearchInput value={q} onChange={setQ} placeholder="Search narration, ref or account…" />
          </div>
          {daybook === null ? <Loading /> : daybookRows.length === 0 ? <div className="empty">{daybook.length ? "No entries match the search" : "No entries"}</div> : daybookRows.map((e) => (
            <div key={e.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <strong>{e.narration}</strong><span className="muted">{e.date} · {e.ref_type} #{e.ref_id}</span>
              </div>
              <div style={{ marginTop: 6 }}>
                {e.lines.map((l: any, i: number) => (
                  <div key={i} className="row" style={{ justifyContent: "space-between", fontSize: 13, color: "var(--text-2)", paddingLeft: l.credit > 0 ? 24 : 0 }}>
                    <span>{l.code} · {l.account}</span>
                    <span>{l.debit > 0 ? `Dr ${inr(l.debit)}` : `Cr ${inr(l.credit)}`}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}
