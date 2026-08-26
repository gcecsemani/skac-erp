import { useEffect, useMemo, useState } from "react";
import { Plus, Undo2 } from "lucide-react";
import { api } from "../api";
import { inr, matchesQuery } from "../format";
import { Card, ExportButtons, Field, Loading, Modal, PageHeader, SearchInput, Table } from "../components/ui";
import * as V from "../validate";

export default function Returns() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [invoiceId, setInvoiceId] = useState("");
  const [invoice, setInvoice] = useState<any>(null);
  const [qty, setQty] = useState<Record<number, number>>({});
  const [reason, setReason] = useState("");
  const [err, setErr] = useState("");

  const load = () => api.creditNotes().then(setRows).catch(() => setRows([]));
  useEffect(() => { load(); }, []);

  const filtered = useMemo(
    () => (rows || []).filter((r) => matchesQuery(q, r.note_no, r.date, r.invoice_id, r.reason, r.total)),
    [rows, q],
  );

  const fetchInvoice = async () => {
    setErr(""); setInvoice(null);
    if (!invoiceId || Number(invoiceId) <= 0) { setErr("Enter a valid invoice ID."); return; }
    try { setInvoice(await api.invoice(Number(invoiceId))); } catch (e: any) { setErr(e.message); }
  };

  const submit = async () => {
    setErr("");
    const items = Object.entries(qty).filter(([, qv]) => qv > 0).map(([pid, qv]) => ({ product_id: Number(pid), quantity: qv }));
    if (items.length === 0) { setErr("Select at least one item to return."); return; }
    const over = (invoice?.items || []).find((it: any) => (qty[it.product_id] || 0) > Number(it.quantity));
    if (over) { setErr(`Return qty cannot exceed sold qty for ${over.product_name}.`); return; }
    const msg = V.minLen(reason, "Reason", 3);
    if (msg) { setErr(msg); return; }
    try {
      await api.createCreditNote({ invoice_id: Number(invoiceId), reason, items });
      setOpen(false); setInvoice(null); setQty({}); setInvoiceId(""); setReason(""); load();
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
              { key: "invoice_id", label: "Invoice ID" }, { key: "reason", label: "Reason" },
              { key: "total", label: "Amount", num: true, money: true },
            ]} rows={filtered} />
            <button className="btn btn-primary" onClick={() => setOpen(true)}><Plus size={16} /> New Credit Note</button>
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
            { key: "invoice_id", label: "Invoice ID" },
            { key: "reason", label: "Reason" },
            { key: "total", label: "Amount", num: true, render: (r) => <strong>{inr(r.total)}</strong> },
          ]}
          rows={filtered}
          empty={rows.length ? "No credit notes match the search" : "No credit notes yet"}
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
          <div className="row" style={{ alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}><Field label="Invoice ID"><input value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} placeholder="e.g. 1" /></Field></div>
            <button className="btn btn-ghost" style={{ marginBottom: 14 }} onClick={fetchInvoice}>Load</button>
          </div>
          {err && <div className="error">{err}</div>}
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
