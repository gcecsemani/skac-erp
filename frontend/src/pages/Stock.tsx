import { useEffect, useMemo, useState } from "react";
import { PackagePlus, Undo2 } from "lucide-react";
import { api } from "../api";
import { matchesQuery, num } from "../format";
import { Badge, BranchSelect, Card, ExportButtons, Field, Loading, Modal, PageHeader, SearchInput, SearchSelect, Table } from "../components/ui";
import * as V from "../validate";

export default function Stock() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [correct, setCorrect] = useState<any | null>(null);
  const [correctForm, setCorrectForm] = useState<any>({ quantity: "", reason: "", relocate: false, branch_id: "", product_id: "", batch_no: "" });
  const [correctErr, setCorrectErr] = useState("");
  const [correcting, setCorrecting] = useState(false);
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
        subtitle="Batch & expiry-wise stock. Use Correct to undo a wrong receive (wrong shop or product)."
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
            { key: "actions", label: "", render: (r) => (
              <button className="btn btn-ghost btn-sm" title="Correct wrong receive" onClick={() => {
                setCorrectErr("");
                setCorrect(r);
                setCorrectForm({
                  quantity: String(r.quantity), reason: "", relocate: false,
                  branch_id: r.branch_id, product_id: "", batch_no: r.batch_no,
                });
                api.products(undefined, undefined, 80).then(setProducts).catch(() => {});
              }}>
                <Undo2 size={14} /> Correct
              </button>
            ) },
          ]}
          rows={filtered}
          empty={rows.length ? "No stock matches the filters" : "No stock recorded"}
          pageSize={50}
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

      {correct && (
        <Modal title="Correct stock" onClose={() => setCorrect(null)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setCorrect(null)} disabled={correcting}>Cancel</button>
            <button className="btn btn-danger" onClick={async () => {
              setCorrectErr("");
              const qty = Number(correctForm.quantity);
              const msg = V.firstError(
                V.positive(correctForm.quantity, "Quantity"),
                qty > Number(correct.quantity) ? `Cannot exceed on-hand ${correct.quantity}.` : null,
                V.minLen(correctForm.reason, "Reason", 3),
                correctForm.relocate && !correctForm.branch_id ? "Select the correct branch." : null,
                correctForm.relocate && !correctForm.product_id ? "Select the correct product." : null,
                correctForm.relocate ? V.required(correctForm.batch_no, "Batch number") : null,
              );
              if (msg) { setCorrectErr(msg); return; }
              setCorrecting(true);
              try {
                const body: any = {
                  branch_id: correct.branch_id, product_id: correct.product_id,
                  batch_id: correct.batch_id, quantity: qty, reason: String(correctForm.reason).trim(),
                };
                if (correctForm.relocate) {
                  body.correct_branch_id = Number(correctForm.branch_id);
                  body.correct_product_id = Number(correctForm.product_id);
                  body.correct_batch_no = correctForm.batch_no;
                }
                await api.adjustStock(body);
                setCorrect(null); load();
              } catch (e: any) { setCorrectErr(e.message); }
              finally { setCorrecting(false); }
            }} disabled={correcting}>{correcting ? "Saving…" : correctForm.relocate ? "Move qty" : "Remove qty"}</button>
          </>}>
          {correctErr && <div className="error">{correctErr}</div>}
          <p className="muted" style={{ marginTop: 0 }}>
            {correct.product} · batch {correct.batch_no} · {branches.find((b) => b.id === correct.branch_id)?.name || "branch"} · on hand <strong>{num(correct.quantity)}</strong>
          </p>
          <p className="muted" style={{ fontSize: 12 }}>
            Stock loaded here with Receive Stock can be corrected. Qty that came from a GRN must be reversed with a purchase return on Purchasing.
          </p>
          <div className="grid grid-2">
            <Field label="Qty to reverse" required>
              <input type="number" value={correctForm.quantity} onChange={(e) => setCorrectForm({ ...correctForm, quantity: e.target.value })} />
            </Field>
            <Field label="Reason" required>
              <input value={correctForm.reason} onChange={(e) => setCorrectForm({ ...correctForm, reason: e.target.value })} placeholder="Wrong branch / wrong product" />
            </Field>
          </div>
          <label className="row" style={{ gap: 8, cursor: "pointer", margin: "8px 0 12px" }}>
            <input type="checkbox" style={{ width: "auto" }} checked={correctForm.relocate}
              onChange={(e) => setCorrectForm({ ...correctForm, relocate: e.target.checked })} />
            Load this qty onto the correct product or branch
          </label>
          {correctForm.relocate && (
            <div className="grid grid-2">
              <Field label="Correct branch" required>
                <select value={correctForm.branch_id} onChange={(e) => setCorrectForm({ ...correctForm, branch_id: e.target.value })}>
                  {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </Field>
              <Field label="Correct product" required>
                <SearchSelect
                  value={correctForm.product_id}
                  options={products}
                  placeholder="Type product name / SKU…"
                  onChange={(id) => setCorrectForm({ ...correctForm, product_id: id })}
                  onQuery={searchProducts}
                  getLabel={(p) => `${p.name}${p.sku ? ` · ${p.sku}` : ""}`}
                />
              </Field>
              <Field label="Batch no" required>
                <input value={correctForm.batch_no} onChange={(e) => setCorrectForm({ ...correctForm, batch_no: e.target.value })} />
              </Field>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}
