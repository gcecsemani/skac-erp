import { useEffect, useMemo, useState } from "react";
import { Plus, Pencil, Trash2, Search, Star } from "lucide-react";
import { api } from "../api";
import { CATEGORY_COLORS, inr, parseWeight } from "../format";
import { Badge, Card, ExportButtons, Field, Loading, Modal, PageHeader, Table } from "../components/ui";
import { ConfigOptions, GstSelect } from "../components/configFields";
import { useConfigBundle } from "../configBundle";
import { getCachedProducts, matchProduct, refreshProducts, removeCached, upsertCached } from "../offline";
import * as V from "../validate";

const empty = {
  sku: "", name: "", category: "fertilizer", hsn_code: "", base_unit: "bag",
  gst_rate: "5", mrp: "", purchase_price: "", sale_price: "", reorder_level: "",
  npk_n: "", npk_p: "", npk_k: "", toxicity_class: "", germination_pct: "", seed_lot: "",
  sell_loose: true, pack_size: "",
};

export default function Products() {
  const { bundle } = useConfigBundle();
  const [rows, setRows] = useState<any[] | null>(null);
  const [cat, setCat] = useState("");
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<any>(empty);
  const [err, setErr] = useState("");

  useEffect(() => {
    getCachedProducts().then((cached) => { if (cached.length) setRows(cached); }).catch(() => {});
    refreshProducts().then(setRows).catch(() => setRows((cur) => cur || []));
  }, []);

  const filtered = useMemo(
    () => (rows || []).filter((r) => matchProduct(r, q, cat || undefined))
      .sort((a, b) => Number(!!b.is_favorite) - Number(!!a.is_favorite) || String(a.name).localeCompare(String(b.name))),
    [rows, q, cat],
  );

  const toggleFav = async (r: any) => {
    const next = !r.is_favorite;
    const updated = { ...r, is_favorite: next };
    setRows((cur) => (cur || []).map((x) => x.id === r.id ? updated : x));
    upsertCached("products", updated);
    try { await api.setFavorite(r.id, next); } catch {
      setRows((cur) => (cur || []).map((x) => x.id === r.id ? r : x));
      upsertCached("products", r);
    }
  };

  const openCreate = () => { setEditId(null); setForm(empty); setErr(""); setOpen(true); };
  const openEdit = (r: any) => {
    setEditId(r.id); setErr("");
    setForm({
      ...empty,
      ...Object.fromEntries(Object.keys(empty).map((k) => [k, r[k] ?? ""])),
      sell_loose: !!r.allows_loose,
      pack_size: r.pack_size > 1 ? String(r.pack_size) : "",
    });
    setOpen(true);
  };
  const remove = async (r: any) => {
    if (!confirm(`Delete product "${r.name}"?`)) return;
    try {
      await api.deleteProduct(r.id);
      removeCached("products", r.id);
      setRows((cur) => (cur || []).filter((x) => x.id !== r.id));
    } catch (e: any) { alert(e.message); }
  };

  const submit = async () => {
    setErr("");
    const msg = V.firstError(
      V.required(form.sku, "SKU"),
      V.minLen(form.name, "Name", 2),
      V.required(form.base_unit, "Base unit"),
      V.gstRate(form.gst_rate),
      V.nonNegative(form.sale_price || 0, "Sale price"),
      V.nonNegative(form.purchase_price || 0, "Purchase price"),
      V.nonNegative(form.mrp || 0, "MRP"),
      form.sell_loose && !(Number(form.pack_size) > 1) && !parseWeight(form.name)
        ? "Enter bag size in kg (50, 45, 25, …) or put it in the name, e.g. UREA - 45KGS."
        : null,
    );
    if (msg) { setErr(msg); return; }
    const numify = (v: any) => (v === "" || v == null ? null : Number(v));
    const payload: any = {
      sku: form.sku, name: form.name, category: form.category, hsn_code: form.hsn_code || null,
      base_unit: form.base_unit, gst_rate: numify(form.gst_rate) ?? 0, mrp: numify(form.mrp) ?? 0,
      purchase_price: numify(form.purchase_price) ?? 0, sale_price: numify(form.sale_price) ?? 0,
      reorder_level: numify(form.reorder_level) ?? 0,
      npk_n: numify(form.npk_n), npk_p: numify(form.npk_p), npk_k: numify(form.npk_k),
      toxicity_class: form.toxicity_class || null, germination_pct: numify(form.germination_pct),
      seed_lot: form.seed_lot || null,
      sell_loose: form.sell_loose !== "" && form.sell_loose != null ? !!form.sell_loose : undefined,
      pack_size: Number(form.pack_size) > 1 ? Number(form.pack_size) : (parseWeight(form.name)?.[0] || undefined),
    };
    try {
      const saved = editId ? await api.updateProduct(editId, payload) : await api.createProduct(payload);
      upsertCached("products", saved);
      setRows((cur) => {
        const list = cur || [];
        return editId ? list.map((x) => x.id === saved.id ? { ...x, ...saved } : x) : [saved, ...list.filter((x) => x.id !== saved.id)];
      });
      setOpen(false); setForm(empty); setEditId(null);
    } catch (e: any) { setErr(e.message); }
  };

  if (!rows) return <Loading />;

  return (
    <div>
      <PageHeader
        title="Products"
        subtitle="Fertilizer, pesticide & seed master with category-specific attributes"
        actions={
          <div className="row">
            <ExportButtons title="Products" columns={[
              { key: "name", label: "Product" }, { key: "sku", label: "SKU" },
              { key: "category", label: "Category" }, { key: "hsn_code", label: "HSN" },
              { key: "gst_rate", label: "GST%" }, { key: "sale_price", label: "Sale", num: true, money: true },
            ]} rows={filtered} />
            <button className="btn btn-primary" onClick={openCreate}><Plus size={16} /> Add Product</button>
          </div>
        }
      />
      <Card>
        <div className="row mb-16" style={{ justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div className="tabs" style={{ marginBottom: 0 }}>
            {["", "fertilizer", "pesticide", "seed"].map((c) => (
              <button key={c || "all"} className={`tab ${cat === c ? "active" : ""}`} onClick={() => setCat(c)}>
                {c === "" ? "All" : c[0].toUpperCase() + c.slice(1)}
              </button>
            ))}
          </div>
          <div className="row" style={{ position: "relative", maxWidth: 320, flex: 1 }}>
            <Search size={17} style={{ position: "absolute", left: 12, color: "#94a3b8" }} />
            <input placeholder="Search name, SKU or barcode…" value={q} onChange={(e) => setQ(e.target.value)} style={{ paddingLeft: 36 }} />
          </div>
        </div>
        <Table
          columns={[
            { key: "fav", label: "", render: (r) => (
              <button className={`fav-star ${r.is_favorite ? "on" : ""}`} style={{ position: "static", boxShadow: "none" }} title="POS favorite"
                onClick={() => toggleFav(r)}><Star size={14} fill={r.is_favorite ? "currentColor" : "none"} /></button>
            ) },
            { key: "name", label: "Product", render: (r) => (
              <span className="row" style={{ gap: 8 }}><span className="cat-dot" style={{ background: CATEGORY_COLORS[r.category] }} />{r.name}</span>
            ) },
            { key: "sku", label: "SKU" },
            { key: "category", label: "Category", render: (r) => <Badge>{r.category}</Badge> },
            { key: "hsn_code", label: "HSN" },
            { key: "gst_rate", label: "GST%", num: true },
            { key: "sale_price", label: "Sale", num: true, render: (r) => inr(r.sale_price) },
            { key: "pack", label: "Pack", render: (r) => r.allows_loose
              ? <span>{r.pack_size}{r.loose_unit} <Badge tone="info">loose kg</Badge></span>
              : (r.sale_unit || r.base_unit || "—") },
            { key: "reorder_level", label: "Reorder", num: true },
            { key: "actions", label: "", render: (r) => (
              <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                <button className="icon-btn" style={{ width: 30, height: 30 }} title="Edit" onClick={() => openEdit(r)}><Pencil size={14} /></button>
                <button className="icon-btn" style={{ width: 30, height: 30 }} title="Delete" onClick={() => remove(r)}><Trash2 size={14} /></button>
              </div>
            ) },
          ]}
          rows={filtered}
          empty="No products"
          pageSize={50}
        />
      </Card>

      {open && (
        <Modal title={editId ? "Edit Product" : "Add Product"} onClose={() => setOpen(false)}
          footer={<><button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button><button className="btn btn-primary" onClick={submit}>Save</button></>}>
          {err && <div className="error">{err}</div>}
          <div className="grid grid-2">
            <Field label="SKU" required><input value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} /></Field>
            <Field label="Name" required><input value={form.name} onChange={(e) => {
              const name = e.target.value;
              const w = parseWeight(name);
              setForm({ ...form, name, pack_size: form.pack_size || (w && w[0] > 1 ? String(w[0]) : form.pack_size) });
            }} /></Field>
            <Field label="Category">
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                <option value="fertilizer">Fertilizer</option><option value="pesticide">Pesticide</option><option value="seed">Seed</option>
              </select>
            </Field>
            <Field label="Base unit">
              {bundle.units.length ? (
                <select value={form.base_unit} onChange={(e) => setForm({ ...form, base_unit: e.target.value })}>
                  <ConfigOptions items={bundle.units} current={form.base_unit} />
                </select>
              ) : (
                <input value={form.base_unit} onChange={(e) => setForm({ ...form, base_unit: e.target.value })} />
              )}
            </Field>
            <Field label="HSN code">
              <input
                list="hsn-options"
                value={form.hsn_code}
                onChange={(e) => {
                  const hsn_code = e.target.value;
                  const hit = bundle.hsn.find((h) => h.code === hsn_code);
                  setForm({
                    ...form,
                    hsn_code,
                    gst_rate: hit?.extra?.gst_rate != null ? String(hit.extra.gst_rate) : form.gst_rate,
                  });
                }}
              />
              <datalist id="hsn-options">
                {bundle.hsn.map((h) => (
                  <option key={h.id} value={h.code}>{h.name}</option>
                ))}
              </datalist>
            </Field>
            <Field label="GST %">
              <GstSelect value={form.gst_rate} onChange={(gst_rate) => setForm({ ...form, gst_rate })} bundle={bundle} />
            </Field>
            <Field label="Purchase price"><input type="number" value={form.purchase_price} onChange={(e) => setForm({ ...form, purchase_price: e.target.value })} /></Field>
            <Field label="Sale price"><input type="number" value={form.sale_price} onChange={(e) => setForm({ ...form, sale_price: e.target.value })} /></Field>
            <Field label="MRP"><input type="number" value={form.mrp} onChange={(e) => setForm({ ...form, mrp: e.target.value })} /></Field>
            <Field label="Reorder level"><input type="number" value={form.reorder_level} onChange={(e) => setForm({ ...form, reorder_level: e.target.value })} /></Field>
          </div>
          <label className="row" style={{ gap: 8, cursor: "pointer", width: "auto", marginBottom: 12 }}>
            <input type="checkbox" style={{ width: "auto" }} checked={!!form.sell_loose}
              onChange={(e) => setForm({ ...form, sell_loose: e.target.checked })} />
            Also sell loose by kg (open this bag and bill 1 kg, 5 kg, …)
          </label>
          {!!form.sell_loose && (
            <Field label="Bag size (kg)">
              <input type="number" min={0.001} step="0.001" value={form.pack_size}
                placeholder="e.g. 50, 45 or 25"
                onChange={(e) => setForm({ ...form, pack_size: e.target.value })} />
            </Field>
          )}
          {!!form.sell_loose && (
            <p className="muted" style={{ fontSize: 12, marginTop: -8 }}>
              Any bag size works. Stock is counted in bags — selling 1 kg from a 50 kg bag reduces 0.02 bag; from 25 kg, 0.04 bag.
            </p>
          )}

          {form.category === "fertilizer" && (
            <div className="grid grid-3">
              <Field label="N %"><input type="number" value={form.npk_n} onChange={(e) => setForm({ ...form, npk_n: e.target.value })} /></Field>
              <Field label="P %"><input type="number" value={form.npk_p} onChange={(e) => setForm({ ...form, npk_p: e.target.value })} /></Field>
              <Field label="K %"><input type="number" value={form.npk_k} onChange={(e) => setForm({ ...form, npk_k: e.target.value })} /></Field>
            </div>
          )}
          {form.category === "pesticide" && (
            <Field label="Toxicity class">
              {bundle.toxicity_classes.length ? (
                <select value={form.toxicity_class} onChange={(e) => setForm({ ...form, toxicity_class: e.target.value })}>
                  <option value="">Select class</option>
                  <ConfigOptions items={bundle.toxicity_classes} current={form.toxicity_class} />
                </select>
              ) : (
                <input value={form.toxicity_class} onChange={(e) => setForm({ ...form, toxicity_class: e.target.value })} placeholder="e.g. Class II" />
              )}
            </Field>
          )}
          {form.category === "seed" && (
            <div className="grid grid-2">
              <Field label="Germination %"><input type="number" value={form.germination_pct} onChange={(e) => setForm({ ...form, germination_pct: e.target.value })} /></Field>
              <Field label="Seed lot"><input value={form.seed_lot} onChange={(e) => setForm({ ...form, seed_lot: e.target.value })} /></Field>
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}
