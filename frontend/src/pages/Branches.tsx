import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Building2 } from "lucide-react";
import { api } from "../api";
import { Card, Field, Loading, Modal, PageHeader, Table } from "../components/ui";
import { ConfigOptions } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
import * as V from "../validate";

const empty = {
  code: "", name: "", address_line1: "", address_line2: "", city: "", district: "",
  state: "Tamil Nadu", state_code: "33", pincode: "", phone: "", gstin: "",
  fco_license_no: "", fco_license_valid_to: "", pesticide_license_no: "", pesticide_license_valid_to: "",
  seed_license_no: "", seed_license_valid_to: "",
  printer_name: "", printer_type: "thermal", thermal_paper_mm: 80,
};

export default function Branches() {
  const { bundle } = useConfigBundle();
  const [rows, setRows] = useState<any[] | null>(null);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<any>(empty);
  const [err, setErr] = useState("");

  const load = () => api.branches().then(setRows).catch(() => setRows([]));
  useEffect(() => { load(); }, []);

  const set = (k: string, v: any) => setForm((f: any) => ({ ...f, [k]: v }));
  const openCreate = () => { setEditId(null); setForm(empty); setErr(""); setOpen(true); };
  const openEdit = (b: any) => {
    setEditId(b.id); setErr("");
    setForm({
      ...empty,
      ...Object.fromEntries(Object.keys(empty).map((k) => [k, b[k] ?? (k === "thermal_paper_mm" ? 80 : k === "printer_type" ? "thermal" : "")])),
    });
    setOpen(true);
  };
  const remove = async (b: any) => {
    if (!confirm(`Delete branch "${b.name}"? Users assigned only to this branch will lose access.`)) return;
    try { await api.deleteBranch(b.id); load(); } catch (e: any) { alert(e.message); }
  };
  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      V.required(form.code, "Code"),
      V.minLen(form.name, "Name", 2),
      V.pincode(form.pincode),
      V.phone(form.phone),
      V.gstin(form.gstin),
    );
    if (msg) { setErr(msg); return; }
    const payload = {
      ...form,
      thermal_paper_mm: Number(form.thermal_paper_mm) || 80,
      fco_license_valid_to: form.fco_license_valid_to || null,
      pesticide_license_valid_to: form.pesticide_license_valid_to || null,
      seed_license_valid_to: form.seed_license_valid_to || null,
    };
    try {
      if (editId) await api.updateBranch(editId, payload);
      else await api.createBranch(payload);
      setOpen(false); load();
    } catch (e: any) { setErr(e.message); }
  };

  if (!rows) return <Loading />;

  return (
    <div>
      <PageHeader
        title="Branches"
        subtitle="Name, address, GSTIN, licenses and thermal printer settings. Assign staff on Users & Audit."
        actions={<button className="btn btn-primary" onClick={openCreate}><Plus size={16} /> Add Branch</button>}
      />
      <Card title="Selling locations" icon={<Building2 size={16} />}>
        <Table
          columns={[
            { key: "code", label: "Code" },
            { key: "name", label: "Branch" },
            { key: "address", label: "Address", render: (r) => [r.address_line1, r.city, r.district].filter(Boolean).join(", ") || "—" },
            { key: "phone", label: "Phone", render: (r) => r.phone || "—" },
            { key: "gstin", label: "GSTIN", render: (r) => r.gstin || "—" },
            { key: "printer", label: "Printer", render: (r) => `${r.thermal_paper_mm || 80}mm${r.printer_name ? ` · ${r.printer_name}` : ""}` },
            { key: "actions", label: "", render: (r) => (
              <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                <button className="icon-btn" style={{ width: 30, height: 30 }} title="Edit" onClick={() => openEdit(r)}><Pencil size={14} /></button>
                <button className="icon-btn" style={{ width: 30, height: 30 }} title="Delete" onClick={() => remove(r)}><Trash2 size={14} /></button>
              </div>
            ) },
          ]}
          rows={rows}
          empty="No branches yet"
        />
      </Card>
      <p className="muted" style={{ marginTop: 12, fontSize: 13 }}>
        User access is assigned per branch on <strong>Users & Audit</strong> (multi-select Branch access). Owner sees all branches; cashiers only the assigned branch.
        Thermal print uses the OS print dialog — set paper width and printer name here so cashiers pick the right device.
      </p>

      {open && (
        <Modal title={editId ? "Edit Branch" : "Add Branch"} onClose={() => setOpen(false)} wide
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={submit}>{editId ? "Save" : "Create"}</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="Code" required><input value={form.code} onChange={(e) => set("code", e.target.value)} placeholder="BR01" /></Field>
            <Field label="Name" required><input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Erode Main" /></Field>
            <Field label="Address line 1"><input value={form.address_line1} onChange={(e) => set("address_line1", e.target.value)} /></Field>
            <Field label="Address line 2"><input value={form.address_line2} onChange={(e) => set("address_line2", e.target.value)} /></Field>
            <Field label="City"><input value={form.city} onChange={(e) => set("city", e.target.value)} /></Field>
            <Field label="District">
              {bundle.districts.length ? (
                <select value={form.district} onChange={(e) => set("district", e.target.value)}>
                  <option value="">Select district</option>
                  <ConfigOptions items={bundle.districts} current={form.district} />
                </select>
              ) : (
                <input value={form.district} onChange={(e) => set("district", e.target.value)} />
              )}
            </Field>
            <Field label="State">
              {bundle.states.length ? (
                <select value={form.state} onChange={(e) => {
                  const name = e.target.value;
                  const hit = bundle.states.find((s) => s.name === name);
                  setForm((f: any) => ({
                    ...f,
                    state: name,
                    state_code: hit?.extra?.state_code || hit?.code || f.state_code,
                  }));
                }}>
                  <option value="">Select state</option>
                  <ConfigOptions items={bundle.states} current={form.state} />
                </select>
              ) : (
                <input value={form.state} onChange={(e) => set("state", e.target.value)} />
              )}
            </Field>
            <Field label="GST state code"><input value={form.state_code} onChange={(e) => set("state_code", e.target.value)} placeholder="33" /></Field>
            <Field label="Pincode"><input value={form.pincode} onChange={(e) => set("pincode", e.target.value)} /></Field>
            <Field label="Phone"><input value={form.phone} onChange={(e) => set("phone", e.target.value)} /></Field>
            <Field label="GSTIN"><input value={form.gstin} onChange={(e) => set("gstin", e.target.value)} /></Field>
            <Field label="FCO license"><input value={form.fco_license_no} onChange={(e) => set("fco_license_no", e.target.value)} /></Field>
            <Field label="FCO valid to"><input type="date" value={form.fco_license_valid_to || ""} onChange={(e) => set("fco_license_valid_to", e.target.value)} /></Field>
            <Field label="Pesticide license"><input value={form.pesticide_license_no} onChange={(e) => set("pesticide_license_no", e.target.value)} /></Field>
            <Field label="Pesticide valid to"><input type="date" value={form.pesticide_license_valid_to || ""} onChange={(e) => set("pesticide_license_valid_to", e.target.value)} /></Field>
            <Field label="Seed license"><input value={form.seed_license_no} onChange={(e) => set("seed_license_no", e.target.value)} /></Field>
            <Field label="Seed valid to"><input type="date" value={form.seed_license_valid_to || ""} onChange={(e) => set("seed_license_valid_to", e.target.value)} /></Field>
            <Field label="Printer type">
              <select value={form.printer_type} onChange={(e) => set("printer_type", e.target.value)}>
                <option value="thermal">Thermal receipt</option>
                <option value="a4">A4 / laser</option>
              </select>
            </Field>
            <Field label="Paper width">
              <select value={form.thermal_paper_mm} onChange={(e) => set("thermal_paper_mm", Number(e.target.value))}>
                <option value={80}>80 mm</option>
                <option value={58}>58 mm</option>
              </select>
            </Field>
            <Field label="Printer name (hint in print dialog)">
              <input value={form.printer_name} onChange={(e) => set("printer_name", e.target.value)} placeholder="e.g. TVS RP 3230 — Erode" />
            </Field>
          </div>
        </Modal>
      )}
    </div>
  );
}
