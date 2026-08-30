import { inr } from "./format";

function esc(s: unknown) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function openPrintHtml(title: string, html: string) {
  const w = window.open("", "_blank", "width=480,height=700");
  if (!w) {
    alert("Allow pop-ups to print the receipt.");
    return;
  }
  w.document.write(html);
  w.document.close();
}

function docShell(opts: {
  title: string;
  mm: number;
  a4?: boolean;
  printer_name?: string;
  body: string;
}) {
  const { title, mm, a4, printer_name, body } = opts;
  const hint = printer_name
    ? `<div class="hint">Select printer: <strong>${esc(printer_name)}</strong></div>`
    : `<div class="hint">Choose this branch printer in the print dialog.</div>`;
  const page = a4 ? "A4" : `${mm}mm auto`;
  const width = a4 ? "auto" : `${mm}mm`;
  const size = a4 ? 13 : mm === 58 ? 11 : 12;
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${esc(title)}</title>
<style>
  @page { size: ${page}; margin: ${a4 ? "14mm" : "3mm"}; }
  * { box-sizing: border-box; }
  body { font-family: ${a4 ? 'ui-sans-serif, system-ui, sans-serif' : 'ui-monospace, "Courier New", monospace'}; font-size: ${size}px; color: #111; margin: 0 auto; width: ${width}; max-width: ${a4 ? "190mm" : width}; }
  .center { text-align: center; }
  .muted { color: #444; font-size: ${a4 ? 12 : 10}px; }
  .hint { background: #fff7ed; border: 1px dashed #fdba74; padding: 6px; margin-bottom: 8px; font-size: 11px; }
  h1 { font-size: ${a4 ? 20 : 15}px; margin: 0 0 2px; }
  hr { border: none; border-top: 1px dashed #333; margin: 8px 0; }
  table { width: 100%; border-collapse: collapse; }
  td { vertical-align: top; padding: 3px 0; }
  .r { text-align: right; }
  .tot td { font-weight: 700; }
  .sign { display: flex; justify-content: space-between; margin-top: 28px; font-size: 11px; }
  .sign span { border-top: 1px solid #333; padding-top: 4px; min-width: 38%; text-align: center; }
  @media print { .hint { display: none; } }
</style></head><body>
${hint}
${body}
<script>window.onload = function () { setTimeout(function () { window.print(); }, 200); };</script>
</body></html>`;
}

function headerBlock(doc: any) {
  const org = doc.organization_name || "Sri Kumaran Agri Clinic";
  return `<div class="center">
  <h1>${esc(org)}</h1>
  <div>${esc(doc.branch_name || "")}</div>
  ${doc.branch_address ? `<div class="muted">${esc(doc.branch_address)}</div>` : ""}
  ${doc.branch_phone ? `<div>Ph: ${esc(doc.branch_phone)}</div>` : ""}
  ${doc.branch_gstin ? `<div>GSTIN: ${esc(doc.branch_gstin)}</div>` : ""}
</div>`;
}

/** Opens a thermal-width receipt and triggers the OS print dialog (USB/network printer). */
export function printThermalReceipt(inv: any) {
  const mm = Number(inv.thermal_paper_mm) === 58 ? 58 : 80;
  const org = inv.organization_name || "Sri Kumaran Agri Clinic";
  const due = Number(inv.grand_total) - Number(inv.amount_paid);
  const items = (inv.items || []).map((it: any) => `
    <tr>
      <td>${esc(it.product_name)}${it.batch_no ? `<div class="muted">B:${esc(it.batch_no)}</div>` : ""}</td>
      <td class="r">${esc(it.quantity)}</td>
      <td class="r">${Number(it.line_total).toFixed(2)}</td>
    </tr>`).join("");
  const licenses = [
    inv.branch_fco_license && `FCO ${esc(inv.branch_fco_license)}`,
    inv.branch_pesticide_license && `Pest. ${esc(inv.branch_pesticide_license)}`,
    inv.branch_seed_license && `Seed ${esc(inv.branch_seed_license)}`,
  ].filter(Boolean).join(" · ");
  const hint = inv.printer_name
    ? `<div class="hint">Select printer: <strong>${esc(inv.printer_name)}</strong></div>`
    : `<div class="hint">Choose this branch thermal printer in the print dialog.</div>`;

  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${esc(inv.invoice_no)}</title>
<style>
  @page { size: ${mm}mm auto; margin: 3mm; }
  * { box-sizing: border-box; }
  body { font-family: ui-monospace, "Courier New", monospace; font-size: ${mm === 58 ? 11 : 12}px; color: #111; margin: 0; width: ${mm}mm; }
  .center { text-align: center; }
  .muted { color: #444; font-size: 10px; }
  .hint { background: #fff7ed; border: 1px dashed #fdba74; padding: 6px; margin-bottom: 8px; font-size: 11px; }
  h1 { font-size: 15px; margin: 0 0 2px; }
  hr { border: none; border-top: 1px dashed #333; margin: 6px 0; }
  table { width: 100%; border-collapse: collapse; }
  td { vertical-align: top; padding: 2px 0; }
  .r { text-align: right; }
  .tot td { font-weight: 700; }
  @media print { .hint { display: none; } }
</style></head><body>
${hint}
<div class="center">
  <h1>${esc(org)}</h1>
  <div>${esc(inv.branch_name || "")}</div>
  ${inv.branch_address ? `<div class="muted">${esc(inv.branch_address)}</div>` : ""}
  ${inv.branch_phone ? `<div>Ph: ${esc(inv.branch_phone)}</div>` : ""}
  ${inv.branch_gstin ? `<div>GSTIN: ${esc(inv.branch_gstin)}</div>` : ""}
  ${licenses ? `<div class="muted">${licenses}</div>` : ""}
</div>
<hr>
<div class="center"><strong>TAX INVOICE</strong></div>
<div>Inv: ${esc(inv.invoice_no)}</div>
<div>Date: ${esc(inv.invoice_date)}</div>
<div>Farmer: ${esc(inv.customer_name || "Walk-in")}${inv.customer_phone ? ` · ${esc(inv.customer_phone)}` : ""}</div>
${inv.customer_village ? `<div class="muted">${esc(inv.customer_village)}</div>` : ""}
<hr>
<table>
  <tr><td><strong>Item</strong></td><td class="r"><strong>Qty</strong></td><td class="r"><strong>Amt</strong></td></tr>
  ${items}
</table>
<hr>
<table>
  <tr><td>Subtotal</td><td class="r">${Number(inv.subtotal).toFixed(2)}</td></tr>
  ${Number(inv.discount_total) > 0 ? `<tr><td>Discount</td><td class="r">- ${Number(inv.discount_total).toFixed(2)}</td></tr>` : ""}
  <tr><td>GST</td><td class="r">${Number(inv.tax_total).toFixed(2)}</td></tr>
  <tr class="tot"><td>TOTAL</td><td class="r">${inr(inv.grand_total).replace("₹", "Rs. ")}</td></tr>
  <tr><td>Paid (${esc(inv.payment_mode)})</td><td class="r">${Number(inv.amount_paid).toFixed(2)}</td></tr>
  ${due > 0.005 ? `<tr class="tot"><td>Balance (khata)</td><td class="r">${due.toFixed(2)}</td></tr>` : ""}
</table>
<hr>
<div class="center muted">Thank you · Visit again</div>
<script>window.onload = function () { setTimeout(function () { window.print(); }, 200); };</script>
</body></html>`;

  const w = window.open("", "_blank", "width=420,height=640");
  if (!w) {
    alert("Allow pop-ups to print the thermal receipt.");
    return;
  }
  w.document.write(html);
  w.document.close();
}

/** Stock transfer / delivery challan — same print flow as a tax invoice. */
export function printTransferReceipt(doc: any) {
  const mm = Number(doc.thermal_paper_mm) === 58 ? 58 : 80;
  const a4 = doc.printer_type === "a4";
  const items = (doc.items || []).map((it: any) => `
    <tr>
      <td>${esc(it.product_name)}${it.batch_no ? `<div class="muted">Batch ${esc(it.batch_no)}${it.expiry_date ? ` · Exp ${esc(it.expiry_date)}` : ""}</div>` : ""}</td>
      <td class="r">${esc(it.quantity)}</td>
    </tr>`).join("");
  const body = `${headerBlock(doc)}
<hr>
<div class="center"><strong>STOCK TRANSFER</strong></div>
<div class="center muted">Delivery challan (not a tax invoice)</div>
<div>No: ${esc(doc.transfer_no)}</div>
<div>Date: ${esc(doc.transfer_date)}</div>
<div>Status: ${esc(doc.status || "")}</div>
<hr>
<div><strong>From:</strong> ${esc(doc.from_branch || doc.branch_name || "")}</div>
<div><strong>To:</strong> ${esc(doc.to_branch || "")}</div>
${doc.notes ? `<div class="muted">${esc(doc.notes)}</div>` : ""}
<hr>
<table>
  <tr><td><strong>Item</strong></td><td class="r"><strong>Qty</strong></td></tr>
  ${items}
</table>
<hr>
<div class="sign"><span>Dispatched by</span><span>Received by</span></div>`;
  openPrintHtml(doc.transfer_no || "Transfer", docShell({
    title: doc.transfer_no || "Transfer", mm, a4, printer_name: doc.printer_name, body,
  }));
}

/** Vendor debit note for a purchase return. */
export function printDebitNote(doc: any) {
  const mm = Number(doc.thermal_paper_mm) === 58 ? 58 : 80;
  const a4 = doc.printer_type === "a4";
  const items = (doc.items || []).map((it: any) => `
    <tr>
      <td>${esc(it.product_name)}${it.batch_no ? `<div class="muted">B:${esc(it.batch_no)}</div>` : ""}</td>
      <td class="r">${esc(it.quantity)}</td>
      <td class="r">${Number(it.line_total).toFixed(2)}</td>
    </tr>`).join("");
  const body = `${headerBlock(doc)}
<hr>
<div class="center"><strong>DEBIT NOTE</strong></div>
<div class="center muted">Purchase return</div>
<div>No: ${esc(doc.note_no)}</div>
<div>Date: ${esc(doc.note_date)}</div>
<div>Vendor: ${esc(doc.vendor || "")}</div>
<div>Against GRN: ${esc(doc.grn_no || "")}</div>
${doc.reason ? `<div>Reason: ${esc(doc.reason)}</div>` : ""}
<hr>
<table>
  <tr><td><strong>Item</strong></td><td class="r"><strong>Qty</strong></td><td class="r"><strong>Amt</strong></td></tr>
  ${items}
</table>
<hr>
<table>
  <tr class="tot"><td>TOTAL</td><td class="r">${inr(doc.total).replace("₹", "Rs. ")}</td></tr>
</table>
<hr>
<div class="center muted">Goods returned to vendor · payable reduced</div>`;
  openPrintHtml(doc.note_no || "Debit note", docShell({
    title: doc.note_no || "Debit note", mm, a4, printer_name: doc.printer_name, body,
  }));
}
