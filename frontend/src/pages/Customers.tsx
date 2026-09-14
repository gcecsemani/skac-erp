import { useEffect, useMemo, useState } from "react";
import { Plus, Search, Wallet, Pencil, Trash2, MessageCircle, BookOpen } from "lucide-react";
import { api } from "../api";
import { inr } from "../format";
import { Badge, Card, ExportButtons, Field, Loading, Modal, PageHeader, Table } from "../components/ui";
import { LocationFields, PaymentSelect } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
import { getCachedCustomers, matchCustomer, refreshCustomers, removeCached, upsertCached } from "../offline";
import * as V from "../validate";

const empty = { name: "", phone: "", aadhaar_no: "", village: "", district: "", land_holding_acres: "", gstin: "", credit_allowed: false, credit_limit: "" };

export default function Customers() {
  const { bundle, ready } = useConfigBundle();
  const [rows, setRows] = useState<any[] | null>(null);
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<any>(empty);
  const [err, setErr] = useState("");
  const [pay, setPay] = useState<any | null>(null);
  const [payForm, setPayForm] = useState({ amount: "", mode: "cash", note: "" });
  const [payErr, setPayErr] = useState("");
  const [remind, setRemind] = useState<any | null>(null);
  const [remindBusy, setRemindBusy] = useState(false);
  const [ledger, setLedger] = useState<any | null>(null);
  const [payConfirm, setPayConfirm] = useState(false);

  useEffect(() => {
    getCachedCustomers().then((cached) => { if (cached.length) setRows(cached); }).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    const q = search.trim();
    const t = window.setTimeout(() => {
      const job = q
        ? api.customers(q, 200)
        : refreshCustomers({ outstandingOnly: true, limit: 200 });
      job.then((list) => { if (!cancelled) setRows(list); })
        .catch(() => { if (!cancelled) setRows((cur) => cur || []); });
    }, q ? 220 : 0);
    return () => { cancelled = true; window.clearTimeout(t); };
  }, [search]);

  const filtered = useMemo(
    () => (rows || [])
      .filter((r) => matchCustomer(r, search))
      .sort((a, b) => Number(b.outstanding_balance || 0) - Number(a.outstanding_balance || 0) || String(a.name).localeCompare(String(b.name))),
    [rows, search],
  );

  const openCreate = () => { setEditId(null); setForm(empty); setErr(""); setOpen(true); };
  const openEdit = (r: any) => {
    setEditId(r.id); setErr("");
    setForm({ ...empty, ...Object.fromEntries(Object.keys(empty).map((k) => [k, r[k] ?? (k === "credit_allowed" ? false : "")])) });
    setOpen(true);
  };
  const remove = async (r: any) => {
    if (!confirm(`Delete farmer "${r.name}"?`)) return;
    try {
      await api.deleteCustomer(r.id);
      removeCached("customers", r.id);
      setRows((cur) => (cur || []).filter((x) => x.id !== r.id));
    } catch (e: any) { alert(e.message); }
  };

  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      V.minLen(form.name, "Name", 2),
      V.phone(form.phone, { required: true }),
      V.required(form.district, "District"),
      V.required(form.village, "Village"),
      V.aadhaar(form.aadhaar_no),
      V.gstin(form.gstin),
      form.credit_limit ? V.nonNegative(form.credit_limit, "Credit limit") : null,
      form.land_holding_acres ? V.nonNegative(form.land_holding_acres, "Land holding") : null,
    );
    if (msg) { setErr(msg); return; }
    const payload = {
      ...form,
      aadhaar_no: form.aadhaar_no || null,
      land_holding_acres: form.land_holding_acres ? Number(form.land_holding_acres) : null,
      credit_limit: form.credit_limit ? Number(form.credit_limit) : 0,
    };
    try {
      const saved = editId ? await api.updateCustomer(editId, payload) : await api.createCustomer(payload);
      upsertCached("customers", saved);
      setRows((cur) => {
        const list = cur || [];
        return editId ? list.map((x) => x.id === saved.id ? { ...x, ...saved } : x) : [saved, ...list.filter((x) => x.id !== saved.id)];
      });
      setOpen(false); setForm(empty); setEditId(null);
    } catch (e: any) { setErr(e.message); }
  };

  if (!rows) return <Loading />;

  return (
    <div>
      <PageHeader
        title="Farmers / Customers"
        subtitle="Khata farmers first — search name, phone or Aadhaar to find anyone"
        actions={
          <div className="row">
            <ExportButtons title="Farmers" columns={[
              { key: "name", label: "Name" }, { key: "phone", label: "Phone" },
              { key: "village", label: "Village" }, { key: "district", label: "District" },
              { key: "outstanding_balance", label: "Outstanding", num: true, money: true },
            ]} rows={rows || []} />
            <button className="btn btn-primary" onClick={openCreate}><Plus size={16} /> Add Farmer</button>
          </div>
        }
      />
      <Card>
        <div className="row mb-16" style={{ position: "relative", maxWidth: 340 }}>
          <Search size={17} style={{ position: "absolute", left: 12, color: "#94a3b8" }} />
          <input placeholder="Search name, phone or Aadhaar…" value={search}
            onChange={(e) => setSearch(e.target.value)} style={{ paddingLeft: 36 }} />
        </div>
        {search.trim() && (
          <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>
            Showing {filtered.length} match{filtered.length === 1 ? "" : "es"} — Excel/PDF export includes all {rows.length} farmers
          </p>
        )}
        <Table
          columns={[
            { key: "name", label: "Name" },
            { key: "phone", label: "Phone" },
            { key: "aadhaar_no", label: "Aadhaar", render: (r) => r.aadhaar_no || "—" },
            { key: "village", label: "Village" },
            { key: "district", label: "District" },
            { key: "credit_allowed", label: "Credit", render: (r) => r.credit_allowed ? <Badge tone="info">Allowed · {inr(r.credit_limit)}</Badge> : <Badge>Cash only</Badge> },
            { key: "outstanding_balance", label: "Outstanding", num: true, render: (r) => <strong style={{ color: r.outstanding_balance > 0 ? "var(--danger)" : "inherit" }}>{inr(r.outstanding_balance)}</strong> },
            { key: "actions", label: "", render: (r) => (
              <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                <button className="icon-btn" style={{ width: 30, height: 30 }} title="Ledger / payment history" onClick={async () => {
                  try { setLedger(await api.customerLedger(r.id)); } catch (e: any) { alert(e.message); }
                }}><BookOpen size={14} /></button>
                {r.outstanding_balance > 0 && (
                  <>
                    <button className="icon-btn" style={{ width: 30, height: 30 }} title="Collect khata" onClick={() => {
                      setPayErr(""); setPayConfirm(false); setPay(r);
                      setPayForm({ amount: "", mode: "cash", note: "" });
                    }}><Wallet size={14} /></button>
                    <button className="icon-btn" style={{ width: 30, height: 30 }} title="WhatsApp reminder" onClick={async () => {
                      try {
                        setRemindBusy(true);
                        const res = await api.remindCustomer(r.id, false);
                        setRemind(res);
                      } catch (e: any) { alert(e.message); }
                      finally { setRemindBusy(false); }
                    }}><MessageCircle size={14} /></button>
                  </>
                )}
                <button className="icon-btn" style={{ width: 30, height: 30 }} title="Edit" onClick={() => openEdit(r)}><Pencil size={14} /></button>
                <button className="icon-btn" style={{ width: 30, height: 30 }} title="Delete" onClick={() => remove(r)}><Trash2 size={14} /></button>
              </div>
            ) },
          ]}
          rows={filtered}
          empty="No farmers yet"
          pageSize={50}
        />
      </Card>

      {open && (
        <Modal title={editId ? "Edit Farmer" : "Add Farmer"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={submit}>Save</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="Name" required><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Phone" required><input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="Aadhaar (12 digits)"><input value={form.aadhaar_no} maxLength={12} onChange={(e) => setForm({ ...form, aadhaar_no: e.target.value.replace(/\D/g, "").slice(0, 12) })} /></Field>
            <LocationFields
              district={form.district || ""}
              village={form.village || ""}
              bundle={bundle}
              ready={ready}
              required
              onChange={(next) => setForm((f: any) => ({ ...f, ...next }))}
            />
            <Field label="Land (acres)"><input type="number" value={form.land_holding_acres} onChange={(e) => setForm({ ...form, land_holding_acres: e.target.value })} /></Field>
            <Field label="Credit limit (₹)"><input type="number" value={form.credit_limit} onChange={(e) => setForm({ ...form, credit_limit: e.target.value, credit_allowed: Number(e.target.value) > 0 })} /></Field>
          </div>
          <label className="row" style={{ gap: 8, cursor: "pointer" }}>
            <input type="checkbox" style={{ width: "auto" }} checked={form.credit_allowed} onChange={(e) => setForm({ ...form, credit_allowed: e.target.checked })} />
            <Wallet size={15} /> Allow credit (khata) account
          </label>
        </Modal>
      )}

      {pay && (
        <Modal
          title={`Collect khata — ${pay.name}`}
          onClose={() => setPay(null)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setPay(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={async () => {
              setPayErr("");
              const amount = Number(payForm.amount);
              if (!amount || amount <= 0) { setPayErr("Enter an amount greater than zero."); return; }
              if (amount > Number(pay.outstanding_balance || 0)) {
                setPayErr(`Amount cannot exceed outstanding ${inr(pay.outstanding_balance)}.`);
                return;
              }
              if (!payConfirm) { setPayConfirm(true); return; }
              try {
                await api.customerPayment(pay.id, { amount, mode: payForm.mode, note: payForm.note || null });
                const nextBal = Math.max(0, Number(pay.outstanding_balance || 0) - amount);
                const next = { ...pay, outstanding_balance: nextBal };
                upsertCached("customers", next);
                setRows((cur) => (cur || []).map((x) => x.id === next.id ? { ...x, ...next } : x));
                setPay(null); setPayConfirm(false);
                refreshCustomers({ outstandingOnly: true, limit: 200 }).then(setRows).catch(() => {});
              } catch (e: any) { setPayErr(e.message); }
            }}>{payConfirm ? `Confirm ${inr(Number(payForm.amount) || 0)}?` : "Record payment"}</button>
          </>}
        >
          {payErr && <div className="error">{payErr}</div>}
          {payConfirm && (
            <div className="error" style={{ background: "var(--warn-bg)", color: "#92400e" }}>
              Confirm collecting {inr(Number(payForm.amount) || 0)} from {pay.name}? This will reduce their khata.
            </div>
          )}
          <p className="muted" style={{ marginTop: 0 }}>Outstanding: <strong>{inr(pay.outstanding_balance)}</strong> — type the amount received. It is not filled in automatically.</p>
          <div className="grid grid-2">
            <Field label="Amount received (₹)" required>
              <input type="number" min={0} step="0.01" value={payForm.amount} placeholder="Enter amount"
                onChange={(e) => { setPayConfirm(false); setPayForm({ ...payForm, amount: e.target.value }); }} />
            </Field>
            <Field label="Mode">
              <PaymentSelect value={payForm.mode} onChange={(mode) => { setPayConfirm(false); setPayForm({ ...payForm, mode }); }} use="khata" bundle={bundle} />
            </Field>
          </div>
          <Field label="Note">
            <input value={payForm.note} onChange={(e) => setPayForm({ ...payForm, note: e.target.value })} placeholder="optional" />
          </Field>
        </Modal>
      )}

      {remind && (
        <Modal
          title={`WhatsApp reminder — ${remind.customer_name}`}
          onClose={() => setRemind(null)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setRemind(null)}>Close</button>
            {remind.wa_link && (
              <a className="btn btn-primary" href={remind.wa_link} target="_blank" rel="noreferrer">
                <MessageCircle size={16} /> Open WhatsApp
              </a>
            )}
            {remind.api_configured && (
              <button className="btn btn-ghost" disabled={remindBusy} onClick={async () => {
                setRemindBusy(true);
                try {
                  const res = await api.remindCustomer(remind.customer_id, true);
                  setRemind(res);
                } catch (e: any) { alert(e.message); }
                finally { setRemindBusy(false); }
              }}>Send via API</button>
            )}
          </>}
        >
          <p className="muted" style={{ marginTop: 0 }}>Outstanding: <strong>{inr(remind.outstanding)}</strong> · {remind.phone}</p>
          {remind.sent && <div style={{ color: "var(--brand-600)", fontWeight: 600, marginBottom: 8 }}>Message sent via WhatsApp Cloud API.</div>}
          {remind.error && <div className="error">{remind.error}</div>}
          <Field label="Message">
            <textarea readOnly value={remind.message} rows={4} style={{ width: "100%", resize: "vertical" }} />
          </Field>
          <p className="muted" style={{ fontSize: 12 }}>
            {remind.api_configured
              ? "Cloud API is configured. You can send from SKAC, or open WhatsApp to send from your phone."
              : "No WhatsApp Business API key is set. Open WhatsApp to send this reminder from your phone or WhatsApp Web. To auto-send, add WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID in the backend .env."}
          </p>
        </Modal>
      )}

      {ledger && (
        <Modal title={`Ledger — ${ledger.name}`} onClose={() => setLedger(null)} wide
          footer={<button className="btn btn-ghost" onClick={() => setLedger(null)}>Close</button>}>
          <p className="muted" style={{ marginTop: 0 }}>
            {ledger.phone || "No phone"}{ledger.village ? ` · ${ledger.village}` : ""} · Outstanding{" "}
            <strong style={{ color: Number(ledger.outstanding_balance) > 0 ? "var(--danger)" : "inherit" }}>{inr(ledger.outstanding_balance)}</strong>
          </p>
          <h3 style={{ fontSize: 14, margin: "4px 0 8px" }}>Khata collections</h3>
          <Table
            columns={[
              { key: "paid_at", label: "Date", render: (r) => String(r.paid_at || "").replace("T", " ").slice(0, 16) },
              { key: "mode", label: "Mode" },
              { key: "note", label: "Note", render: (r) => r.note || "—" },
              { key: "amount", label: "Amount", num: true, render: (r) => inr(r.amount) },
            ]}
            rows={ledger.payments || []}
            empty="No khata collections recorded yet"
            scroll={false}
          />
          <h3 style={{ fontSize: 14, margin: "16px 0 8px" }}>Invoices</h3>
          <Table
            columns={[
              { key: "invoice_no", label: "Invoice #" },
              { key: "date", label: "Date" },
              { key: "total", label: "Total", num: true, render: (r) => inr(r.total) },
              { key: "outstanding", label: "Balance", num: true, render: (r) => Number(r.outstanding) > 0 ? inr(r.outstanding) : "Paid" },
            ]}
            rows={ledger.invoices || []}
            empty="No invoices for this farmer"
            pageSize={25}
          />
        </Modal>
      )}
    </div>
  );
}
