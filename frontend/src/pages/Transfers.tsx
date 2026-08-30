import { useEffect, useState } from "react";
import { ArrowLeftRight, Check, Eye, Plus, Printer, Trash2, X } from "lucide-react";
import { api } from "../api";
import { printTransferReceipt } from "../print";
import { Badge, Card, Field, Loading, Modal, PageHeader, SearchSelect, Table } from "../components/ui";
import * as V from "../validate";

function newLine() {
  return { key: `${Date.now()}-${Math.random()}`, product_id: "", quantity: "" };
}

export default function Transfers() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [pickerProducts, setPickerProducts] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<any>({ from_branch_id: "", to_branch_id: "", notes: "", lines: [newLine()] });
  const [view, setView] = useState<any | null>(null);

  const load = () => api.transfers().then(setRows).catch(() => setRows([]));
  useEffect(() => {
    load();
    api.branches().then(setBranches).catch(() => {});
  }, []);

  const searchProducts = (q: string) => {
    api.products(q || undefined, undefined, 40).then(setPickerProducts).catch(() => {});
  };

  const openNew = () => {
    setErr("");
    setForm({
      from_branch_id: branches[0]?.id || "",
      to_branch_id: branches[1]?.id || "",
      notes: "",
      lines: [newLine()],
    });
    setPickerProducts([]);
    api.products(undefined, undefined, 80).then(setPickerProducts).catch(() => {});
    setOpen(true);
  };

  const setLine = (index: number, patch: any) => {
    setForm((f: any) => ({
      ...f,
      lines: (f.lines || []).map((ln: any, i: number) => (i === index ? { ...ln, ...patch } : ln)),
    }));
  };

  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      form.from_branch_id ? null : "Select the from branch.",
      form.to_branch_id ? null : "Select the to branch.",
      String(form.from_branch_id) === String(form.to_branch_id) ? "From and to branches must be different." : null,
      (form.lines || []).length ? null : "Add at least one product.",
      ...(form.lines || []).flatMap((ln: any, i: number) => [
        ln.product_id ? null : `Line ${i + 1}: select a product.`,
        V.positive(ln.quantity, `Line ${i + 1} quantity`),
      ]),
    );
    if (msg) { setErr(msg); return; }
    setSaving(true);
    try {
      await api.createTransfer({
        from_branch_id: Number(form.from_branch_id),
        to_branch_id: Number(form.to_branch_id),
        notes: form.notes || null,
        items: form.lines.map((ln: any) => ({
          product_id: Number(ln.product_id), quantity: Number(ln.quantity),
        })),
      });
      setOpen(false);
      load();
    } catch (e: any) { setErr(e.message); }
    finally { setSaving(false); }
  };

  const act = async (id: number, approve: boolean) => {
    try {
      await (approve ? api.approveTransfer(id) : api.rejectTransfer(id));
      load();
    } catch (e: any) { alert(e.message); }
  };

  const loadDoc = async (row: any) => {
    try { return await api.transfer(row.id); } catch { return row; }
  };

  const openView = async (row: any) => setView(await loadDoc(row));
  const printDoc = async (row: any) => printTransferReceipt(await loadDoc(row));

  if (!rows) return <Loading />;
  const bname = (id: number) => branches.find((b) => b.id === id)?.name || id;
  const tone = (s: string) => (s === "received" ? "success" : s === "rejected" ? "danger" : "warn");

  return (
    <div>
      <PageHeader
        title="Stock Transfers"
        subtitle="Move one or more products between branches. View or print the transfer receipt when you need it."
        actions={<button className="btn btn-primary" onClick={openNew}><Plus size={16} /> New Transfer</button>}
      />
      <Card>
        <Table
          columns={[
            { key: "transfer_no", label: "Transfer #" },
            { key: "from", label: "From", render: (r) => r.from_branch || bname(r.from_branch_id) },
            { key: "arrow", label: "", render: () => <ArrowLeftRight size={15} className="muted" /> },
            { key: "to", label: "To", render: (r) => r.to_branch || bname(r.to_branch_id) },
            { key: "items", label: "Items", render: (r) => r.items.map((i: any) => `${i.product_name} ×${i.quantity}`).join(", ") },
            { key: "status", label: "Status", render: (r) => <Badge tone={tone(r.status)}>{r.status}</Badge> },
            { key: "actions", label: "", render: (r) => (
              <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                <button className="btn btn-ghost btn-sm" title="View" onClick={() => openView(r)}><Eye size={15} /></button>
                <button className="btn btn-ghost btn-sm" title="Print" onClick={() => printDoc(r)}><Printer size={15} /></button>
                {r.status === "requested" ? (
                  <>
                    <button className="btn btn-primary btn-sm" onClick={() => act(r.id, true)}><Check size={14} /></button>
                    <button className="btn btn-ghost btn-sm" onClick={() => act(r.id, false)}><X size={14} /></button>
                  </>
                ) : null}
              </div>
            ) },
          ]}
          rows={rows}
          empty="No transfers yet"
        />
      </Card>

      {open && (
        <Modal title="New Stock Transfer" onClose={() => setOpen(false)} wide
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)} disabled={saving}>Cancel</button><button className="btn btn-primary" onClick={submit} disabled={saving}>{saving ? "Saving…" : "Request transfer"}</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="From branch" required>
              <select value={form.from_branch_id} onChange={(e) => setForm({ ...form, from_branch_id: e.target.value })}>
                <option value="">Select…</option>
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </Field>
            <Field label="To branch" required>
              <select value={form.to_branch_id} onChange={(e) => setForm({ ...form, to_branch_id: e.target.value })}>
                <option value="">Select…</option>
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Notes"><input value={form.notes || ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Optional — e.g. weekly replenishment" /></Field>
          <div className="row" style={{ justifyContent: "space-between", margin: "4px 0 8px" }}>
            <strong style={{ fontSize: 13 }}>Products</strong>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setForm((f: any) => ({ ...f, lines: [...(f.lines || []), newLine()] }))}>
              <Plus size={14} /> Add product
            </button>
          </div>
          {(form.lines || []).map((ln: any, i: number) => (
            <div key={ln.key} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12, marginBottom: 10 }}>
              <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                <span className="muted">Line {i + 1}</span>
                {(form.lines || []).length > 1 && (
                  <button type="button" className="icon-btn" style={{ width: 30, height: 30 }} title="Remove line"
                    onClick={() => setForm((f: any) => ({ ...f, lines: f.lines.filter((_: any, idx: number) => idx !== i) }))}>
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
              <div className="grid grid-2">
                <Field label="Product" required>
                  <SearchSelect
                    value={ln.product_id}
                    options={pickerProducts}
                    placeholder="Type product name / SKU…"
                    onChange={(id) => setLine(i, { product_id: id })}
                    onQuery={searchProducts}
                    getLabel={(p) => `${p.name}${p.sku ? ` · ${p.sku}` : ""}`}
                  />
                </Field>
                <Field label="Quantity" required>
                  <input type="number" value={ln.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} />
                </Field>
              </div>
            </div>
          ))}
        </Modal>
      )}

      {view && (
        <Modal title={`Transfer ${view.transfer_no}`} onClose={() => setView(null)} wide
          footer={<>
            <button className="btn btn-ghost" onClick={() => setView(null)}>Close</button>
            <button className="btn btn-primary" onClick={() => printTransferReceipt(view)}><Printer size={16} /> Print</button>
          </>}>
          <div className="row mb-16" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div><div className="muted">Date</div><strong>{view.transfer_date}</strong></div>
            <div><div className="muted">From</div><strong>{view.from_branch || bname(view.from_branch_id)}</strong></div>
            <div><div className="muted">To</div><strong>{view.to_branch || bname(view.to_branch_id)}</strong></div>
            <div><div className="muted">Status</div><Badge tone={tone(view.status)}>{view.status}</Badge></div>
          </div>
          {view.notes && <p className="muted" style={{ marginTop: 0 }}>{view.notes}</p>}
          <Table
            columns={[
              { key: "product_name", label: "Product" },
              { key: "batch_no", label: "Batch", render: (r) => r.batch_no || "—" },
              { key: "expiry_date", label: "Expiry", render: (r) => r.expiry_date || "—" },
              { key: "quantity", label: "Qty", num: true },
            ]}
            rows={view.items || []}
            empty="No lines"
          />
        </Modal>
      )}
    </div>
  );
}
