import { useEffect, useState } from "react";
import { ArrowLeftRight, Check, Plus, X } from "lucide-react";
import { api } from "../api";
import { Badge, Card, Field, Loading, Modal, PageHeader, Table } from "../components/ui";
import * as V from "../validate";

export default function Transfers() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [products, setProducts] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState<any>({ from_branch_id: "", to_branch_id: "", product_id: "", quantity: "" });

  const load = () => api.transfers().then(setRows).catch(() => setRows([]));
  useEffect(() => {
    load();
    api.branches().then(setBranches).catch(() => {});
    api.products().then(setProducts).catch(() => {});
  }, []);

  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      form.from_branch_id ? null : "Select the from branch.",
      form.to_branch_id ? null : "Select the to branch.",
      String(form.from_branch_id) === String(form.to_branch_id) ? "From and to branches must be different." : null,
      form.product_id ? null : "Select a product.",
      V.positive(form.quantity, "Quantity"),
    );
    if (msg) { setErr(msg); return; }
    try {
      await api.createTransfer({
        from_branch_id: Number(form.from_branch_id), to_branch_id: Number(form.to_branch_id),
        items: [{ product_id: Number(form.product_id), quantity: Number(form.quantity) }],
      });
      setOpen(false); load();
    } catch (e: any) { setErr(e.message); }
  };

  const act = async (id: number, approve: boolean) => {
    try { approve ? await api.approveTransfer(id) : await api.rejectTransfer(id); load(); }
    catch (e: any) { alert(e.message); }
  };

  if (!rows) return <Loading />;
  const bname = (id: number) => branches.find((b) => b.id === id)?.name || id;
  const tone = (s: string) => (s === "received" ? "success" : s === "rejected" ? "danger" : "warn");

  return (
    <div>
      <PageHeader
        title="Stock Transfers"
        subtitle="Move stock between branches with an approval workflow"
        actions={<button className="btn btn-primary" onClick={() => setOpen(true)}><Plus size={16} /> New Transfer</button>}
      />
      <Card>
        <Table
          columns={[
            { key: "transfer_no", label: "Transfer #" },
            { key: "from", label: "From", render: (r) => bname(r.from_branch_id) },
            { key: "arrow", label: "", render: () => <ArrowLeftRight size={15} className="muted" /> },
            { key: "to", label: "To", render: (r) => bname(r.to_branch_id) },
            { key: "items", label: "Items", render: (r) => r.items.map((i: any) => `${i.product_name} ×${i.quantity}`).join(", ") },
            { key: "status", label: "Status", render: (r) => <Badge tone={tone(r.status)}>{r.status}</Badge> },
            { key: "actions", label: "", render: (r) => r.status === "requested" ? (
              <div className="row" style={{ gap: 6 }}>
                <button className="btn btn-primary btn-sm" onClick={() => act(r.id, true)}><Check size={14} /></button>
                <button className="btn btn-ghost btn-sm" onClick={() => act(r.id, false)}><X size={14} /></button>
              </div>
            ) : null },
          ]}
          rows={rows}
          empty="No transfers yet"
        />
      </Card>

      {open && (
        <Modal title="New Stock Transfer" onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={submit}>Request</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="From branch" required><select value={form.from_branch_id} onChange={(e) => setForm({ ...form, from_branch_id: e.target.value })}><option value="">Select…</option>{branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></Field>
            <Field label="To branch" required><select value={form.to_branch_id} onChange={(e) => setForm({ ...form, to_branch_id: e.target.value })}><option value="">Select…</option>{branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></Field>
            <Field label="Product" required><select value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })}><option value="">Select…</option>{products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></Field>
            <Field label="Quantity" required><input type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></Field>
          </div>
        </Modal>
      )}
    </div>
  );
}
