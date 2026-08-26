import { useEffect, useState } from "react";
import { MapPin, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "../api";
import { invalidateConfigBundle } from "../configBundle";
import { Badge, Card, Field, Loading, Modal, PageHeader, Table } from "../components/ui";

const TABS = [
  { id: "locations", label: "Locations" },
  { id: "units", label: "Units" },
  { id: "gst_rate", label: "GST rates" },
  { id: "hsn", label: "HSN codes" },
  { id: "expense_category", label: "Expense categories" },
  { id: "payment_mode", label: "Payment modes" },
  { id: "toxicity_class", label: "Toxicity" },
  { id: "state", label: "States" },
] as const;

const USE_IN = [
  { key: "pos", label: "POS" },
  { key: "khata", label: "Khata collection" },
  { key: "expense", label: "Expenses" },
  { key: "purchase", label: "Vendor payments" },
  { key: "invoice_filter", label: "Invoice filter" },
];

type Item = {
  id: number;
  kind: string;
  parent_id: number | null;
  code: string;
  name: string;
  extra: Record<string, any>;
  is_active: boolean;
  sort_order: number;
};

const emptyForm = { name: "", code: "", extra: {} as Record<string, any>, is_active: true };

export default function Config() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("locations");
  return (
    <div>
      <PageHeader
        title="Master data"
        subtitle="Districts, villages and other lists used on farmer, product, expense and payment screens. Changing a name here does not rewrite past bills."
      />
      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={`tab ${tab === t.id ? "active" : ""}`} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>
      {tab === "locations" && <LocationsTab />}
      {tab === "units" && <SimpleTab kind="unit" title="Units" hint="Used as the product base unit (bag, kg, litre…)." />}
      {tab === "gst_rate" && <GstTab />}
      {tab === "hsn" && <HsnTab />}
      {tab === "expense_category" && <ExpenseTab />}
      {tab === "payment_mode" && <PaymentTab />}
      {tab === "toxicity_class" && <SimpleTab kind="toxicity_class" title="Toxicity classes" hint="Shown on pesticide products." />}
      {tab === "state" && <StateTab />}
    </div>
  );
}

