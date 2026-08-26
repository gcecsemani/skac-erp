import { useEffect, useState } from "react";
import { Plus, Truck, FileText, PackageCheck, IndianRupee, Pencil, Trash2, Search, BookOpen } from "lucide-react";
import { api } from "../api";
import { inr } from "../format";
import { Badge, Card, ExportButtons, Field, Loading, Modal, PageHeader, SearchSelect, Table } from "../components/ui";
import { PaymentSelect } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
import * as V from "../validate";

export default function Purchasing() {
  const { bundle } = useConfigBundle();
  const [tab, setTab] = useState("vendors");
  const [vendors, setVendors] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [grns, setGrns] = useState<any[]>([]);
  const [branches, setBranches] = useState<any[]>([]);
  const [pickerVendors, setPickerVendors] = useState<any[]>([]);
  const [pickerProducts, setPickerProducts] = useState<any[]>([]);
  const [ready, setReady] = useState(false);
  const [modal, setModal] = useState<string | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const [form, setForm] = useState<any>({});
  const [vendorQ, setVendorQ] = useState("");
  const [orderQ, setOrderQ] = useState("");
  const [grnQ, setGrnQ] = useState("");
  const [ledger, setLedger] = useState<any | null>(null);

  const loadAll = async (vq?: string, oq?: string, gq?: string) => {
    const [v, o, g] = await Promise.all([
      api.vendors((vq !== undefined ? vq : vendorQ) || undefined),
      api.purchaseOrders((oq !== undefined ? oq : orderQ) || undefined),
      api.grns((gq !== undefined ? gq : grnQ) || undefined),
    ]);
    setVendors(v); setOrders(o); setGrns(g);
  };
  useEffect(() => {
    Promise.all([loadAll(), api.branches().then(setBranches)])
      .finally(() => setReady(true));
  }, []);

  const searchProducts = (q: string) => {
    api.products(q || undefined, undefined, 40).then(setPickerProducts).catch(() => {});
  };
  const searchVendors = (q: string) => {
    api.vendors(q || undefined).then(setPickerVendors).catch(() => {});
  };

  const openModal = (m: string) => {
    setEditId(null);
    setForm({ branch_id: branches[0]?.id, vendor_id: vendors[0]?.id });
    setErr("");
    setModal(m);
    setPickerVendors(vendors);
    api.products(undefined, undefined, 80).then(setPickerProducts).catch(() => setPickerProducts([]));
  };
  const openEditVendor = (v: any) => { setEditId(v.id); setForm({ name: v.name, gstin: v.gstin, phone: v.phone }); setErr(""); setModal("vendor"); };
  const removeVendor = async (v: any) => {
    if (!confirm(`Delete vendor "${v.name}"?`)) return;
    try { await api.deleteVendor(v.id); await loadAll(); } catch (e: any) { alert(e.message); }
  };
  const openLedger = async (v: any) => {
    try { setLedger(await api.vendorLedger(v.id)); } catch (e: any) { alert(e.message); }
  };

  const save = async () => {
    setErr("");
    const msg =
      modal === "vendor" ? V.firstError(V.minLen(form.name, "Vendor name", 2), V.gstin(form.gstin), V.phone(form.phone))
      : modal === "po" ? V.firstError(
          form.branch_id ? null : "Select a branch.",
          form.vendor_id ? null : "Select a vendor.",
          form.product_id ? null : "Select a product.",
          V.positive(form.quantity, "Quantity"),
          V.nonNegative(form.unit_price || 0, "Unit price"),
        )
      : modal === "grn" ? V.firstError(
          form.branch_id ? null : "Select a branch.",
          form.vendor_id ? null : "Select a vendor.",
          form.product_id ? null : "Select a product.",
          V.required(form.batch_no, "Batch number"),
          V.positive(form.quantity, "Quantity"),
        )
      : modal === "pay" ? V.firstError(
          form.vendor_id ? null : "Select a vendor.",
          V.positive(form.amount, "Amount"),
        )
      : null;
    if (msg) { setErr(msg); return; }
    try {
      if (modal === "vendor" && editId) await api.updateVendor(editId, { name: form.name, gstin: form.gstin, phone: form.phone });
      else if (modal === "vendor") await api.createVendor({ name: form.name, gstin: form.gstin, phone: form.phone });
      if (modal === "po") {
        if (!form.vendor_id || !form.product_id) { setErr("Select a vendor and a product."); return; }
        await api.createPO({ branch_id: Number(form.branch_id), vendor_id: Number(form.vendor_id), items: [{ product_id: Number(form.product_id), quantity: Number(form.quantity), unit_price: Number(form.unit_price || 0) }] });
      }
      if (modal === "grn") {
        if (!form.vendor_id || !form.product_id) { setErr("Select a vendor and a product."); return; }
        await api.createGRN({ branch_id: Number(form.branch_id), vendor_id: Number(form.vendor_id), vendor_invoice_no: form.vendor_invoice_no, items: [{ product_id: Number(form.product_id), batch_no: form.batch_no, quantity: Number(form.quantity), unit_price: Number(form.unit_price || 0), expiry_date: form.expiry_date || null }] });
      }
      if (modal === "pay") await api.vendorPayment({ vendor_id: Number(form.vendor_id), branch_id: Number(form.branch_id), amount: Number(form.amount), mode: form.mode || "cash" });
      setModal(null); await loadAll();
    } catch (e: any) { setErr(e.message); }
  };

  if (!ready) return <Loading />;

  return (
    <div>
      <PageHeader title="Purchasing" subtitle="Vendors, purchase orders, goods receipt, payment ledger"
        actions={<ExportButtons
          title={tab === "vendors" ? "Vendors" : tab === "orders" ? "Purchase orders" : "Goods receipts"}
          columns={tab === "vendors"
            ? [{ key: "name", label: "Vendor" }, { key: "gstin", label: "GSTIN" }, { key: "phone", label: "Phone" }, { key: "outstanding_balance", label: "Payable", num: true, money: true }]
            : tab === "orders"
              ? [{ key: "po_no", label: "PO #" }, { key: "vendor", label: "Vendor" }, { key: "order_date", label: "Date" }, { key: "status", label: "Status" }, { key: "expected_total", label: "Value", num: true, money: true }]
              : [{ key: "grn_no", label: "GRN #" }, { key: "vendor", label: "Vendor" }, { key: "received_date", label: "Date" }, { key: "vendor_invoice_no", label: "Vendor Inv#" }, { key: "total_value", label: "Value", num: true, money: true }]}
          rows={tab === "vendors" ? vendors : tab === "orders" ? orders : grns}
        />}
      />
      <div className="tabs">
        {[["vendors", "Vendors"], ["orders", "Purchase Orders"], ["grns", "Goods Receipts"]].map(([k, l]) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>

      {tab === "vendors" && (
        <Card title="Vendors" icon={<Truck size={16} />} actions={<div className="row"><button className="btn btn-ghost btn-sm" onClick={() => openModal("pay")}><IndianRupee size={15} /> Record Payment</button><button className="btn btn-primary btn-sm" onClick={() => openModal("vendor")}><Plus size={15} /> Add Vendor</button></div>}>
          <div className="row mb-16" style={{ position: "relative", maxWidth: 340 }}>
            <Search size={17} style={{ position: "absolute", left: 12, color: "#94a3b8" }} />
            <input placeholder="Search vendor, GSTIN or phone…" value={vendorQ} style={{ paddingLeft: 36 }}
              onChange={(e) => { setVendorQ(e.target.value); loadAll(e.target.value); }} />
          </div>
          <Table
            columns={[
              { key: "name", label: "Vendor" }, { key: "gstin", label: "GSTIN" }, { key: "phone", label: "Phone" },
              { key: "outstanding_balance", label: "Payable", num: true, render: (r) => <strong style={{ color: r.outstanding_balance > 0 ? "var(--danger)" : "inherit" }}>{inr(r.outstanding_balance)}</strong> },
              { key: "actions", label: "", render: (r) => (
                <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                  <button className="icon-btn" style={{ width: 30, height: 30 }} title="Payment ledger" onClick={() => openLedger(r)}><BookOpen size={14} /></button>
                  <button className="icon-btn" style={{ width: 30, height: 30 }} title="Edit" onClick={() => openEditVendor(r)}><Pencil size={14} /></button>
                  <button className="icon-btn" style={{ width: 30, height: 30 }} title="Delete" onClick={() => removeVendor(r)}><Trash2 size={14} /></button>
                </div>
              ) },
            ]}
            rows={vendors} empty="No vendors"
          />
        </Card>
      )}

      {tab === "orders" && (
        <Card title="Purchase Orders" icon={<FileText size={16} />} actions={<button className="btn btn-primary btn-sm" onClick={() => openModal("po")}><Plus size={15} /> New PO</button>}>
          <div className="row mb-16" style={{ position: "relative", maxWidth: 340 }}>
            <Search size={17} style={{ position: "absolute", left: 12, color: "#94a3b8" }} />
            <input placeholder="Search PO # or vendor…" value={orderQ} style={{ paddingLeft: 36 }}
              onChange={(e) => { setOrderQ(e.target.value); loadAll(undefined, e.target.value); }} />
          </div>
          <Table
            columns={[
              { key: "po_no", label: "PO #" }, { key: "vendor", label: "Vendor" }, { key: "order_date", label: "Date" },
              { key: "status", label: "Status", render: (r) => <Badge tone={r.status === "received" ? "success" : "info"}>{r.status.replace("_", " ")}</Badge> },
              { key: "expected_total", label: "Value", num: true, render: (r) => inr(r.expected_total) },
            ]}
            rows={orders} empty="No purchase orders"
          />
        </Card>
      )}

      {tab === "grns" && (
        <Card title="Goods Receipts" icon={<PackageCheck size={16} />} actions={<button className="btn btn-primary btn-sm" onClick={() => openModal("grn")}><Plus size={15} /> New GRN</button>}>
          <div className="row mb-16" style={{ position: "relative", maxWidth: 340 }}>
            <Search size={17} style={{ position: "absolute", left: 12, color: "#94a3b8" }} />
            <input placeholder="Search GRN #, vendor or invoice…" value={grnQ} style={{ paddingLeft: 36 }}
              onChange={(e) => { setGrnQ(e.target.value); loadAll(undefined, undefined, e.target.value); }} />
          </div>
          <Table
            columns={[
              { key: "grn_no", label: "GRN #" },
              { key: "vendor", label: "Vendor", render: (r) => r.vendor || "—" },
              { key: "received_date", label: "Date" },
              { key: "vendor_invoice_no", label: "Vendor Inv#" },
              { key: "total_value", label: "Value", num: true, render: (r) => inr(r.total_value) },
            ]}
            rows={grns} empty="No goods receipts"
          />
        </Card>
      )}

      {modal && (
        <Modal
          title={{ vendor: editId ? "Edit Vendor" : "Add Vendor", po: "New Purchase Order", grn: "Goods Receipt (GRN)", pay: "Record Vendor Payment" }[modal]!}
          onClose={() => setModal(null)}
          footer={<><button className="btn btn-ghost" onClick={() => setModal(null)}>Cancel</button><button className="btn btn-primary" onClick={save}>Save</button></>}
        >
          {err && <div className="error">{err}</div>}
          {modal === "vendor" && (
            <div className="grid grid-2">
              <Field label="Name" required><input value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
              <Field label="GSTIN"><input value={form.gstin || ""} onChange={(e) => setForm({ ...form, gstin: e.target.value })} /></Field>
              <Field label="Phone"><input value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></Field>
            </div>
          )}
          {(modal === "po" || modal === "grn" || modal === "pay") && (
            <div className="grid grid-2">
              <Field label="Branch"><select value={form.branch_id} onChange={(e) => setForm({ ...form, branch_id: e.target.value })}>{branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></Field>
              <Field label="Vendor">
                <SearchSelect
                  value={form.vendor_id}
                  options={pickerVendors}
                  placeholder="Type vendor name…"
                  onChange={(id) => setForm({ ...form, vendor_id: id })}
                  onQuery={searchVendors}
                  getLabel={(v) => `${v.name}${v.gstin ? ` · ${v.gstin}` : ""}`}
                />
              </Field>
            </div>
          )}
          {(modal === "po" || modal === "grn") && (
            <div className="grid grid-2">
              <Field label="Product">
                <SearchSelect
                  value={form.product_id}
                  options={pickerProducts}
                  placeholder="Type product name / SKU…"
                  onChange={(id) => setForm({ ...form, product_id: id })}
                  onQuery={searchProducts}
                  getLabel={(p) => `${p.name}${p.sku ? ` · ${p.sku}` : ""}`}
                />
              </Field>
              <Field label="Quantity"><input type="number" onChange={(e) => setForm({ ...form, quantity: e.target.value })} /></Field>
              <Field label="Unit price"><input type="number" onChange={(e) => setForm({ ...form, unit_price: e.target.value })} /></Field>
              {modal === "grn" && <>
                <Field label="Batch no"><input onChange={(e) => setForm({ ...form, batch_no: e.target.value })} /></Field>
                <Field label="Expiry date"><input type="date" onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} /></Field>
                <Field label="Vendor invoice #"><input onChange={(e) => setForm({ ...form, vendor_invoice_no: e.target.value })} /></Field>
              </>}
            </div>
          )}
          {modal === "pay" && (
            <div className="grid grid-2">
              <Field label="Amount"><input type="number" onChange={(e) => setForm({ ...form, amount: e.target.value })} /></Field>
              <Field label="Mode">
                <PaymentSelect value={form.mode || "cash"} onChange={(mode) => setForm({ ...form, mode })} use="purchase" bundle={bundle} />
              </Field>
            </div>
          )}
        </Modal>
      )}

      {ledger && (
        <Modal title={`Ledger — ${ledger.name}`} onClose={() => setLedger(null)} wide
          footer={<button className="btn btn-ghost" onClick={() => setLedger(null)}>Close</button>}>
          <p className="muted" style={{ marginTop: 0 }}>
            GSTIN {ledger.gstin || "—"} · Phone {ledger.phone || "—"} · Outstanding <strong style={{ color: ledger.outstanding_balance > 0 ? "var(--danger)" : "inherit" }}>{inr(ledger.outstanding_balance)}</strong>
          </p>
          <Table
            columns={[
              { key: "date", label: "Date" },
              { key: "kind", label: "Type", render: (r) => <Badge tone={r.kind === "payment" ? "success" : "info"}>{r.kind === "payment" ? "Payment" : "GRN"}</Badge> },
              { key: "ref", label: "Ref" },
              { key: "note", label: "Note", render: (r) => r.note || "—" },
              { key: "debit", label: "Purchase", num: true, render: (r) => r.debit ? inr(r.debit) : "—" },
              { key: "credit", label: "Paid", num: true, render: (r) => r.credit ? inr(r.credit) : "—" },
              { key: "balance", label: "Balance", num: true, render: (r) => inr(r.balance) },
            ]}
            rows={ledger.entries || []}
            empty="No purchases or payments yet"
          />
        </Modal>
      )}
    </div>
  );
}
