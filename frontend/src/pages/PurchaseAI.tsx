import { useEffect, useMemo, useState } from "react";
import { Brain, ShoppingCart, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { api } from "../api";
import { inr, num } from "../format";
import { Badge, BranchSelect, Card, Field, Loading, Modal, PageHeader, Table } from "../components/ui";

export default function PurchaseAI() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [sel, setSel] = useState<Record<number, boolean>>({});
  const [qty, setQty] = useState<Record<number, number>>({});
  const [branches, setBranches] = useState<any[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  const [draft, setDraft] = useState<{ branchId: number; vendorId: number; notes: string } | null>(null);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState("");

  const load = () => api.forecast(true).then(setRows).catch(() => setRows([]));
  useEffect(() => {
    load();
    api.branches().then(setBranches).catch(() => setBranches([]));
    api.vendors().then(setVendors).catch(() => setVendors([]));
  }, []);

  const selected = useMemo(
    () => (rows || []).filter((r) => sel[r.product_id]),
    [rows, sel],
  );
  const qtyFor = (r: any) => qty[r.product_id] ?? r.recommended_purchase_qty;
  const draftTotal = selected.reduce(
    (s, r) => s + qtyFor(r) * Number(r.purchase_price || 0), 0,
  );

  if (!rows) return <Loading />;

  const trendBadge = (t: string) =>
    t === "rising" ? <Badge tone="success"><TrendingUp size={12} /> rising</Badge>
    : t === "falling" ? <Badge tone="danger"><TrendingDown size={12} /> falling</Badge>
    : <Badge tone="neutral"><Minus size={12} /> stable</Badge>;

  const openDraft = () => {
    setErr(""); setDone("");
    setDraft({ branchId: branches[0]?.id || 0, vendorId: vendors[0]?.id || 0, notes: "Raised from AI purchase recommendations" });
  };

  const createPO = async () => {
    if (!draft) return;
    if (!draft.branchId) { setErr("Select a branch."); return; }
    if (!draft.vendorId) { setErr("Select a supplier."); return; }
    const items = selected
      .map((r) => ({ product_id: r.product_id, quantity: qtyFor(r), unit_price: Number(r.purchase_price || 0) }))
      .filter((i) => i.quantity > 0);
    if (!items.length) { setErr("Set a quantity above zero on at least one item."); return; }

    setErr(""); setSaving(true);
    try {
      const po: any = await api.createPO({
        branch_id: draft.branchId,
        vendor_id: draft.vendorId,
        notes: draft.notes || undefined,
        items,
      });
      setDraft(null);
      setSel({});
      setQty({});
      setDone(`Purchase order ${po?.po_no || ""} created. Track it under Purchasing → Orders.`);
      load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="AI Purchase Recommendations"
        subtitle="Demand-forecasted restock suggestions per product"
        actions={
          <button className="btn btn-primary" disabled={selected.length === 0} onClick={openDraft}>
            <ShoppingCart size={16} /> Convert {selected.length} to PO
          </button>
        }
      />
      {done && <div className="card" style={{ padding: 12, marginBottom: 12, color: "var(--brand-600)", fontWeight: 600 }}>{done}</div>}
      <Card title="Recommended Purchases" icon={<Brain size={16} color="#7c3aed" />}>
        <Table
          columns={[
            {
              key: "sel",
              label: "",
              render: (r) => (
                <input
                  type="checkbox"
                  style={{ width: "auto" }}
                  checked={!!sel[r.product_id]}
                  onChange={(e) => setSel((s) => ({ ...s, [r.product_id]: e.target.checked }))}
                />
              ),
            },
            { key: "product_name", label: "Product" },
            { key: "current_stock", label: "Stock", num: true, render: (r) => num(r.current_stock) },
            { key: "weekly_sales", label: "Avg / week", num: true, render: (r) => num(r.weekly_sales) },
            { key: "trend", label: "Trend", render: (r) => trendBadge(r.trend) },
            { key: "estimated_stockout_date", label: "Stock-out", render: (r) => r.estimated_stockout_date || "—" },
            {
              key: "recommended_purchase_qty",
              label: "Recommend Buy",
              num: true,
              render: (r) => <strong style={{ color: "var(--brand-600)" }}>{num(r.recommended_purchase_qty)}</strong>,
            },
          ]}
          rows={rows}
          empty="No restocking needed right now"
        />
      </Card>

      {draft && (
        <Modal
          wide
          title={`New purchase order — ${selected.length} item${selected.length === 1 ? "" : "s"}`}
          onClose={() => setDraft(null)}
          footer={
            <>
              <button className="btn" onClick={() => setDraft(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={createPO} disabled={saving}>
                {saving ? "Creating…" : "Create purchase order"}
              </button>
            </>
          }
        >
          <div className="row" style={{ gap: 12, flexWrap: "wrap" }}>
            <Field label="Branch" required>
              <BranchSelect
                value={draft.branchId}
                branches={branches}
                allowAll={false}
                onChange={(id) => setDraft({ ...draft, branchId: id })}
              />
            </Field>
            <Field label="Supplier" required>
              <select
                value={draft.vendorId}
                onChange={(e) => setDraft({ ...draft, vendorId: Number(e.target.value) })}
              >
                <option value={0}>Select supplier…</option>
                {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Notes">
            <input value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} />
          </Field>

          <Table
            columns={[
              { key: "product_name", label: "Product" },
              {
                key: "quantity",
                label: "Order qty",
                num: true,
                render: (r) => (
                  <input
                    type="number"
                    min={0}
                    step="0.001"
                    value={qtyFor(r)}
                    onChange={(e) => setQty((q) => ({ ...q, [r.product_id]: Number(e.target.value) }))}
                    style={{ width: 90, padding: 6, textAlign: "right" }}
                  />
                ),
              },
              { key: "purchase_price", label: "Rate", num: true, render: (r) => inr(r.purchase_price) },
              { key: "line", label: "Amount", num: true, render: (r) => inr(qtyFor(r) * Number(r.purchase_price || 0)) },
            ]}
            rows={selected}
            empty="Nothing selected"
          />
          <div className="row" style={{ justifyContent: "flex-end", paddingTop: 12, borderTop: "1px solid var(--border)" }}>
            Expected total:&nbsp;<strong>{inr(draftTotal)}</strong>
          </div>
          <p className="muted" style={{ fontSize: 13, marginTop: 8 }}>
            Rates default to each product's last purchase price. The order is placed, not received —
            stock only moves when you record the GRN against it.
          </p>
          {err && <div className="error" style={{ marginTop: 8 }}>{err}</div>}
        </Modal>
      )}
    </div>
  );
}