function LocationsTab() {
  const [districts, setDistricts] = useState<Item[] | null>(null);
  const [villages, setVillages] = useState<Item[]>([]);
  const [sel, setSel] = useState<Item | null>(null);
  const [err, setErr] = useState("");
  const [modal, setModal] = useState<"district" | "village" | null>(null);
  const [edit, setEdit] = useState<Item | null>(null);
  const [form, setForm] = useState(emptyForm);

  const loadDistricts = async (keepId?: number) => {
    const rows = await api.configItems("district", undefined, true);
    setDistricts(rows);
    const keep = rows.find((r: Item) => r.id === (keepId ?? sel?.id)) || rows[0] || null;
    setSel(keep);
    if (keep) setVillages(await api.configItems("village", keep.id, true));
    else setVillages([]);
  };

  useEffect(() => { loadDistricts().catch(() => setDistricts([])); }, []);

  const pickDistrict = async (d: Item) => {
    setSel(d);
    setVillages(await api.configItems("village", d.id, true));
  };

  const openAdd = (kind: "district" | "village") => {
    setErr(""); setEdit(null); setForm(emptyForm); setModal(kind);
  };
  const openEdit = (kind: "district" | "village", item: Item) => {
    setErr(""); setEdit(item); setForm({ name: item.name, code: item.code, extra: item.extra || {}, is_active: item.is_active }); setModal(kind);
  };

  const save = async () => {
    setErr("");
    if (!form.name.trim()) { setErr("Enter a name."); return; }
    try {
      if (modal === "village" && !sel) { setErr("Select a district first."); return; }
      if (edit) {
        await api.updateConfigItem(edit.id, { name: form.name.trim(), is_active: form.is_active });
      } else if (modal === "district") {
        await api.createConfigItem({ kind: "district", name: form.name.trim() });
      } else {
        await api.createConfigItem({ kind: "village", name: form.name.trim(), parent_id: sel!.id });
      }
      invalidateConfigBundle();
      setModal(null);
      await loadDistricts(modal === "village" ? sel?.id : edit?.id);
    } catch (e: any) { setErr(e.message); }
  };

  const remove = async (item: Item, kind: "district" | "village") => {
    const extra = kind === "district" ? " Villages under it will also be removed from the list." : "";
    if (!confirm(`Remove "${item.name}" from the list? Existing farmer records keep the old spelling.${extra}`)) return;
    try {
      await api.deleteConfigItem(item.id);
      invalidateConfigBundle();
      await loadDistricts(kind === "district" ? undefined : sel?.id);
    } catch (e: any) { alert(e.message); }
  };

  if (!districts) return <Loading />;
  const selected = sel;

  return (
    <>
      <div className="config-split">
        <Card title="Districts" icon={<MapPin size={16} />} actions={
          <button className="btn btn-primary btn-sm" onClick={() => openAdd("district")}><Plus size={14} /> Add district</button>
        }>
          <ItemList
            rows={districts}
            selectedId={selected?.id}
            onSelect={(r) => pickDistrict(r)}
            onEdit={(r) => openEdit("district", r)}
            onDelete={(r) => remove(r, "district")}
            empty="No districts yet"
          />
        </Card>
        <Card
          title={selected ? `Villages in ${selected.name}` : "Villages"}
          actions={
            <button className="btn btn-primary btn-sm" disabled={!selected} onClick={() => openAdd("village")}>
              <Plus size={14} /> Add village
            </button>
          }
        >
          {!selected ? (
            <p className="muted">Select a district to manage its villages.</p>
          ) : (
            <ItemList
              rows={villages}
              onEdit={(r) => openEdit("village", r)}
              onDelete={(r) => remove(r, "village")}
              empty={`No villages in ${selected.name} yet. Add the ones your cashiers use so farmer forms stay consistent.`}
            />
          )}
        </Card>
      </div>
      <p className="muted" style={{ marginTop: 12, fontSize: 13 }}>
        Farmer add/edit screens pick district first, then village. Add every village you serve so cashiers never type it by hand.
      </p>
      {modal && (
        <Modal
          title={`${edit ? "Edit" : "Add"} ${modal}`}
          onClose={() => setModal(null)}
          footer={<><button className="btn btn-ghost" onClick={() => setModal(null)}>Cancel</button><button className="btn btn-primary" onClick={save}>Save</button></>}
        >
          {err && <div className="error">{err}</div>}
          {modal === "village" && selected && <p className="muted" style={{ marginTop: 0 }}>District: <strong>{selected.name}</strong></p>}
          <Field label="Name" required>
            <input value={form.name} autoFocus onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder={modal === "district" ? "Erode" : "Bhavani"} />
          </Field>
          {edit && (
            <label className="row" style={{ gap: 8, cursor: "pointer" }}>
              <input type="checkbox" style={{ width: "auto" }} checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
              Active (shown on farmer forms)
            </label>
          )}
        </Modal>
      )}
    </>
  );
}

function ItemList({
  rows, selectedId, onSelect, onEdit, onDelete, empty,
}: {
  rows: Item[];
  selectedId?: number;
  onSelect?: (row: Item) => void;
  onEdit: (row: Item) => void;
  onDelete: (row: Item) => void;
  empty: string;
}) {
  if (!rows.length) return <p className="muted" style={{ margin: 0 }}>{empty}</p>;
  return (
    <div className="config-list">
      {rows.map((r) => (
        <div
          key={r.id}
          className={`config-list-item ${selectedId === r.id ? "active" : ""} ${r.is_active ? "" : "inactive"}`}
          onClick={() => onSelect?.(r)}
          style={{ cursor: onSelect ? "pointer" : "default" }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 600 }}>{r.name}</div>
            {!r.is_active && <Badge>Inactive</Badge>}
          </div>
          <div className="row" style={{ gap: 4 }} onClick={(e) => e.stopPropagation()}>
            <button className="icon-btn" style={{ width: 30, height: 30 }} title="Edit" onClick={() => onEdit(r)}><Pencil size={14} /></button>
            <button className="icon-btn" style={{ width: 30, height: 30 }} title="Remove" onClick={() => onDelete(r)}><Trash2 size={14} /></button>
          </div>
        </div>
      ))}
    </div>
  );
}

function useKind(kind: string) {
  const [rows, setRows] = useState<Item[] | null>(null);
  const reload = () => api.configItems(kind, undefined, true).then(setRows).catch(() => setRows([]));
  useEffect(() => { reload(); }, [kind]);
  const after = async () => { invalidateConfigBundle(); await reload(); };
  return { rows, after, reload };
}

