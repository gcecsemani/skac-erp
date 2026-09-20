import { useEffect, useState } from "react";
import { Banknote, Landmark, CheckCircle2, AlertTriangle } from "lucide-react";
import { api } from "../api";
import { inr, todayISO } from "../format";
import { Badge, BranchSelect, Card, Field, Loading, PageHeader, StatCard, Table } from "../components/ui";
import * as V from "../validate";

const r2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

function tone(v: number) {
  if (Math.abs(v) < 0.005) return "success" as const;
  return v < 0 ? "danger" as const : "warn" as const;
}

function Line({ label, value, strong, danger }: { label: string; value: number; strong?: boolean; danger?: boolean }) {
  return (
    <div className="totals-row" style={{ fontWeight: strong ? 700 : 400, color: danger && value < 0 ? "var(--danger)" : undefined }}>
      <span>{label}</span>
      <span>{inr(value)}</span>
    </div>
  );
}

export default function DayClose() {
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState(0);
  const [closeDate, setCloseDate] = useState(todayISO);
  const [preview, setPreview] = useState<any | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [openingCash, setOpeningCash] = useState("");
  const [countedCash, setCountedCash] = useState("");
  const [countedDigital, setCountedDigital] = useState("");
  const [note, setNote] = useState("");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.branches().then((b) => {
      setBranches(b);
      if (b[0]) setBranchId(b[0].id);
    }).catch(() => setBranches([]));
  }, []);

  const load = (opts?: { keepMsg?: boolean }) => {
    if (!branchId) return;
    if (!opts?.keepMsg) { setErr(""); setMsg(""); }
    api.dayClosePreview(branchId, closeDate)
      .then((p) => {
        setPreview(p);
        const existing = p.existing;
        setOpeningCash(String(existing ? existing.opening_cash : p.opening_cash ?? 0));
        setCountedCash(existing ? String(existing.counted_cash) : "");
        setCountedDigital(existing ? String(existing.counted_digital) : "");
        setNote(existing?.note || "");
      })
      .catch((e: any) => { setErr(e.message); setPreview({}); });
    api.dayCloses(branchId).then(setHistory).catch(() => setHistory([]));
  };

  useEffect(() => { load(); }, [branchId, closeDate]);

  const opening = r2(Number(openingCash) || 0);
  const cashIn = Number(preview?.cash_in || 0);
  const cashOut = Number(preview?.cash_out || 0);
  const expectedCash = r2(opening + cashIn - cashOut);
  const expectedDigital = r2(Number(preview?.digital_in || 0) - Number(preview?.digital_out || 0));
  const countedC = r2(Number(countedCash) || 0);
  const countedD = r2(Number(countedDigital) || 0);
  const cashVar = r2(countedC - expectedCash);
  const digitalVar = r2(countedD - expectedDigital);

  const save = async () => {
    setErr(""); setMsg("");
    const msg0 = V.firstError(
      branchId ? null : "Select a branch.",
      countedCash === "" ? "Enter the cash counted in the box." : V.nonNegative(countedCash, "Counted cash"),
      countedDigital === "" ? "Enter UPI / bank received (0 if none)." : V.nonNegative(countedDigital, "UPI / bank"),
      V.nonNegative(openingCash || 0, "Opening cash"),
    );
    if (msg0) { setErr(msg0); return; }
    if ((cashVar !== 0 || digitalVar !== 0) && !note.trim()) {
      setErr("There is a difference. Add a short note (shortage, extra bill, wrong payment mode) before closing.");
      return;
    }
    const ok = confirm(
      cashVar === 0 && digitalVar === 0
        ? `Close ${closeDate}? Cash and UPI match SKAC.`
        : `Close ${closeDate} with differences?\nCash ${inr(cashVar)} · UPI/bank ${inr(digitalVar)}`,
    );
    if (!ok) return;
    setSaving(true);
    try {
      await api.saveDayClose({
        branch_id: branchId,
        close_date: closeDate,
        opening_cash: opening,
        counted_cash: countedC,
        counted_digital: countedD,
        note: note.trim() || null,
      });
      setMsg("Day closed. Opening cash for the next day will be today’s counted cash.");
      load({ keepMsg: true });
    } catch (e: any) { setErr(e.message); }
    finally { setSaving(false); }
  };

  if (!preview) return <Loading />;

  return (
    <div>
      <PageHeader
        title="Day close"
        subtitle="Match the cash box and UPI / bank to what SKAC collected today"
        actions={
          <div className="row">
            <BranchSelect value={branchId} onChange={setBranchId} branches={branches} allowAll={false} />
            <input type="date" value={closeDate} onChange={(e) => setCloseDate(e.target.value)} style={{ width: "auto" }} />
          </div>
        }
      />

      {preview.closed && (
        <div className="error" style={{ background: "var(--success-bg)", color: "#166534", marginBottom: 16 }}>
          This day is already closed. You can recount and save again if something was missed.
        </div>
      )}

      <div className="grid grid-4 mb-16">
        <StatCard label="Bills" value={preview.bill_count || 0} sub={inr(preview.sales_total)} icon={<CheckCircle2 size={22} />} />
        <StatCard label="Collected" value={inr(preview.collected_total)} sub={`Khata collected ${inr(preview.khata_collected)}`} icon={<Banknote size={22} />} tone="bg-teal" />
        <StatCard label="On khata (new)" value={inr(preview.khata_new)} sub="Unpaid on today’s bills" icon={<AlertTriangle size={22} />} tone="bg-amber" />
        <StatCard label="Paid out" value={inr(Number(preview.expense_total || 0) + Number(preview.vendor_paid || 0))} sub={`Expenses ${inr(preview.expense_total)} · vendors ${inr(preview.vendor_paid)}`} icon={<Landmark size={22} />} tone="bg-rose" />
      </div>

      <div className="grid grid-2 mb-16">
        <Card title="Cash box" icon={<Banknote size={16} />}>
          <Field label="Opening cash (from last close, edit if needed)">
            <input type="number" min={0} step="0.01" value={openingCash} onChange={(e) => setOpeningCash(e.target.value)} />
          </Field>
          {preview.previous_close_date && (
            <p className="muted" style={{ marginTop: -8, fontSize: 12 }}>Last close: {preview.previous_close_date}</p>
          )}
          {!preview.previous_close_date && (
            <p className="muted" style={{ marginTop: -8, fontSize: 12 }}>No earlier close — opening is ₹0 unless you type yesterday’s leftover cash.</p>
          )}
          <Line label="Cash collected (bills + khata)" value={cashIn} />
          <Line label="Cash paid out (expenses / vendors)" value={-cashOut} danger />
          <div className="totals-grand"><span>Should be in the box</span><span>{inr(expectedCash)}</span></div>
          {expectedCash < 0 && (
            <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>
              Paid out more cash than came in. Count what is still in the box (often ₹0), or enter leftover from yesterday as opening cash.
            </p>
          )}
          <Field label="Cash counted in the box" required>
            <input type="number" min={0} step="0.01" value={countedCash} placeholder="Count notes and coins" onChange={(e) => setCountedCash(e.target.value)} />
          </Field>
          {countedCash !== "" && (
            <div className="totals-row" style={{ fontWeight: 700 }}>
              <span>Difference</span>
              <Badge tone={tone(cashVar)}>{cashVar === 0 ? "Matched" : `${cashVar > 0 ? "Extra" : "Short"} ${inr(Math.abs(cashVar))}`}</Badge>
            </div>
          )}
        </Card>

        <Card title="UPI / card / bank" icon={<Landmark size={16} />}>
          <Line label="Received in SKAC" value={Number(preview.digital_in || 0)} />
          <Line label="Paid from UPI / bank" value={-Number(preview.digital_out || 0)} danger />
          <div className="totals-grand"><span>Should be in bank / UPI</span><span>{inr(expectedDigital)}</span></div>
          <Field label="Amount in bank / UPI app for this day" required>
            <input type="number" min={0} step="0.01" value={countedDigital} placeholder="PhonePe / GPay / bank total" onChange={(e) => setCountedDigital(e.target.value)} />
          </Field>
          {countedDigital !== "" && (
            <div className="totals-row" style={{ fontWeight: 700 }}>
              <span>Difference</span>
              <Badge tone={tone(digitalVar)}>{digitalVar === 0 ? "Matched" : `${digitalVar > 0 ? "Extra" : "Short"} ${inr(Math.abs(digitalVar))}`}</Badge>
            </div>
          )}
          <p className="muted" style={{ fontSize: 12, marginBottom: 0 }}>
            Sales on khata do not go into cash or UPI. Credit bills show under “On khata (new)”. Collections against old credit bills show as “Khata collected”.
          </p>
        </Card>
      </div>

      {(Number(preview.unscoped_in) > 0 || Number(preview.unscoped_out) > 0) && (
        <div className="error" style={{ background: "var(--warn-bg)", color: "#92400e", marginBottom: 16 }}>
          Unassigned collections {inr(preview.unscoped_in)} / payments {inr(preview.unscoped_out)} have no branch tag, so they are not in the totals above. Add them to counted cash/UPI only if that money is in this shop and not already on today’s bills.
        </div>
      )}

      <Card>
        <Field label="Note (required if there is a difference)">
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Shortage, extra cash, bill saved as cash instead of UPI…" />
        </Field>
        {err && <div className="error">{err}</div>}
        {msg && <div style={{ color: "var(--brand-600)", fontWeight: 600, marginBottom: 12 }}>{msg}</div>}
        <button className="btn btn-primary" disabled={saving || !branchId} onClick={save}>
          <CheckCircle2 size={16} /> {preview.closed ? "Update day close" : "Close day"}
        </button>
      </Card>

      <div style={{ marginTop: 18 }}>
        <Card title="Recent closes">
          <Table
            pageSize={50}
            empty="No day closes yet"
            rows={history}
            columns={[
              { key: "close_date", label: "Date" },
              { key: "branch_name", label: "Branch", render: (r) => r.branch_name || "—" },
              { key: "sales_total", label: "Sales", num: true, render: (r) => inr(r.sales_total) },
              { key: "collected_total", label: "Collected", num: true, render: (r) => inr(r.collected_total) },
              { key: "counted_cash", label: "Cash counted", num: true, render: (r) => inr(r.counted_cash) },
              { key: "cash_variance", label: "Cash diff", num: true, render: (r) => (
                <Badge tone={tone(Number(r.cash_variance))}>{inr(r.cash_variance)}</Badge>
              ) },
              { key: "counted_digital", label: "UPI / bank", num: true, render: (r) => inr(r.counted_digital) },
              { key: "digital_variance", label: "UPI diff", num: true, render: (r) => (
                <Badge tone={tone(Number(r.digital_variance))}>{inr(r.digital_variance)}</Badge>
              ) },
              { key: "closed_by", label: "Closed by", render: (r) => r.closed_by || "—" },
            ]}
          />
        </Card>
      </div>
    </div>
  );
}
