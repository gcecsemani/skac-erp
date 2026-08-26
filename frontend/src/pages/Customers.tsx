import { useEffect, useState } from "react";
import { Plus, Search, Wallet, Pencil, Trash2, MessageCircle } from "lucide-react";
import { api } from "../api";
import { inr } from "../format";
import { Badge, Card, ExportButtons, Field, Loading, Modal, PageHeader, Table } from "../components/ui";
import { LocationFields, PaymentSelect } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
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

  const load = (q?: string) => api.customers(q || undefined, 200).then(setRows).catch(() => setRows([]));
  useEffect(() => { load(); }, []);

  const openCreate = () => { setEditId(null); setForm(empty); setErr(""); setOpen(true); };
  const openEdit = (r: any) => {
    setEditId(r.id); setErr("");
    setForm({ ...empty, ...Object.fromEntries(Object.keys(empty).map((k) => [k, r[k] ?? (k === "credit_allowed" ? false : "")])) });
    setOpen(true);
  };
  const remove = async (r: any) => {
    if (!confirm(`Delete farmer "${r.name}"?`)) return;
    try { await api.deleteCustomer(r.id); load(search); } catch (e: any) { alert(e.message); }
  };

  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      V.minLen(form.name, "Name", 2),
      V.phone(form.phone),
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
      if (editId) await api.updateCustomer(editId, payload);
      else await api.createCustomer(payload);
      setOpen(false); setForm(empty); setEditId(null); load(search);
    } catch (e: any) { setErr(e.message); }
  };

  if (!rows) return <Loading />;

  return (
    <div>
      <PageHeader
        title="Farmers / Customers"
        subtitle="Customer master with credit (khata) accounts"
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
            onChange={(e) => { setSearch(e.target.value); load(e.target.value); }} style={{ paddingLeft: 36 }} />
        </div>
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
                {r.outstanding_balance > 0 && (
                  <>
                    <button className="icon-btn" style={{ width: 30, height: 30 }} title="Collect khata" onClick={() => {
                      setPayErr(""); setPay(r);
                      setPayForm({ amount: String(r.outstanding_balance), mode: "cash", note: "" });
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
          rows={rows}
          empty="No farmers yet"
        />
      </Card>

      {open && (
        <Modal title={editId ? "Edit Farmer" : "Add Farmer"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={submit}>Save</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="Name" required><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Phone"><input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            <Field label="Aadhaar (12 digits)"><input value={form.aadhaar_no} maxLength={12} onChange={(e) => setForm({ ...form, aadhaar_no: e.target.value.replace(/\D/g, "").slice(0, 12) })} /></Field>
            <LocationFields
              district={form.district || ""}
              village={form.village || ""}
              bundle={bundle}
              ready={ready}
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
              try {
                await api.customerPayment(pay.id, { amount, mode: payForm.mode, note: payForm.note || null });
                setPay(null); load(search);
              } catch (e: any) { setPayErr(e.message); }
            }}>Record payment</button>
          </>}
        >
          {payErr && <div className="error">{payErr}</div>}
          <p className="muted" style={{ marginTop: 0 }}>Outstanding: <strong>{inr(pay.outstanding_balance)}</strong></p>
          <div className="grid grid-2">
            <Field label="Amount received (₹)">
              <input type="number" min={0} step="0.01" value={payForm.amount} onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} />
            </Field>
            <Field label="Mode">
              <PaymentSelect value={payForm.mode} onChange={(mode) => setPayForm({ ...payForm, mode })} use="khata" bundle={bundle} />
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
    </div>
  );
}