function SimpleTab({ kind, title, hint }: { kind: string; title: string; hint: string }) {
  const { rows, after } = useKind(kind);
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Item | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [err, setErr] = useState("");
  if (!rows) return <Loading />;
  return (
    <Card title={title} actions={<button className="btn btn-primary btn-sm" onClick={() => { setErr(""); setEdit(null); setForm(emptyForm); setOpen(true); }}><Plus size={14} /> Add</button>}>
      <p className="muted" style={{ marginTop: 0 }}>{hint}</p>
      <SimpleTable rows={rows} onEdit={(r) => { setErr(""); setEdit(r); setForm({ name: r.name, code: r.code, extra: r.extra || {}, is_active: r.is_active }); setOpen(true); }} onDelete={async (r) => {
        if (!confirm(`Remove "${r.name}"?`)) return;
        try { await api.deleteConfigItem(r.id); await after(); } catch (e: any) { alert(e.message); }
      }} />
      {open && (
        <NameModal title={`${edit ? "Edit" : "Add"} ${title.toLowerCase()}`} err={err} form={form} setForm={setForm} edit={edit}
          onClose={() => setOpen(false)}
          onSave={async () => {
            setErr("");
            if (!form.name.trim()) { setErr("Enter a name."); return; }
            try {
              if (edit) await api.updateConfigItem(edit.id, { name: form.name.trim(), is_active: form.is_active });
              else await api.createConfigItem({ kind, name: form.name.trim() });
              await after(); setOpen(false);
            } catch (e: any) { setErr(e.message); }
          }}
        />
      )}
    </Card>
  );
}

function GstTab() {
  const { rows, after } = useKind("gst_rate");
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Item | null>(null);
  const [rate, setRate] = useState("");
  const [active, setActive] = useState(true);
  const [err, setErr] = useState("");
  if (!rows) return <Loading />;
  return (
    <Card title="GST rates" actions={<button className="btn btn-primary btn-sm" onClick={() => { setErr(""); setEdit(null); setRate(""); setActive(true); setOpen(true); }}><Plus size={14} /> Add</button>}>
      <p className="muted" style={{ marginTop: 0 }}>Product GST % dropdown. Typical values: 0, 5, 12, 18, 28.</p>
      <Table
        columns={[
          { key: "name", label: "Label" },
          { key: "code", label: "Rate %", num: true },
          { key: "is_active", label: "Status", render: (r) => r.is_active ? <Badge tone="success">Active</Badge> : <Badge>Inactive</Badge> },
          { key: "actions", label: "", render: (r) => <RowActions onEdit={() => { setEdit(r); setRate(String(r.extra?.rate ?? r.code)); setActive(r.is_active); setErr(""); setOpen(true); }} onDelete={async () => {
            if (!confirm(`Remove ${r.name}?`)) return;
            try { await api.deleteConfigItem(r.id); await after(); } catch (e: any) { alert(e.message); }
          }} /> },
        ]}
        rows={rows}
        empty="No GST rates"
      />
      {open && (
        <Modal title={edit ? "Edit GST rate" : "Add GST rate"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={async () => {
            setErr("");
            const n = Number(rate);
            if (Number.isNaN(n) || n < 0) { setErr("Enter a valid rate."); return; }
            try {
              const name = `${n}%`;
              if (edit) await api.updateConfigItem(edit.id, { name, extra: { rate: n }, is_active: active });
              else await api.createConfigItem({ kind: "gst_rate", name, code: String(n), extra: { rate: n } });
              await after(); setOpen(false);
            } catch (e: any) { setErr(e.message); }
          }}>Save</button></>}
        >
          {err && <div className="error">{err}</div>}
          <Field label="Rate %" required><input type="number" min={0} step="0.01" value={rate} onChange={(e) => setRate(e.target.value)} /></Field>
          {edit && <ActiveCheck checked={active} onChange={setActive} />}
        </Modal>
      )}
    </Card>
  );
}

