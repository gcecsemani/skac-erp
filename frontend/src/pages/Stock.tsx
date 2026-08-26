import { useEffect, useMemo, useState } from "react";
import { PackagePlus } from "lucide-react";
import { api } from "../api";
import { matchesQuery, num } from "../format";
import { Badge, BranchSelect, Card, ExportButtons, Field, Loading, Modal, PageHeader, SearchInput, SearchSelect, Table } from "../components/ui";
import * as V from "../validate";

export default function Stock() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [branchId, setBranchId] = useState(0);
  const [expiry, setExpiry] = useState("all");
  const [form, setForm] = useState<any>({ branch_id: "", product_id: "", batch_no: "", quantity: "", mfg_date: "", expiry_date: "", purchase_price: "" });

  const load = () => api.stock().then(setRows).catch(() => setRows([]));
  useEffect(() => {
    load();
    api.products(undefined, undefined, 80).then(setProducts).catch(() => {});
    api.branches().then((b) => { setBranches(b); setForm((f: any) => ({ ...f, branch_id: b[0]?.id || "" })); }).catch(() => {});
  }, []);

  const searchProducts = (query: string) => {
    api.products(query || undefined, undefined, 40).then(setProducts).catch(() => {});
  };

  const daysTo = (d: string | null) => d ? Math.round((+new Date(d) - Date.now()) / 86400000) : null;

  const filtered = useMemo(() => {
    return (rows || []).filter((r) => {
      if (branchId && r.branch_id !== branchId) return false;
      if (!matchesQuery(q, r.product, r.batch_no, r.quantity)) return false;
      const d = daysTo(r.expiry_date);
      if (expiry === "expired" && !(d !== null && d < 0)) return false;
      if (expiry === "soon" && !(d !== null && d >= 0 && d <= 30)) return false;
      return true;
    });
  }, [rows, q, branchId, expiry]);

  const openReceive = () => {
    setErr("");
    setForm({
      branch_id: branches[0]?.id || "", product_id: "", batch_no: "", quantity: "",
      mfg_date: "", expiry_date: "", purchase_price: "",
    });
    setOpen(true);
    api.products(undefined, undefined, 80).then(setProducts).catch(() => {});
  };

  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      form.branch_id ? null : "Select a branch.",
      form.product_id ? null : "Select a product.",
      V.required(form.batch_no, "Batch number"),
      V.positive(form.quantity, "Quantity"),
      form.purchase_price ? V.nonNegative(form.purchase_price, "Purchase price") : null,
    );
    if (msg) { setErr(msg); return; }
    try {
      await api.receiveStock({
        branch_id: Number(form.branch_id), product_id: Number(form.product_id),
        batch_no: form.batch_no, quantity: Number(form.quantity),
        mfg_date: form.mfg_date || null, expiry_date: form.expiry_date || null,
        purchase_price: form.purchase_price ? Number(form.purchase_price) : 0,
      });
      setOpen(false); load();
    } catch (e: any) { setErr(e.message); }
  };

  if (!rows) return <Loading />;

  return (
    <div>
      <PageHeader
        title="Stock on Hand"
        subtitle="Batch & expiry-wise stock across branches"
        actions={
          <div className="row">
            <ExportButtons title="Stock on hand" columns={[
              { key: "product", label: "Product" }, { key: "batch_no", label: "Batch" },
              { key: "expiry_date", label: "Expiry" }, { key: "quantity", label: "Qty", num: true },
            ]} rows={filtered} />
            <button className="btn btn-primary" onClick={openReceive}><PackagePlus size={16} /> Receive Stock</button>
          </div>
        }
      />
      <Card>
        <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
          <SearchInput value={q} onChange={setQ} placeholder="Search product or batch…" />
          <BranchSelect value={branchId} onChange={setBranchId} branches={branches} />
          <select value={expiry} onChange={(e) => setExpiry(e.target.value)} style={{ width: "auto" }}>
            <option value="all">All expiry</option>
            <option value="soon">Expiring in 30 days</option>
            <option value="expired">Expired</option>
          </select>
        </div>
        <Table
          columns={[
            { key: "product", label: "Product" },
            { key: "batch_no", label: "Batch" },
            { key: "branch_id", label: "Branch", render: (r) => branches.find((b) => b.id === r.branch_id)?.name || r.branch_id },
            { key: "expiry_date", label: "Expiry", render: (r) => {
              const d = daysTo(r.expiry_date);
              return r.expiry_date ? <Badge tone={d! < 0 ? "danger" : d! <= 30 ? "warn" : "neutral"}>{r.expiry_date}</Badge> : "—";
            } },
            { key: "quantity", label: "Qty", num: true, render: (r) => <strong>{num(r.quantity)}</strong> },
          ]}
          rows={filtered}
          empty={rows.length ? "No stock matches the filters" : "No stock recorded"}
        />
      </Card>

      {open && (
        <Modal title="Receive Stock (GRN)" onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={submit}>Receive</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="Branch" required><select value={form.branch_id} onChange={(e) => setForm({ ...form, branch_id: e.target.value })}>{branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></Field>
            <Field label="Product" required>
              <SearchSelect
                value={form.product_id}
                options={products}
                placeholder="Type product name / SKU…"
                onChange={(id) => setForm({ ...form, product_id: id })}
                onQuery={searchProducts}
                getLabel={(p) => `${p.name}${p.sku ? ` · ${p.sku}` : ""}`}
              />
            </Field>
            <Field label="Batch no" required><input value={form.batch_no} onChange={(e) => setForm({ ...form, batch_no: e.target.value })} /></Field>
            <Field label="Quantity" required><input type="number" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></Field>
            <Field label="Mfg date"><input type="date" value={form.mfg_date} onChange={(e) => setForm({ ...form, mfg_date: e.target.value })} /></Field>
            <Field label="Expiry date"><input type="date" value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} /></Field>
            <Field label="Purchase price"><input type="number" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} /></Field>
          </div>
        </Modal>
      )}
    </div>
  );
}
