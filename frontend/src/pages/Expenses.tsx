import { useEffect, useState } from "react";
import { Plus, ReceiptIndianRupee } from "lucide-react";
import { api } from "../api";
import { inr } from "../format";
import { Badge, Card, ExportButtons, Field, Loading, Modal, PageHeader, Table, BranchSelect } from "../components/ui";
import { PaymentSelect } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
import { useAuth } from "../auth";
import { seesAllBranches } from "../roles";
import * as V from "../validate";

const monthStart = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
};
const today = () => new Date().toISOString().slice(0, 10);

export default function Expenses() {
  const { user } = useAuth();
  const { bundle } = useConfigBundle();
  const allBranches = seesAllBranches(user);
  const [rows, setRows] = useState<any[] | null>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [cats, setCats] = useState<any[]>([]);
  const [branchId, setBranchId] = useState(0);
  const [category, setCategory] = useState("");
  const [start, setStart] = useState(monthStart);
  const [end, setEnd] = useState(today);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<any>({});
  const [err, setErr] = useState("");

  const load = () => {
    setRows(null);
    api.expenses({
      branchId: branchId || undefined,
      start, end,
      category: category || undefined,
    }).then(setRows).catch(() => setRows([]));
  };

  useEffect(() => {
    api.branches().then((b) => {
      setBranches(b);
      setForm((f: any) => ({ ...f, branch_id: b[0]?.id }));
      if (!allBranches && b[0]) setBranchId(b[0].id);
    }).catch(() => {});
    api.expenseCategories().then(setCats).catch(() => setCats([]));
  }, []);
  useEffect(() => { load(); }, [branchId, category, start, end]);

  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      form.branch_id ? null : "Select a branch.",
      form.category ? null : "Select a category.",
      V.positive(form.amount, "Amount"),
    );
    if (msg) { setErr(msg); return; }
    try {
      await api.createExpense({
        branch_id: Number(form.branch_id),
        expense_date: form.expense_date || today(),
        category: form.category,
        payee: form.payee,
        amount: Number(form.amount),
        mode: form.mode || "cash",
        note: form.note,
      });
      setOpen(false); load();
    } catch (e: any) { setErr(e.message); }
  };

  if (!rows) return <Loading />;
  const total = rows.reduce((s, r) => s + Number(r.amount || 0), 0);

  return (
    <div>
      <PageHeader
        title="Expenses"
        subtitle="Transport, salary, rent and other operating costs — posted to the ledger"
        actions={
          <div className="row">
            <ExportButtons title="Expenses" columns={[
              { key: "expense_date", label: "Date" }, { key: "branch_name", label: "Branch" },
              { key: "category", label: "Category" }, { key: "payee", label: "Payee" },
              { key: "amount", label: "Amount", num: true, money: true },
            ]} rows={rows || []} />
            <button className="btn btn-primary" onClick={() => { setErr(""); setForm({ branch_id: branches[0]?.id, category: "transport", mode: "cash", expense_date: today() }); setOpen(true); }}><Plus size={16} /> Record Expense</button>
          </div>
        }
      />
      <Card title="Filters" icon={<ReceiptIndianRupee size={16} />}>
        <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
          <BranchSelect value={branchId} onChange={setBranchId} branches={branches} allowAll={allBranches} />
          <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ width: "auto" }}>
            <option value="">All categories</option>
            {cats.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} style={{ width: "auto" }} />
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} style={{ width: "auto" }} />
          <span className="muted" style={{ marginLeft: "auto" }}>Period total <strong>{inr(total)}</strong></span>
        </div>
        <Table
          columns={[
            { key: "expense_date", label: "Date" },
            { key: "branch_name", label: "Branch" },
            { key: "category", label: "Category", render: (r) => <Badge tone="info">{r.category}</Badge> },
            { key: "payee", label: "Payee", render: (r) => r.payee || "—" },
            { key: "mode", label: "Paid by", render: (r) => r.mode },
            { key: "note", label: "Note", render: (r) => r.note || "—" },
            { key: "amount", label: "Amount", num: true, render: (r) => <strong>{inr(r.amount)}</strong> },
          ]}
          rows={rows}
          empty="No expenses in this period"
        />
      </Card>

      {open && (
        <Modal title="Record Expense" onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={submit}>Save</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="Branch" required>
              <select value={form.branch_id || ""} onChange={(e) => setForm({ ...form, branch_id: e.target.value })}>
                {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </Field>
            <Field label="Date" required><input type="date" value={form.expense_date || today()} onChange={(e) => setForm({ ...form, expense_date: e.target.value })} /></Field>
            <Field label="Category">
              <select value={form.category || "transport"} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {cats.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
                {cats.length === 0 && <>
                  <option value="transport">Transport charges</option>
                  <option value="salary">Employee salary</option>
                  <option value="rent">Rent</option>
                  <option value="electricity">Electricity</option>
                  <option value="other">Other</option>
                </>}
              </select>
            </Field>
            <Field label="Payee / employee"><input value={form.payee || ""} onChange={(e) => setForm({ ...form, payee: e.target.value })} placeholder="Transporter / staff name" /></Field>
            <Field label="Amount (₹)" required><input type="number" min={0} step="0.01" value={form.amount || ""} onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
            <Field label="Paid from">
              <PaymentSelect value={form.mode || "cash"} onChange={(mode) => setForm({ ...form, mode })} use="expense" bundle={bundle} />
            </Field>
            <Field label="Note"><input value={form.note || ""} onChange={(e) => setForm({ ...form, note: e.target.value })} placeholder="Optional" /></Field>
          </div>
        </Modal>
      )}
    </div>
  );
}
