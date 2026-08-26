/** Excel (CSV that Excel opens) and print-to-PDF helpers for tabular data. */

export type ExportColumn = { key: string; label: string; money?: boolean; num?: boolean };

function cell(v: unknown): string {
  if (v == null || v === "") return "";
  if (typeof v === "number") return String(v);
  return String(v);
}

function numeric(v: unknown): string {
  if (v == null || v === "") return "";
  const n = Number(v);
  return Number.isFinite(n) ? String(n) : cell(v);
}

function csvEscape(s: string): string {
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
}

function downloadBlob(filename: string, mime: string, contents: string) {
  const blob = new Blob([contents], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    a.remove();
    URL.revokeObjectURL(url);
  }, 1500);
}

export function exportExcel(title: string, columns: ExportColumn[], rows: any[]) {
  if (!rows?.length) {
    alert("Nothing to export yet.");
    return;
  }
  const header = columns.map((c) => csvEscape(c.label)).join(",");
  const body = rows.map((r) =>
    columns.map((c) => {
      const raw = c.money || c.num ? numeric(r[c.key]) : cell(r[c.key]);
      return csvEscape(raw);
    }).join(",")
  ).join("\r\n");
  const csv = `\uFEFF${csvEscape(title)}\r\n${header}\r\n${body}`;
  const stamp = new Date().toISOString().slice(0, 10);
  downloadBlob(`${slug(title)}-${stamp}.csv`, "text/csv;charset=utf-8", csv);
}

export function exportPdf(title: string, subtitle: string, columns: ExportColumn[], rows: any[]) {
  if (!rows?.length) {
    alert("Nothing to export yet.");
    return;
  }
  const header = columns.map((c) => `<th>${escapeHtml(c.label)}</th>`).join("");
  const body = rows.map((r) =>
    `<tr>${columns.map((c) => {
      const align = c.num || c.money ? "right" : "left";
      const value = c.money || c.num ? numeric(r[c.key]) : cell(r[c.key]);
      return `<td style="text-align:${align}">${escapeHtml(value)}</td>`;
    }).join("")}</tr>`
  ).join("");
  const html = `<!doctype html><html><head><meta charset="utf-8"><title>${escapeHtml(title)}</title>
<style>
  body { font-family: Inter, system-ui, sans-serif; color: #0f172a; padding: 28px; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  p { color: #64748b; margin: 0 0 18px; font-size: 13px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { text-align: left; background: #0f5132; color: #fff; padding: 8px; }
  td { border-bottom: 1px solid #e2e8f0; padding: 7px 8px; }
  @media print { body { padding: 0; } }
</style></head><body>
  <h1>SKAC · ${escapeHtml(title)}</h1>
  <p>${escapeHtml(subtitle || "")}</p>
  <table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>
  <p style="margin-top:24px;font-size:11px">Generated ${new Date().toLocaleString("en-IN")}</p>
</body></html>`;

  const iframe = document.createElement("iframe");
  iframe.setAttribute("title", title);
  iframe.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0;opacity:0";
  document.body.appendChild(iframe);
  const win = iframe.contentWindow;
  if (!win) {
    iframe.remove();
    alert("Could not open the print dialog. Allow pop-ups for this site and try again.");
    return;
  }
  win.document.open();
  win.document.write(html);
  win.document.close();
  const cleanup = () => { try { iframe.remove(); } catch { /* already gone */ } };
  win.addEventListener("afterprint", cleanup);
  setTimeout(() => {
    try {
      win.focus();
      win.print();
    } catch {
      alert("Could not open the print dialog. Allow pop-ups for this site and try again.");
      cleanup();
    }
    setTimeout(cleanup, 60_000);
  }, 250);
}

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]!));
}

function slug(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "export";
}