function HsnTab() {
  const { rows, after } = useKind("hsn");
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Item | null>(null);
  const [form, setForm] = useState({ code: "", name: "", gst_rate: "", is_active: true });
  const [err, setErr] = useState("");
  if (!rows) return <Loading />;
  return (
    <Card title="HSN codes" actions={<button className="btn btn-primary btn-sm" onClick={() => { setErr(""); setEdit(null); setForm({ code: "", name: "", gst_rate: "", is_active: true }); setOpen(true); }}><Plus size={14} /> Add</button>}>
      <p className="muted" style={{ marginTop: 0 }}>Suggested HSN list on the product form. Picking one can fill GST %.</p>
      <Table
        columns={[
          { key: "code", label: "HSN" },
          { key: "name", label: "Description" },
          { key: "gst", label: "GST %", render: (r) => r.extra?.gst_rate ?? "—" },
          { key: "is_active", label: "Status", render: (r) => r.is_active ? <Badge tone="success">Active</Badge> : <Badge>Inactive</Badge> },
          { key: "actions", label: "", render: (r) => <RowActions onEdit={() => {
            setEdit(r); setErr("");
            setForm({ code: r.code, name: r.name, gst_rate: r.extra?.gst_rate != null ? String(r.extra.gst_rate) : "", is_active: r.is_active });
            setOpen(true);
          }} onDelete={async () => {
            if (!confirm(`Remove HSN ${r.code}?`)) return;
            try { await api.deleteConfigItem(r.id); await after(); } catch (e: any) { alert(e.message); }
          }} /> },
        ]}
        rows={rows}
        empty="No HSN codes"
      />
      {open && (
        <Modal title={edit ? "Edit HSN" : "Add HSN"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={async () => {
            setErr("");
            if (!form.code.trim() || !form.name.trim()) { setErr("Enter HSN code and description."); return; }
            const extra = form.gst_rate === "" ? {} : { gst_rate: Number(form.gst_rate) };
            try {
              if (edit) await api.updateConfigItem(edit.id, { name: form.name.trim(), extra, is_active: form.is_active });
              else await api.createConfigItem({ kind: "hsn", code: form.code.trim(), name: form.name.trim(), extra });
              await after(); setOpen(false);
            } catch (e: any) { setErr(e.message); }
          }}>Save</button></>}
        >
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="HSN code" required><input value={form.code} disabled={!!edit} onChange={(e) => setForm({ ...form, code: e.target.value })} /></Field>
            <Field label="Suggested GST %"><input type="number" value={form.gst_rate} onChange={(e) => setForm({ ...form, gst_rate: e.target.value })} /></Field>
          </div>
          <Field label="Description" required><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          {edit && <ActiveCheck checked={form.is_active} onChange={(v) => setForm({ ...form, is_active: v })} />}
        </Modal>
      )}
    </Card>
  );
}

function ExpenseTab() {
  const { rows, after } = useKind("expense_category");
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Item | null>(null);
  const [form, setForm] = useState({ name: "", code: "", account: "4500", is_active: true });
  const [err, setErr] = useState("");
  if (!rows) return <Loading />;
  return (
    <Card title="Expense categories" actions={<button className="btn btn-primary btn-sm" onClick={() => { setErr(""); setEdit(null); setForm({ name: "", code: "", account: "4500", is_active: true }); setOpen(true); }}><Plus size={14} /> Add</button>}>
      <p className="muted" style={{ marginTop: 0 }}>Categories on the Expenses screen. Ledger account is used when posting (4100 transport, 4200 salary, 4300 rent, 4400 electricity, 4500 other).</p>
      <Table
        columns={[
          { key: "name", label: "Category" },
          { key: "code", label: "Key" },
          { key: "account", label: "Ledger", render: (r) => r.extra?.account || "4500" },
          { key: "is_active", label: "Status", render: (r) => r.is_active ? <Badge tone="success">Active</Badge> : <Badge>Inactive</Badge> },
          { key: "actions", label: "", render: (r) => <RowActions onEdit={() => {
            setEdit(r); setErr("");
            setForm({ name: r.name, code: r.code, account: r.extra?.account || "4500", is_active: r.is_active });
            setOpen(true);
          }} onDelete={async () => {
            if (!confirm(`Remove "${r.name}"? Past expenses keep the old category key.`)) return;
            try { await api.deleteConfigItem(r.id); await after(); } catch (e: any) { alert(e.message); }
          }} /> },
        ]}
        rows={rows}
        empty="No expense categories"
      />
      {open && (
        <Modal title={edit ? "Edit category" : "Add category"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={async () => {
            setErr("");
            if (!form.name.trim()) { setErr("Enter a name."); return; }
            try {
              const extra = { account: form.account || "4500" };
              if (edit) await api.updateConfigItem(edit.id, { name: form.name.trim(), extra, is_active: form.is_active });
              else await api.createConfigItem({ kind: "expense_category", name: form.name.trim(), code: form.code || undefined, extra });
              await after(); setOpen(false);
            } catch (e: any) { setErr(e.message); }
          }}>Save</button></>}
        >
          {err && <div className="error">{err}</div>}
          <Field label="Name" required><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Transport charges" /></Field>
          {!edit && <Field label="Key (optional)"><input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="auto from name" /></Field>}
          <Field label="Ledger account">
            <select value={form.account} onChange={(e) => setForm({ ...form, account: e.target.value })}>
              <option value="4100">4100 Transport</option>
              <option value="4200">4200 Salaries</option>
              <option value="4300">4300 Rent</option>
              <option value="4400">4400 Electricity</option>
              <option value="4500">4500 Other operating</option>
            </select>
          </Field>
          {edit && <ActiveCheck checked={form.is_active} onChange={(v) => setForm({ ...form, is_active: v })} />}
        </Modal>
      )}
    </Card>
  );
}

