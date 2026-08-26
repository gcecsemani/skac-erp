import { useEffect, useState } from "react";
import { Brain, ShoppingCart, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { api } from "../api";
import { num } from "../format";
import { Badge, Card, Loading, PageHeader, Table } from "../components/ui";

export default function PurchaseAI() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [sel, setSel] = useState<Record<number, boolean>>({});

  useEffect(() => { api.forecast(true).then(setRows).catch(() => setRows([])); }, []);
  if (!rows) return <Loading />;

  const trendBadge = (t: string) =>
    t === "rising" ? <Badge tone="success"><TrendingUp size={12} /> rising</Badge>
    : t === "falling" ? <Badge tone="danger"><TrendingDown size={12} /> falling</Badge>
    : <Badge tone="neutral"><Minus size={12} /> stable</Badge>;

  const selectedCount = Object.values(sel).filter(Boolean).length;

  return (
    <div>
      <PageHeader
        title="AI Purchase Recommendations"
        subtitle="Demand-forecasted restock suggestions per product"
        actions={<button className="btn btn-primary" disabled={selectedCount === 0}><ShoppingCart size={16} /> Convert {selectedCount} to PO</button>}
      />
      <Card title="Recommended Purchases" icon={<Brain size={16} color="#7c3aed" />}>
        <Table
          columns={[
            { key: "sel", label: "", render: (r) => <input type="checkbox" style={{ width: "auto" }} checked={!!sel[r.product_id]} onChange={(e) => setSel((s) => ({ ...s, [r.product_id]: e.target.checked }))} /> },
            { key: "product_name", label: "Product" },
            { key: "current_stock", label: "Stock", num: true, render: (r) => num(r.current_stock) },
            { key: "weekly_sales", label: "Avg / week", num: true, render: (r) => num(r.weekly_sales) },
            { key: "trend", label: "Trend", render: (r) => trendBadge(r.trend) },
            { key: "estimated_stockout_date", label: "Stock-out", render: (r) => r.estimated_stockout_date || "—" },
            { key: "recommended_purchase_qty", label: "Recommend Buy", num: true, render: (r) => <strong style={{ color: "var(--brand-600)" }}>{num(r.recommended_purchase_qty)}</strong> },
          ]}
          rows={rows}
          empty="No restocking needed right now"
        />
      </Card>
    </div>
  );
}
