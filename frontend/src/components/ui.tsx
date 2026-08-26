import { CSSProperties, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { Loader2, Inbox, Search, X, FileSpreadsheet, FileText } from "lucide-react";
import { exportExcel, exportPdf, type ExportColumn } from "../export";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}

export function Card({ title, icon, actions, children, className }: {
  title?: string; icon?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string;
}) {
  return (
    <div className={`card ${className ?? ""}`}>
      {(title || actions) && (
        <div className="card-head">
          <div className="card-title">{icon}{title}</div>
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}

export function StatCard({ label, value, sub, icon, tone = "bg-brand" }: {
  label: string; value: ReactNode; sub?: string; icon: ReactNode; tone?: string;
}) {
  return (
    <div className="stat">
      <div className={`stat-icon ${tone}`}>{icon}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "success" | "warn" | "danger" | "info" | "neutral" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="loading"><Loader2 className="spin" /> {label}</div>;
}

export function Empty({ label = "No data yet" }: { label?: string }) {
  return <div className="empty"><Inbox size={30} style={{ marginBottom: 8, opacity: .5 }} /><div>{label}</div></div>;
}

export function Table({ columns, rows, empty }: {
  columns: { key: string; label: string; num?: boolean; render?: (row: any) => ReactNode }[];
  rows: any[];
  empty?: string;
}) {
  if (!rows || rows.length === 0) return <Empty label={empty} />;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c.key} className={c.num ? "num" : ""}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c.key} className={c.num ? "num" : ""}>
                  {c.render ? c.render(row) : row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ExportButtons({ title, subtitle = "", columns, rows }: {
  title: string; subtitle?: string; columns: ExportColumn[]; rows: any[];
}) {
  const disabled = !rows?.length;
  return (
    <div className="row export-btns">
      <button type="button" className="btn btn-ghost btn-sm" disabled={disabled}
        onClick={() => exportExcel(title, columns, rows)}>
        <FileSpreadsheet size={15} /> Excel
      </button>
      <button type="button" className="btn btn-ghost btn-sm" disabled={disabled}
        onClick={() => exportPdf(title, subtitle, columns, rows)}>
        <FileText size={15} /> PDF
      </button>
    </div>
  );
}

export function Modal({ title, onClose, children, footer, wide }: { title: string; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,.5)", zIndex: 60, display: "grid", placeItems: "center", padding: 16 }} onClick={onClose}>
      <div className="card" style={{ width: "100%", maxWidth: wide ? 760 : 520, maxHeight: "90vh", overflow: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div className="card-head">
          <div className="card-title">{title}</div>
          <button className="icon-btn" onClick={onClose}><X size={18} /></button>
        </div>
        {children}
        {footer && <div className="row" style={{ marginTop: 16, justifyContent: "flex-end" }}>{footer}</div>}
      </div>
    </div>
  );
}

export function Field({ label, children, error, required }: {
  label: string; children: ReactNode; error?: string; required?: boolean;
}) {
  return (
    <div className={`field ${error ? "invalid" : ""}`}>
      <label>{label}{required ? <span className="req"> *</span> : null}</label>
      {children}
      {error && <div className="field-error">{error}</div>}
    </div>
  );
}

export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="switch">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="switch-track" />
      {label}
    </label>
  );
}

export function BranchSelect({
  value, onChange, branches, allowAll = true, allLabel = "All branches",
}: {
  value: number; onChange: (id: number) => void; branches: any[]; allowAll?: boolean; allLabel?: string;
}) {
  const locked = !allowAll && branches.length <= 1;
  return (
    <select value={value} disabled={locked} onChange={(e) => onChange(Number(e.target.value))} style={{ width: "auto" }}>
      {allowAll && <option value={0}>{allLabel}</option>}
      {branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
    </select>
  );
}

export function SearchInput({
  value, onChange, placeholder = "Search…", style,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  style?: CSSProperties;
}) {
  return (
    <div style={{ position: "relative", flex: "1 1 220px", minWidth: 180, maxWidth: 360, ...style }}>
      <Search size={16} style={{ position: "absolute", left: 10, top: 11, color: "#94a3b8", pointerEvents: "none" }} />
      <input placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} style={{ paddingLeft: 32 }} />
    </div>
  );
}

/** Type-to-filter picker for vendors, products, districts, etc. */
export function SearchSelect({
  value,
  options,
  onChange,
  placeholder = "Search…",
  getLabel = (o: any) => o.name,
  getId = (o: any) => o.id,
  onQuery,
  disabled,
  allowEmpty,
  emptyLabel = "None",
}: {
  value: number | string | "" | undefined;
  options: any[];
  onChange: (id: any) => void;
  placeholder?: string;
  getLabel?: (o: any) => string;
  getId?: (o: any) => number | string;
  onQuery?: (q: string) => void;
  disabled?: boolean;
  allowEmpty?: boolean;
  emptyLabel?: string;
}) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState<any>(null);
  const box = useRef<HTMLDivElement>(null);
  const fromList = options.find((o) => String(getId(o)) === String(value));
  const selected = fromList || (picked && String(getId(picked)) === String(value) ? picked : null);
  const closedLabel = selected ? getLabel(selected) : (value ? String(value) : "");
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const list = needle
      ? options.filter((o) => getLabel(o).toLowerCase().includes(needle))
      : options;
    return list.slice(0, 80);
  }, [options, q, getLabel]);

  useEffect(() => {
    if (fromList) setPicked(fromList);
  }, [fromList]);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const pick = (id: any, item?: any) => {
    if (item) setPicked(item);
    onChange(id);
    setOpen(false);
    setQ("");
  };

  return (
    <div ref={box} style={{ position: "relative" }}>
      <input
        value={open ? q : closedLabel}
        placeholder={placeholder}
        disabled={disabled}
        onFocus={() => { if (disabled) return; setOpen(true); setQ(closedLabel); }}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
          onQuery?.(e.target.value);
        }}
      />
      {open && !disabled && (
        <div style={{
          position: "absolute", zIndex: 30, top: "100%", left: 0, right: 0, marginTop: 4,
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-sm)", boxShadow: "var(--shadow-lg)",
          maxHeight: 240, overflow: "auto",
        }}>
          {allowEmpty && (
            <button
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick("")}
              style={{
                width: "100%", textAlign: "left", background: !value ? "var(--surface-2)" : "none",
                border: "none", padding: "9px 12px", cursor: "pointer", fontSize: 13, color: "var(--text-3)",
              }}
            >
              {emptyLabel}
            </button>
          )}
          {filtered.length === 0 && <div className="muted" style={{ padding: "9px 12px", fontSize: 13 }}>No matches</div>}
          {filtered.map((o) => (
            <button
              key={String(getId(o))}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => pick(getId(o), o)}
              style={{
                width: "100%", textAlign: "left", background: String(getId(o)) === String(value) ? "var(--surface-2)" : "none",
                border: "none", padding: "9px 12px", cursor: "pointer", fontSize: 13,
              }}
            >
              {getLabel(o)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
