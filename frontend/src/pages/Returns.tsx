import { useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Plus, Undo2 } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { inr, matchesQuery, todayISO } from "../format";
import { BranchSelect, Card, ExportButtons, Field, Loading, Modal, PageHeader, SearchInput, SearchSelect, Table } from "../components/ui";
import { seesAllBranches } from "../roles";
import * as V from "../validate";

export default function Returns() {
  const { user } = useAuth();
  const allBranches = seesAllBranches(user);
  const [rows, setRows] = useState<any[] | null>(null);
  const [branches, setBranches] = useState<any[]>([]);
  const [branchId, setBranchId] = useState(0);
  const [day, setDay] = useState(todayISO());
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [invoiceId, setInvoiceId] = useState<number | "">("");
  const [invoiceHits, setInvoiceHits] = useState<any[]>([]);
  const [searchingInv, setSearchingInv] = useState(false);
  const [loadingInvoice, setLoadingInvoice] = useState(false);
  const [invoice, setInvoice] = useState<any>(null);
  const [qty, setQty] = useState<Record<number, number>>({});
  const [reason, setReason] = useState("");
  const [err, setErr] = useState("");
  const findAc = useRef<AbortController | null>(null);
  const findSeq = useRef(0);

  const load = () => api.creditNotes({
    branchId: branchId || undefined,
    on: day || undefined,
  }).then(setRows).catch(() => setRows([]));
  useEffect(() => {
    api.branches().then((b) => {
      setBranches(b);
      if (!allBranches && b[0]) setBranchId(b[0].id);
    }).catch(() => setBranches([]));
  }, []);
  useEffect(() => { load(); }, [branchId, day]);

  const filtered = useMemo(
    () => (rows || []).filter((r) => matchesQuery(q, r.note_no, r.date, r.invoice_id, r.invoice_no, r.reason, r.total, r.customer_name, r.customer_village, r.customer_phone)),
    [rows, q],
  );

  const searchInvoices = (needle: string) => {
    const seq = ++findSeq.current;
    findAc.current?.abort();
    const ac = new AbortController();
    findAc.current = ac;
    setSearchingInv(true);
    api.findInvoices(needle.trim(), ac.signal).then((hits) => {
      if (seq !== findSeq.current) return;
      setInvoiceHits(hits);
    }).catch((e: any) => {
      if (e?.name === "AbortError") return;
      if (seq !== findSeq.current) return;
      setInvoiceHits([]);
    }).finally(() => {
      if (seq !== findSeq.current) return;
      setSearchingInv(false);
    });
  };

  const pickInvoice = (id: number | "") => {
    setErr("");
    setInvoiceId(id);
    setQty({});
    if (!id) { setInvoice(null); setLoadingInvoice(false); return; }
    const hit = invoiceHits.find((inv) => inv.id === id);
    if (hit) setInvoice({ ...hit, items: hit.items || [] });
    setLoadingInvoice(true);
    api.invoice(Number(id)).then((inv) => {
      setInvoice(inv);
    }).catch((e: any) => {
      setErr(e.message); setInvoice(null);
    }).finally(() => setLoadingInvoice(false));
  };

  useEffect(() => {
    if (open) searchInvoices("");
    return () => findAc.current?.abort();
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
        subtitle="A sales return issues a credit note. The original invoice stays finalized and is not cancelled."
        actions={
          <div className="row">
            <ExportButtons title="Sales returns" columns={[
              { key: "note_no", label: "Credit Note #" }, { key: "date", label: "Date" },
              { key: "branch_name", label: "Branch" },
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
        <div className="row mb-16" style={{ flexWrap: "wrap", gap: 10, alignItems: "center" }}>
          <SearchInput value={q} onChange={setQ} placeholder="Search note #, invoice, farmer…" />
          <BranchSelect value={branchId} onChange={setBranchId} branches={branches} allowAll={allBranches} />
          <input type="date" value={day} onChange={(e) => setDay(e.target.value)} style={{ width: "auto" }} title="Return date" />
          {day !== todayISO() && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDay(todayISO())}>Today</button>
          )}
          {day && (
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDay("")}>All dates</button>
          )}
        </div>
        <Table
          columns={[
            { key: "note_no", label: "Credit Note #" },
            { key: "date", label: "Date" },
            { key: "branch_name", label: "Branch", render: (r: any) => r.branch_name || "—" },
            { key: "invoice_no", label: "Invoice #", render: (r: any) => r.invoice_no || `#${r.invoice_id}` },
            { key: "customer_name", label: "Farmer", render: (r: any) => r.customer_name || "—" },
            { key: "customer_village", label: "Village", render: (r: any) => r.customer_village || "—" },
            { key: "customer_phone", label: "Phone", render: (r: any) => r.customer_phone || "—" },
            { key: "reason", label: "Reason" },
            { key: "total", label: "Amount", num: true, render: (r) => <strong>{inr(r.total)}</strong> },
          ]}
          rows={filtered}
          empty={rows.length ? "No credit notes match the search" : day ? "No sales returns on this date" : "No credit notes yet"}
          pageSize={50}
        />
      </Card>

      {open && (
        <Modal
          title="New Credit Note"
          onClose={() => setOpen(false)}
          footer={<>
            <button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={submit} disabled={!invoice || loadingInvoice}><Undo2 size={16} /> Issue Credit Note</button>
          </>}
        >
          <Field label="Invoice">
            <SearchSelect
              value={invoiceId}
              options={invoiceHits}
              loading={searchingInv}
              placeholder="Invoice #, farmer name, or phone"
              onChange={pickInvoice}
              onQuery={searchInvoices}
              getLabel={(inv) =>
                `${inv.invoice_no} · ${inv.customer_name || "Walk-in"}${inv.customer_phone ? ` · ${inv.customer_phone}` : ""} · ${inr(inv.grand_total)}`
              }
            />
          </Field>
          {err && <div className="error">{err}</div>}
          {loadingInvoice && (
            <p className="muted" style={{ display: "flex", alignItems: "center", gap: 8, marginTop: -8 }}>
              <Loader2 size={14} className="spin" /> Loading invoice…
            </p>
          )}
          {invoice && (
            <p className="muted" style={{ marginTop: -8 }}>
              {invoice.invoice_date} · {invoice.customer_name || "Walk-in"}
              {invoice.customer_village ? ` · ${invoice.customer_village}` : ""}
              {invoice.customer_phone ? ` · ${invoice.customer_phone}` : ""}
              {" · "}{invoice.payment_mode} · {inr(invoice.grand_total)}
              {" · Invoice stays "}{invoice.status || "finalized"}
              {". The credit note reduces this farmer's khata and shows on their ledger."}
            </p>
          )}
          {invoice && !loadingInvoice && (
            <>
              <Field label="Reason" required><input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Damaged / expired / wrong item" /></Field>
              <Table
                columns={[
                  { key: "product_name", label: "Product" },
                  { key: "quantity", label: "Sold", num: true, render: (r: any) => `${r.quantity}${r.unit ? ` ${r.unit}` : ""}` },
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
