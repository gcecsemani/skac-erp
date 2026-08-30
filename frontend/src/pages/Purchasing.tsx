import { useEffect, useRef, useState } from "react";
import { Plus, Truck, FileText, PackageCheck, IndianRupee, Pencil, Trash2, Search, BookOpen } from "lucide-react";
import { api } from "../api";
import { inr } from "../format";
import { Badge, Card, ExportButtons, Field, Loading, Modal, PageHeader, SearchSelect, Table } from "../components/ui";
import { PaymentSelect } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
import * as V from "../validate";

function newLine(kind: "po" | "grn") {
  const line: any = { key: `${Date.now()}-${Math.random()}`, product_id: "", quantity: "", unit_price: "" };
  if (kind === "grn") { line.batch_no = ""; line.expiry_date = ""; }
  return line;
}

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
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);

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
    const kind = m === "grn" ? "grn" : "po";
    setForm({
      branch_id: branches[0]?.id,
      vendor_id: vendors[0]?.id,
      vendor_invoice_no: "",
      lines: m === "po" || m === "grn" ? [newLine(kind)] : undefined,
    });
    setErr("");
    setModal(m);
    setPickerVendors(vendors);
    api.products(undefined, undefined, 80).then(setPickerProducts).catch(() => setPickerProducts([]));
  };

  const setLine = (index: number, patch: any) => {
    setForm((f: any) => ({
      ...f,
      lines: (f.lines || []).map((ln: any, i: number) => (i === index ? { ...ln, ...patch } : ln)),
    }));
  };
  const addLine = () => {
    const kind = modal === "grn" ? "grn" : "po";
    setForm((f: any) => ({ ...f, lines: [...(f.lines || []), newLine(kind)] }));
  };
  const removeLine = (index: number) => {
    setForm((f: any) => ({ ...f, lines: (f.lines || []).filter((_: any, i: number) => i !== index) }));
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
    if (savingRef.current) return;
    savingRef.current = true;
    setErr("");
    const msg =
      modal === "vendor" ? V.firstError(
          V.businessName(form.name, "Vendor name"),
          V.gstin(form.gstin),
          V.phone(form.phone, { allowLandline: true }),
        )
      : modal === "po" || modal === "grn" ? V.firstError(
          form.branch_id ? null : "Select a branch.",
          form.vendor_id ? null : "Select a vendor.",
          (form.lines || []).length ? null : "Add at least one product.",
          ...(form.lines || []).flatMap((ln: any, i: number) => {
            const n = i + 1;
            return [
              ln.product_id ? null : `Line ${n}: select a product.`,
              V.positive(ln.quantity, `Line ${n} quantity`),
              V.nonNegative(ln.unit_price || 0, `Line ${n} unit price`),
              modal === "grn" ? V.required(ln.batch_no, `Line ${n} batch number`) : null,
            ];
          }),
        )
      : modal === "pay" ? V.firstError(
          form.vendor_id ? null : "Select a vendor.",
          V.positive(form.amount, "Amount"),
        )
      : null;
    if (msg) { savingRef.current = false; setErr(msg); return; }
    setSaving(true);
    try {
      if (modal === "vendor" && editId) await api.updateVendor(editId, { name: form.name.trim(), gstin: form.gstin, phone: form.phone });
      else if (modal === "vendor") await api.createVendor({ name: form.name.trim(), gstin: form.gstin, phone: form.phone });
      else if (modal === "po") {
        await api.createPO({
          branch_id: Number(form.branch_id), vendor_id: Number(form.vendor_id),
          items: form.lines.map((ln: any) => ({
            product_id: Number(ln.product_id), quantity: Number(ln.quantity), unit_price: Number(ln.unit_price || 0),
          })),
        });
      } else if (modal === "grn") {
        await api.createGRN({
          branch_id: Number(form.branch_id), vendor_id: Number(form.vendor_id),
          vendor_invoice_no: form.vendor_invoice_no,
          items: form.lines.map((ln: any) => ({
            product_id: Number(ln.product_id), batch_no: ln.batch_no, quantity: Number(ln.quantity),
            unit_price: Number(ln.unit_price || 0), expiry_date: ln.expiry_date || null,
          })),
        });
      } else if (modal === "pay") await api.vendorPayment({ vendor_id: Number(form.vendor_id), branch_id: Number(form.branch_id), amount: Number(form.amount), mode: form.mode || "cash" });
      setModal(null); await loadAll();
    } catch (e: any) { setErr(e.message); }
    finally { savingRef.current = false; setSaving(false); }
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
              { key: "items", label: "Items", render: (r) => r.items?.length || 0 },
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
              { key: "item_count", label: "Items" },
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
          wide={modal === "po" || modal === "grn"}
          footer={<><button type="button" className="btn btn-ghost" onClick={() => setModal(null)} disabled={saving}>Cancel</button><button type="button" className="btn btn-primary" onClick={save} disabled={saving}>{saving ? "Saving…" : "Save"}</button></>}
        >
          {err && <div className="error">{err}</div>}
          {modal === "vendor" && (
            <div className="grid grid-2">
              <Field label="Name" required><input value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. Ram & Co" /></Field>
              <Field label="GSTIN"><input value={form.gstin || ""} onChange={(e) => setForm({ ...form, gstin: e.target.value })} /></Field>
              <Field label="Phone"><input value={form.phone || ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="Mobile or landline" inputMode="tel" /></Field>
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
            <div>
              {modal === "grn" && (
                <div className="grid grid-2" style={{ marginBottom: 12 }}>
                  <Field label="Vendor invoice #"><input value={form.vendor_invoice_no || ""} onChange={(e) => setForm({ ...form, vendor_invoice_no: e.target.value })} /></Field>
                </div>
              )}
              <div className="row" style={{ justifyContent: "space-between", margin: "4px 0 8px" }}>
                <strong style={{ fontSize: 13 }}>Products</strong>
                <button type="button" className="btn btn-ghost btn-sm" onClick={addLine}><Plus size={14} /> Add product</button>
              </div>
              {(form.lines || []).map((ln: any, i: number) => (
                <div key={ln.key} style={{ border: "1px solid var(--border)", borderRadius: 10, padding: 12, marginBottom: 10 }}>
                  <div className="row" style={{ justifyContent: "space-between", marginBottom: 8 }}>
                    <span className="muted">Line {i + 1}</span>
                    {(form.lines || []).length > 1 && (
                      <button type="button" className="icon-btn" style={{ width: 30, height: 30 }} title="Remove line" onClick={() => removeLine(i)}>
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
                    <Field label="Quantity" required><input type="number" value={ln.quantity} onChange={(e) => setLine(i, { quantity: e.target.value })} /></Field>
                    <Field label="Unit price"><input type="number" value={ln.unit_price} onChange={(e) => setLine(i, { unit_price: e.target.value })} /></Field>
                    {modal === "grn" && <>
                      <Field label="Batch no" required><input value={ln.batch_no} onChange={(e) => setLine(i, { batch_no: e.target.value })} /></Field>
                      <Field label="Expiry date"><input type="date" value={ln.expiry_date} onChange={(e) => setLine(i, { expiry_date: e.target.value })} /></Field>
                    </>}
                  </div>
                </div>
              ))}
              <p className="muted" style={{ margin: "4px 0 0", textAlign: "right" }}>
                Total {inr((form.lines || []).reduce((s: number, ln: any) => s + Number(ln.quantity || 0) * Number(ln.unit_price || 0), 0))}
              </p>
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
