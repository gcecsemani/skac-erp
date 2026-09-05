import { useEffect, useMemo, useState } from "react";
import { Plus, Undo2 } from "lucide-react";
import { api } from "../api";
import { inr, matchesQuery } from "../format";
import { Card, ExportButtons, Field, Loading, Modal, PageHeader, SearchInput, SearchSelect, Table } from "../components/ui";
import * as V from "../validate";

export default function Returns() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [invoiceId, setInvoiceId] = useState<number | "">("");
  const [invoiceHits, setInvoiceHits] = useState<any[]>([]);
  const [invoice, setInvoice] = useState<any>(null);
  const [qty, setQty] = useState<Record<number, number>>({});
  const [reason, setReason] = useState("");
  const [err, setErr] = useState("");

  const load = () => api.creditNotes().then(setRows).catch(() => setRows([]));
  useEffect(() => { load(); }, []);

  const filtered = useMemo(
    () => (rows || []).filter((r) => matchesQuery(q, r.note_no, r.date, r.invoice_id, r.invoice_no, r.reason, r.total, r.customer_name, r.customer_village, r.customer_phone)),
    [rows, q],
  );

  const searchInvoices = (needle: string) => {
    const q = needle.trim();
    if (q.length === 1) return;
    api.findInvoices(q).then(setInvoiceHits).catch(() => setInvoiceHits([]));
  };

  const pickInvoice = (id: number | "") => {
    setErr("");
    setInvoiceId(id);
    setQty({});
    if (!id) { setInvoice(null); return; }
    const hit = invoiceHits.find((inv) => inv.id === id);
    if (hit) { setInvoice(hit); return; }
    api.invoice(Number(id)).then((inv) => setInvoice(inv)).catch((e: any) => {
      setErr(e.message); setInvoice(null);
    });
  };

  useEffect(() => {
    if (open) searchInvoices("");
  }, [open]);

  const submit = async () => {
    setErr("");
    if (!invoice?.id) { setErr("Select an invoice."); return; }
    const items = Object.entries(qty).filter(([, qv]) => qv > 0).map(([pid, qv]) => ({ product_id: Number(pid), quantity: qv }));
    if (items.length === 0) { setErr("Select at least one item to return."); return; }
    const over = (invoice?.items || []).find((it: any) => (qty[it.product_id] || 0) > Number(it.quantity));
    if (over) { setErr(`Return qty cannot exceed sold qty for ${over.product_name}.`); return; }
    const msg = V.minLen(reason, "Reason", 3);
    if (msg) { setErr(msg); return; }
    try {
      await api.createCreditNote({ invoice_id: invoice.id, reason, items });
      setOpen(false); setInvoice(null); setQty({}); setInvoiceId(""); setReason(""); setInvoiceHits([]); load();
    } catch (e: any) { setErr(e.message); }
  };

  if (!rows) return <Loading />;

  return (
    <div>
      <PageHeader
        title="Sales Returns"
        subtitle="Corrections are issued as immutable credit notes — invoices are never edited"
        actions={
          <div className="row">
            <ExportButtons title="Sales returns" columns={[
              { key: "note_no", label: "Credit Note #" }, { key: "date", label: "Date" },
              { key: "invoice_no", label: "Invoice #" }, { key: "customer_name", label: "Farmer" },
              { key: "customer_village", label: "Village" }, { key: "customer_phone", label: "Phone" },
              { key: "reason", label: "Reason" },
              { key: "total", label: "Amount", num: true, money: true },
            ]} rows={filtered} />
            <button className="btn btn-primary" onClick={() => { setOpen(true); setErr(""); setInvoice(null); setInvoiceId(""); setQty({}); setReason(""); }}><Plus size={16} /> New Credit Note</button>
          </div>
        }
      />
      <Card>
        <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10 }}>
          <SearchInput value={q} onChange={setQ} placeholder="Search note #, invoice, reason…" />
        </div>
        <Table
          columns={[
            { key: "note_no", label: "Credit Note #" },
            { key: "date", label: "Date" },
            { key: "invoice_no", label: "Invoice #", render: (r: any) => r.invoice_no || `#${r.invoice_id}` },
            { key: "customer_name", label: "Farmer", render: (r: any) => r.customer_name || "—" },
            { key: "customer_village", label: "Village", render: (r: any) => r.customer_village || "—" },
            { key: "customer_phone", label: "Phone", render: (r: any) => r.customer_phone || "—" },
            { key: "reason", label: "Reason" },
            { key: "total", label: "Amount", num: true, render: (r) => <strong>{inr(r.total)}</strong> },
          ]}
          rows={filtered}
          empty={rows.length ? "No credit notes match the search" : "No credit notes yet"}
          pageSize={50}
        />
      </Card>

      {open && (
        <Modal
          title="New Credit Note"
          onClose={() => setOpen(false)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={submit} disabled={!invoice}><Undo2 size={16} /> Issue Credit Note</button>
          </>}
        >
          <Field label="Invoice #">
            <SearchSelect
              value={invoiceId}
              options={invoiceHits}
              placeholder="Type AVL/2026-27/00003 or farmer name"
              onChange={pickInvoice}
              onQuery={searchInvoices}
              getLabel={(inv) => `${inv.invoice_no} · ${inv.customer_name || "Walk-in"} · ${inr(inv.grand_total)}`}
            />
          </Field>
          {err && <div className="error">{err}</div>}
          {invoice && (
            <p className="muted" style={{ marginTop: -8 }}>
              {invoice.invoice_date} · {invoice.customer_name || "Walk-in"}
              {invoice.customer_village ? ` · ${invoice.customer_village}` : ""}
              {invoice.customer_phone ? ` · ${invoice.customer_phone}` : ""}
              {" · "}{invoice.payment_mode} · {inr(invoice.grand_total)}
              {invoice.payment_mode !== "cash" ? " · Credit bill — return posts a credit note against this invoice" : ""}
            </p>
          )}
          {invoice && (
            <>
              <Field label="Reason" required><input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Damaged / expired / wrong item" /></Field>
              <Table
                columns={[
                  { key: "product_name", label: "Product" },
                  { key: "quantity", label: "Sold", num: true },
                  { key: "ret", label: "Return qty", num: true, render: (r) => (
                    <input type="number" min={0} max={r.quantity} value={qty[r.product_id] ?? 0}
                      onChange={(e) => setQty((s) => ({ ...s, [r.product_id]: Number(e.target.value) }))}
                      style={{ width: 80, padding: 6, textAlign: "right" }} />
                  ) },
                ]}
                rows={invoice.items || []}
              />
            </>
          )}
        </Modal>
      )}
    </div>
  );
}