function PaymentTab() {
  const { rows, after } = useKind("payment_mode");
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Item | null>(null);
  const [form, setForm] = useState({ name: "", code: "", use_in: ["pos"] as string[], is_active: true });
  const [err, setErr] = useState("");
  if (!rows) return <Loading />;
  const toggle = (key: string) => setForm((f) => ({
    ...f,
    use_in: f.use_in.includes(key) ? f.use_in.filter((k) => k !== key) : [...f.use_in, key],
  }));
  return (
    <Card title="Payment modes" actions={<button className="btn btn-primary btn-sm" onClick={() => { setErr(""); setEdit(null); setForm({ name: "", code: "", use_in: ["pos"], is_active: true }); setOpen(true); }}><Plus size={14} /> Add</button>}>
      <p className="muted" style={{ marginTop: 0 }}>Choose where each mode appears. Cash cannot be deleted.</p>
      <Table
        columns={[
          { key: "name", label: "Mode" },
          { key: "code", label: "Key" },
          { key: "use", label: "Used on", render: (r) => (r.extra?.use_in || []).join(", ") || "—" },
          { key: "is_active", label: "Status", render: (r) => r.is_active ? <Badge tone="success">Active</Badge> : <Badge>Inactive</Badge> },
          { key: "actions", label: "", render: (r) => <RowActions onEdit={() => {
            setEdit(r); setErr("");
            setForm({ name: r.name, code: r.code, use_in: r.extra?.use_in || [], is_active: r.is_active });
            setOpen(true);
          }} onDelete={async () => {
            if (!confirm(`Remove "${r.name}"?`)) return;
            try { await api.deleteConfigItem(r.id); await after(); } catch (e: any) { alert(e.message); }
          }} /> },
        ]}
        rows={rows}
        empty="No payment modes"
      />
      {open && (
        <Modal title={edit ? "Edit payment mode" : "Add payment mode"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={async () => {
            setErr("");
            if (!form.name.trim()) { setErr("Enter a name."); return; }
            try {
              const extra = { use_in: form.use_in };
              if (edit) await api.updateConfigItem(edit.id, { name: form.name.trim(), extra, is_active: form.is_active });
              else await api.createConfigItem({ kind: "payment_mode", name: form.name.trim(), code: form.code || undefined, extra });
              await after(); setOpen(false);
            } catch (e: any) { setErr(e.message); }
          }}>Save</button></>}
        >
          {err && <div className="error">{err}</div>}
          <Field label="Name" required><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="UPI" /></Field>
          {!edit && <Field label="Key (optional)"><input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="upi" /></Field>}
          <div className="field">
            <label>Show on</label>
            {USE_IN.map((u) => (
              <label key={u.key} className="row" style={{ gap: 8, cursor: "pointer", marginBottom: 6 }}>
                <input type="checkbox" style={{ width: "auto" }} checked={form.use_in.includes(u.key)} onChange={() => toggle(u.key)} />
                {u.label}
              </label>
            ))}
          </div>
          {edit && <ActiveCheck checked={form.is_active} onChange={(v) => setForm({ ...form, is_active: v })} />}
        </Modal>
      )}
    </Card>
  );
}

