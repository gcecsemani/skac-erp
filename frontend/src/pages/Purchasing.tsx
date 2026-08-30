import { useEffect, useRef, useState } from "react";
import { Plus, Truck, FileText, PackageCheck, IndianRupee, Pencil, Trash2, Search, BookOpen, Undo2, Printer, Eye } from "lucide-react";
import { api } from "../api";
import { inr } from "../format";
import { printDebitNote } from "../print";
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
  const [returns, setReturns] = useState<any[]>([]);
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
  const [returnQ, setReturnQ] = useState("");
  const [ledger, setLedger] = useState<any | null>(null);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const [grnDetail, setGrnDetail] = useState<any | null>(null);
  const [returnQty, setReturnQty] = useState<Record<number, number>>({});
  const [pickerGrns, setPickerGrns] = useState<any[]>([]);
  const [viewReturn, setViewReturn] = useState<any | null>(null);

  const loadAll = async (vq?: string, oq?: string, gq?: string, rq?: string) => {
    const [v, o, g, r] = await Promise.all([
      api.vendors((vq !== undefined ? vq : vendorQ) || undefined),
      api.purchaseOrders((oq !== undefined ? oq : orderQ) || undefined),
      api.grns((gq !== undefined ? gq : grnQ) || undefined),
      api.purchaseReturns((rq !== undefined ? rq : returnQ) || undefined),
    ]);
    setVendors(v); setOrders(o); setGrns(g); setReturns(r);
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

  const searchGrns = (q: string) => {
    api.grns(q || undefined).then(setPickerGrns).catch(() => {});
  };

  const withBranchPrint = (doc: any) => {
    const b = branches.find((x) => x.id === doc.branch_id);
    if (!b) return doc;
    const parts = [b.address_line1, b.address_line2, b.city, b.district, b.state, b.pincode].filter(Boolean);
    return {
      ...doc,
      organization_name: "Sri Kumaran Agri Clinic",
      branch_name: b.name,
      branch_phone: b.phone,
      branch_gstin: b.gstin,
      branch_address: parts.join(", ") || undefined,
      printer_name: b.printer_name,
      printer_type: b.printer_type,
      thermal_paper_mm: b.thermal_paper_mm,
    };
  };

  const pickGrnForReturn = async (id: number | "") => {
    setErr("");
    setReturnQty({});
    if (!id) { setGrnDetail(null); setForm((f: any) => ({ ...f, grn_id: "" })); return; }
    try {
      const g = await api.grn(Number(id));
      setGrnDetail(g);
      setForm((f: any) => ({ ...f, grn_id: g.id }));
    } catch (e: any) {
      setErr(e.message); setGrnDetail(null);
    }
  };

  const openReturn = async (grn?: any) => {
    setEditId(null);
    setErr("");
    setReturnQty({});
    setGrnDetail(null);
    setForm({ reason: "", grn_id: grn?.id || "" });
    setModal("pret");
    searchGrns("");
    if (grn?.id) await pickGrnForReturn(grn.id);
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
      : modal === "pret" ? V.firstError(
          form.grn_id ? null : "Select a GRN.",
          V.minLen(form.reason, "Reason", 3),
          Object.values(returnQty).some((q) => Number(q) > 0) ? null : "Enter a return quantity for at least one item.",
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
      else if (modal === "pret") {
        const over = (grnDetail?.items || []).find((it: any) => (returnQty[it.id] || 0) > Number(it.returnable));
        if (over) {
          setErr(`Return qty cannot exceed returnable qty for ${over.product_name}.`);
          savingRef.current = false; setSaving(false); return;
        }
        await api.createPurchaseReturn({
          grn_id: Number(form.grn_id),
          reason: String(form.reason || "").trim(),
          items: Object.entries(returnQty).filter(([, q]) => Number(q) > 0).map(([id, q]) => ({
            grn_item_id: Number(id), quantity: Number(q),
          })),
        });
      }
      setModal(null); setGrnDetail(null); await loadAll();
    } catch (e: any) { setErr(e.message); }
    finally { savingRef.current = false; setSaving(false); }
  };

  if (!ready) return <Loading />;

  return (
    <div>
      <PageHeader title="Purchasing" subtitle="Vendors, purchase orders, goods receipt, purchase returns, payment ledger"
        actions={<ExportButtons
          title={tab === "vendors" ? "Vendors" : tab === "orders" ? "Purchase orders" : tab === "returns" ? "Purchase returns" : "Goods receipts"}
          columns={tab === "vendors"
            ? [{ key: "name", label: "Vendor" }, { key: "gstin", label: "GSTIN" }, { key: "phone", label: "Phone" }, { key: "outstanding_balance", label: "Payable", num: true, money: true }]
            : tab === "orders"
              ? [{ key: "po_no", label: "PO #" }, { key: "vendor", label: "Vendor" }, { key: "order_date", label: "Date" }, { key: "status", label: "Status" }, { key: "expected_total", label: "Value", num: true, money: true }]
              : tab === "returns"
                ? [{ key: "note_no", label: "Debit note #" }, { key: "note_date", label: "Date" }, { key: "vendor", label: "Vendor" }, { key: "grn_no", label: "GRN #" }, { key: "reason", label: "Reason" }, { key: "total", label: "Amount", num: true, money: true }]
              : [{ key: "grn_no", label: "GRN #" }, { key: "vendor", label: "Vendor" }, { key: "received_date", label: "Date" }, { key: "vendor_invoice_no", label: "Vendor Inv#" }, { key: "total_value", label: "Value", num: true, money: true }]}
          rows={tab === "vendors" ? vendors : tab === "orders" ? orders : tab === "returns" ? returns : grns}
        />}
      />
      <div className="tabs">
        {[["vendors", "Vendors"], ["orders", "Purchase Orders"], ["grns", "Goods Receipts"], ["returns", "Purchase Returns"]].map(([k, l]) => (
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
        <Card title="Goods Receipts" icon={<PackageCheck size={16} />} actions={<div className="row"><button className="btn btn-ghost btn-sm" onClick={() => openReturn()}><Undo2 size={15} /> Return to vendor</button><button className="btn btn-primary btn-sm" onClick={() => openModal("grn")}><Plus size={15} /> New GRN</button></div>}>
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
              { key: "actions", label: "", render: (r) => (
                <button className="btn btn-ghost btn-sm" title="Return to vendor" onClick={() => openReturn(r)}>
                  <Undo2 size={14} /> Return
                </button>
              ) },
            ]}
            rows={grns} empty="No goods receipts"
          />
        </Card>
      )}

      {tab === "returns" && (
        <Card title="Purchase Returns" icon={<Undo2 size={16} />} actions={<button className="btn btn-primary btn-sm" onClick={() => openReturn()}><Plus size={15} /> New debit note</button>}>
          <div className="row mb-16" style={{ position: "relative", maxWidth: 340 }}>
            <Search size={17} style={{ position: "absolute", left: 12, color: "#94a3b8" }} />
            <input placeholder="Search debit note, GRN or vendor…" value={returnQ} style={{ paddingLeft: 36 }}
              onChange={(e) => { setReturnQ(e.target.value); loadAll(undefined, undefined, undefined, e.target.value); }} />
          </div>
          <Table
            columns={[
              { key: "note_no", label: "Debit note #" },
              { key: "note_date", label: "Date" },
              { key: "vendor", label: "Vendor" },
              { key: "grn_no", label: "GRN #" },
              { key: "reason", label: "Reason" },
              { key: "total", label: "Amount", num: true, render: (r) => <strong>{inr(r.total)}</strong> },
              { key: "actions", label: "", render: (r) => (
                <div className="row" style={{ gap: 4, justifyContent: "flex-end" }}>
                  <button className="btn btn-ghost btn-sm" title="View" onClick={() => setViewReturn(r)}><Eye size={15} /></button>
                  <button className="btn btn-ghost btn-sm" title="Print" onClick={() => printDebitNote(withBranchPrint(r))}><Printer size={15} /></button>
                </div>
              ) },
            ]}
            rows={returns}
            empty="No purchase returns yet"
          />
        </Card>
      )}

      {modal && (
        <Modal
          title={{ vendor: editId ? "Edit Vendor" : "Add Vendor", po: "New Purchase Order", grn: "Goods Receipt (GRN)", pay: "Record Vendor Payment", pret: "Purchase Return (Debit Note)" }[modal]!}
          onClose={() => { setModal(null); setGrnDetail(null); }}
          wide={modal === "po" || modal === "grn" || modal === "pret"}
          footer={<><button type="button" className="btn btn-ghost" onClick={() => { setModal(null); setGrnDetail(null); }} disabled={saving}>Cancel</button><button type="button" className="btn btn-primary" onClick={save} disabled={saving}>{saving ? "Saving…" : modal === "pret" ? "Issue debit note" : "Save"}</button></>}
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
          {modal === "pret" && (
            <>
              <Field label="GRN #">
                <SearchSelect
                  value={form.grn_id}
                  options={pickerGrns}
                  placeholder="Type GRN # or vendor…"
                  onChange={pickGrnForReturn}
                  onQuery={searchGrns}
                  getLabel={(g) => `${g.grn_no} · ${g.vendor || "Vendor"} · ${inr(g.total_value)}`}
                />
              </Field>
              {grnDetail && (
                <p className="muted" style={{ marginTop: -8 }}>
                  {grnDetail.received_date} · {grnDetail.vendor}
                  {grnDetail.vendor_invoice_no ? ` · Inv ${grnDetail.vendor_invoice_no}` : ""}
                </p>
              )}
              <Field label="Reason" required>
                <input value={form.reason || ""} onChange={(e) => setForm({ ...form, reason: e.target.value })} placeholder="Not needed / damaged / wrong item / expired" />
              </Field>
              {grnDetail && (
                <Table
                  columns={[
                    { key: "product_name", label: "Product" },
                    { key: "batch_no", label: "Batch" },
                    { key: "quantity", label: "Received", num: true },
                    { key: "returned_quantity", label: "Already returned", num: true },
                    { key: "on_hand", label: "On hand", num: true },
                    { key: "ret", label: "Return qty", num: true, render: (r) => (
                      <input type="number" min={0} max={r.returnable} value={returnQty[r.id] ?? 0}
                        disabled={Number(r.returnable) <= 0}
                        onChange={(e) => setReturnQty((s) => ({ ...s, [r.id]: Number(e.target.value) }))}
                        style={{ width: 80, padding: 6, textAlign: "right" }} />
                    ) },
                  ]}
                  rows={grnDetail.items || []}
                  empty="No lines on this GRN"
                />
              )}
              {grnDetail && <p className="muted" style={{ margin: "8px 0 0" }}>Return qty cannot exceed remaining GRN qty or on-hand stock of that batch (already sold stock cannot be returned).</p>}
            </>
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
              { key: "kind", label: "Type", render: (r) => <Badge tone={r.kind === "payment" ? "success" : r.kind === "return" ? "warn" : "info"}>{r.kind === "payment" ? "Payment" : r.kind === "return" ? "Return" : "GRN"}</Badge> },
              { key: "ref", label: "Ref" },
              { key: "note", label: "Note", render: (r) => r.note || "—" },
              { key: "debit", label: "Purchase", num: true, render: (r) => r.debit ? inr(r.debit) : "—" },
              { key: "credit", label: "Paid / returned", num: true, render: (r) => r.credit ? inr(r.credit) : "—" },
              { key: "balance", label: "Balance", num: true, render: (r) => inr(r.balance) },
            ]}
            rows={ledger.entries || []}
            empty="No purchases or payments yet"
          />
        </Modal>
      )}

      {viewReturn && (
        <Modal title={`Debit note ${viewReturn.note_no}`} onClose={() => setViewReturn(null)} wide
          footer={<>
            <button className="btn btn-ghost" onClick={() => setViewReturn(null)}>Close</button>
            <button className="btn btn-primary" onClick={() => printDebitNote(withBranchPrint(viewReturn))}><Printer size={16} /> Print</button>
          </>}>
          <div className="row mb-16" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div><div className="muted">Date</div><strong>{viewReturn.note_date}</strong></div>
            <div><div className="muted">Vendor</div><strong>{viewReturn.vendor || "—"}</strong></div>
            <div><div className="muted">Against GRN</div><strong>{viewReturn.grn_no || "—"}</strong></div>
            <div><div className="muted">Amount</div><strong>{inr(viewReturn.total)}</strong></div>
          </div>
          {viewReturn.reason && <p className="muted" style={{ marginTop: 0 }}>Reason: {viewReturn.reason}</p>}
          <Table
            columns={[
              { key: "product_name", label: "Product" },
              { key: "batch_no", label: "Batch", render: (r) => r.batch_no || "—" },
              { key: "quantity", label: "Qty", num: true },
              { key: "unit_price", label: "Rate", num: true, render: (r) => inr(r.unit_price) },
              { key: "line_total", label: "Amount", num: true, render: (r) => inr(r.line_total) },
            ]}
            rows={viewReturn.items || []}
            empty="No lines"
          />
        </Modal>
      )}
    </div>
  );
}