function StateTab() {
  const { rows, after } = useKind("state");
  const [open, setOpen] = useState(false);
  const [edit, setEdit] = useState<Item | null>(null);
  const [form, setForm] = useState({ name: "", code: "", is_active: true });
  const [err, setErr] = useState("");
  if (!rows) return <Loading />;
  return (
    <Card title="States" actions={<button className="btn btn-primary btn-sm" onClick={() => { setErr(""); setEdit(null); setForm({ name: "", code: "", is_active: true }); setOpen(true); }}><Plus size={14} /> Add</button>}>
      <p className="muted" style={{ marginTop: 0 }}>Used on the branch form. Code is the GST state code (Tamil Nadu = 33).</p>
      <Table
        columns={[
          { key: "name", label: "State" },
          { key: "code", label: "GST code" },
          { key: "is_active", label: "Status", render: (r) => r.is_active ? <Badge tone="success">Active</Badge> : <Badge>Inactive</Badge> },
          { key: "actions", label: "", render: (r) => <RowActions onEdit={() => {
            setEdit(r); setErr(""); setForm({ name: r.name, code: r.code, is_active: r.is_active }); setOpen(true);
          }} onDelete={async () => {
            if (!confirm(`Remove "${r.name}"?`)) return;
            try { await api.deleteConfigItem(r.id); await after(); } catch (e: any) { alert(e.message); }
          }} /> },
        ]}
        rows={rows}
        empty="No states"
      />
      {open && (
        <Modal title={edit ? "Edit state" : "Add state"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={async () => {
            setErr("");
            if (!form.name.trim() || !form.code.trim()) { setErr("Enter name and GST state code."); return; }
            try {
              if (edit) await api.updateConfigItem(edit.id, { name: form.name.trim(), extra: { state_code: form.code.trim() }, is_active: form.is_active });
              else await api.createConfigItem({ kind: "state", name: form.name.trim(), code: form.code.trim(), extra: { state_code: form.code.trim() } });
              await after(); setOpen(false);
            } catch (e: any) { setErr(e.message); }
          }}>Save</button></>}
        >
          {err && <div className="error">{err}</div>}
          <Field label="State" required><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="GST state code" required><input value={form.code} disabled={!!edit} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="33" /></Field>
          {edit && <ActiveCheck checked={form.is_active} onChange={(v) => setForm({ ...form, is_active: v })} />}
        </Modal>
      )}
    </Card>
  );
}

function SimpleTable({ rows, onEdit, onDelete }: { rows: Item[]; onEdit: (r: Item) => void; onDelete: (r: Item) => void }) {
  return (
    <Table
      columns={[
        { key: "name", label: "Name" },
        { key: "is_active", label: "Status", render: (r) => r.is_active ? <Badge tone="success">Active</Badge> : <Badge>Inactive</Badge> },
        { key: "actions", label: "", render: (r) => <RowActions onEdit={() => onEdit(r)} onDelete={() => onDelete(r)} /> },
      ]}
      rows={rows}
      empty="Nothing here yet"
    />
  );
}

function RowActions({ onEdit, onDelete }: { onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
      <button className="icon-btn" style={{ width: 30, height: 30 }} title="Edit" onClick={onEdit}><Pencil size={14} /></button>
      <button className="icon-btn" style={{ width: 30, height: 30 }} title="Remove" onClick={onDelete}><Trash2 size={14} /></button>
    </div>
  );
}

function NameModal({ title, err, form, setForm, edit, onClose, onSave }: {
  title: string; err: string; form: typeof emptyForm; setForm: (f: typeof emptyForm) => void;
  edit: Item | null; onClose: () => void; onSave: () => void;
}) {
  return (
    <Modal title={title} onClose={onClose}
      footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={onSave}>Save</button></>}>
      {err && <div className="error">{err}</div>}
      <Field label="Name" required><input value={form.name} autoFocus onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
      {edit && <ActiveCheck checked={form.is_active} onChange={(v) => setForm({ ...form, is_active: v })} />}
    </Modal>
  );
}

function ActiveCheck({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="row" style={{ gap: 8, cursor: "pointer" }}>
      <input type="checkbox" style={{ width: "auto" }} checked={checked} onChange={(e) => onChange(e.target.checked)} />
      Active (shown on forms)
    </label>
  );
}
