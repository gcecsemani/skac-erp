import { inr, inrWords } from "./format";

function esc(s: unknown) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

const FARMER_PESTICIDE_DISCLAIMER =
  "பூச்சி மருந்து விஷம் என அறிவேன். இதை விவசாயத்திற்கு மட்டுமே பயன்படுத்துவேன் என்று உறுதி கூறுகிறேன்.";

function money(n: unknown) {
  return Number(n ?? 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function dmy(iso: unknown) {
  const s = String(iso ?? "").slice(0, 10);
  const [y, m, d] = s.split("-");
  return y && m && d ? `${d}-${m}-${y}` : String(iso ?? "");
}

function panOf(gstin: unknown) {
  const g = String(gstin ?? "").replace(/\s/g, "").toUpperCase();
  return g.length >= 12 ? g.slice(2, 12) : "";
}

function openPrintHtml(html: string) {
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
  .ta { font-family: "Nirmala UI", "Tamil MN", "Tamil Sangam MN", "Latha", "Noto Sans Tamil", sans-serif; font-size: ${mm === 58 ? 10 : 11}px; line-height: 1.35; margin: 6px 0; }
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
<div class="ta">${esc(FARMER_PESTICIDE_DISCLAIMER)}</div>
<div class="muted" style="margin-top:10px">Farmer sign: ________________</div>
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
  openPrintHtml(docShell({
    title: doc.transfer_no || "Transfer", mm, a4, printer_name: doc.printer_name, body,
  }));
}

/** A4 GST debit note / purchase return — matches B2B tax-invoice layout. */
export function printDebitNote(doc: any) {
  const org = doc.organization_name || "Sri Kumaran Agri Clinic";
  const intra = (doc.tax_type || "intra") !== "inter";
  const items: any[] = doc.items || [];
  const taxableTotal = items.reduce((s, it) => s + Number(it.taxable_value ?? (Number(it.quantity) * Number(it.unit_price))), 0);
  const taxTotal = items.reduce((s, it) => s + Number(it.tax_amount || 0), 0);
  const grand = Number(doc.total ?? taxableTotal + taxTotal);
  const byRate = new Map<number, { taxable: number; tax: number }>();
  for (const it of items) {
    const rate = Number(it.gst_rate || 0);
    const cur = byRate.get(rate) || { taxable: 0, tax: 0 };
    cur.taxable += Number(it.taxable_value ?? (Number(it.quantity) * Number(it.unit_price)));
    cur.tax += Number(it.tax_amount || 0);
    byRate.set(rate, cur);
  }
  const taxRows = [...byRate.entries()].filter(([, v]) => v.tax > 0.004 || v.taxable > 0);
  const half = (n: number) => n / 2;
  const taxLineRows = taxRows.map(([rate, v]) => {
    if (intra) {
      const split = rate / 2;
      return [
        `<tr><td></td><td class="desc">CGST</td><td></td><td></td><td></td><td class="r">${split}</td><td class="r">${money(half(v.tax))}</td></tr>`,
        `<tr><td></td><td class="desc">SGST</td><td></td><td></td><td></td><td class="r">${split}</td><td class="r">${money(half(v.tax))}</td></tr>`,
      ].join("");
    }
    return `<tr><td></td><td class="desc">IGST</td><td></td><td></td><td></td><td class="r">${rate}</td><td class="r">${money(v.tax)}</td></tr>`;
  }).join("");

  const hsnMap = new Map<string, { hsn: string; taxable: number; rate: number; tax: number }>();
  for (const it of items) {
    const hsn = String(it.hsn_code || "");
    const rate = Number(it.gst_rate || 0);
    const key = `${hsn}|${rate}`;
    const cur = hsnMap.get(key) || { hsn, taxable: 0, rate, tax: 0 };
    cur.taxable += Number(it.taxable_value ?? (Number(it.quantity) * Number(it.unit_price)));
    cur.tax += Number(it.tax_amount || 0);
    hsnMap.set(key, cur);
  }
  const hsnRows = [...hsnMap.values()].map((r) => `
    <tr>
      <td>${esc(r.hsn)}</td>
      <td class="r">${money(r.taxable)}</td>
      ${intra
        ? `<td class="r">${r.rate / 2}</td><td class="r">${money(half(r.tax))}</td><td class="r">${r.rate / 2}</td><td class="r">${money(half(r.tax))}</td>`
        : `<td class="r">${r.rate}</td><td class="r">${money(r.tax)}</td><td></td><td></td>`}
      <td class="r">${money(r.tax)}</td>
    </tr>`).join("");

  const minRows = 8;
  const pad = Math.max(0, minRows - items.length);
  const itemRows = items.map((it: any, i: number) => {
    const taxable = Number(it.taxable_value ?? (Number(it.quantity) * Number(it.unit_price)));
    const extra = [
      it.batch_no && `Batch ${it.batch_no}`,
      it.expiry_date && `Exp ${dmy(it.expiry_date)}`,
    ].filter(Boolean).join(" · ");
    return `<tr>
      <td class="c">${i + 1}</td>
      <td class="desc">${esc(it.product_name)}${extra ? `<div class="sub">${esc(extra)}</div>` : ""}</td>
      <td class="c">${esc(it.hsn_code || "")}</td>
      <td class="c">${esc(it.packing || "")}</td>
      <td class="r">${esc(it.quantity)}</td>
      <td class="r">${money(it.unit_price)}</td>
      <td class="r">${money(taxable)}</td>
    </tr>`;
  }).join("") + Array.from({ length: pad }, () =>
    `<tr class="blank"><td>&nbsp;</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>`
  ).join("");

  const ourGstin = doc.branch_gstin || "";
  const buyerGstin = doc.vendor_gstin || "";
  const ourPan = doc.organization_pan || panOf(ourGstin);
  const buyerPan = doc.vendor_pan || panOf(buyerGstin);
  const state = doc.branch_state || "Tamil Nadu";
  const stateCode = doc.branch_state_code || "33";
  const hint = doc.printer_name
    ? `<div class="hint">Select printer: <strong>${esc(doc.printer_name)}</strong></div>`
    : `<div class="hint">Choose an A4 / laser printer in the print dialog.</div>`;

  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>${esc(doc.note_no || "Debit Note")}</title>
<style>
  @page { size: A4; margin: 8mm; }
  * { box-sizing: border-box; }
  body { font-family: Arial, "Nirmala UI", sans-serif; font-size: 11px; color: #000; margin: 0 auto; width: 194mm; }
  .hint { background: #fff7ed; border: 1px dashed #fdba74; padding: 6px; margin-bottom: 8px; font-size: 11px; }
  .sheet { border: 1px solid #000; }
  table { width: 100%; border-collapse: collapse; }
  td, th { border: 1px solid #000; padding: 4px 5px; vertical-align: top; }
  .nob { border: none; }
  .c { text-align: center; }
  .r { text-align: right; }
  .org { font-size: 16px; font-weight: 700; }
  .sub { font-size: 10px; color: #333; }
  .meta td { width: 50%; }
  .items th { font-size: 10px; background: #f3f3f3; }
  .items td { height: 18px; }
  .desc { font-weight: 600; }
  .tot { font-size: 13px; font-weight: 700; }
  .foot { font-size: 10px; }
  .signbox { height: 48px; }
  .center { text-align: center; }
  @media print { .hint { display: none; } body { width: auto; } }
</style></head><body>
${hint}
<div class="sheet">
  <table class="meta">
    <tr>
      <td rowspan="2">
        <div class="org">${esc(org)}</div>
        ${doc.branch_name && doc.branch_name !== org ? `<div>${esc(doc.branch_name)}</div>` : ""}
        <div>${esc(doc.branch_address || "")}</div>
        <div>State Name: ${esc(state)}, Code: ${esc(stateCode)}</div>
        ${doc.branch_phone ? `<div>Cell No: ${esc(doc.branch_phone)}</div>` : ""}
        ${ourGstin ? `<div>GSTIN: ${esc(ourGstin)}</div>` : ""}
      </td>
      <td>
        <div style="display:flex;justify-content:space-between"><span>Debit Note No</span><strong>${esc(doc.note_no || "")}</strong></div>
        <div style="display:flex;justify-content:space-between"><span>Dated</span><strong>${esc(dmy(doc.note_date))}</strong></div>
      </td>
      <td class="c" style="width:28%"><strong>Debit Note</strong><div class="sub">Purchase Return</div></td>
    </tr>
    <tr>
      <td>
        <div>Against GRN: ${esc(doc.grn_no || "")}</div>
        <div>Vendor Inv. No: ${esc(doc.vendor_invoice_no || "")}</div>
        ${doc.reason ? `<div>Reason: ${esc(doc.reason)}</div>` : ""}
      </td>
      <td>
        <div>Mode of Payments</div>
        <div>Destination: ${esc((doc.vendor_address || "").split(",")[0] || doc.vendor || "")}</div>
      </td>
    </tr>
    <tr>
      <td>
        <div class="sub">Buyer (Vendor)</div>
        <div class="org" style="font-size:13px">${esc(doc.vendor || "")}</div>
        <div>${esc(doc.vendor_address || "")}</div>
        ${doc.vendor_phone ? `<div>Cell: ${esc(doc.vendor_phone)}</div>` : ""}
        ${buyerGstin ? `<div>GSTIN: ${esc(buyerGstin)}</div>` : ""}
      </td>
      <td colspan="2">
        <div>Dispatch Document No: ${esc(doc.grn_no || "")}</div>
        <div>Dated: ${esc(dmy(doc.grn_date || doc.note_date))}</div>
        <div>Terms of Delivery: Goods returned to vendor</div>
      </td>
    </tr>
  </table>
  <table class="items">
    <tr>
      <th style="width:6%">SL No</th>
      <th>Description of Goods</th>
      <th style="width:11%">HSN Code</th>
      <th style="width:10%">Packing</th>
      <th style="width:9%">Quantity</th>
      <th style="width:10%">Rate</th>
      <th style="width:13%">Amount</th>
    </tr>
    ${itemRows}
    ${taxLineRows}
    <tr>
      <td></td><td class="desc">Total</td><td></td><td></td>
      <td class="r">${items.reduce((s, it) => s + Number(it.quantity || 0), 0)}</td>
      <td></td>
      <td class="r tot">${money(grand)}</td>
    </tr>
  </table>
  <table>
    <tr>
      <td>
        Amount Chargeable (in words)<br>
        <strong>${esc(inrWords(grand))}</strong>
      </td>
      <td class="r" style="width:28%">
        Taxable ${money(taxableTotal)}<br>
        ${intra ? `CGST ${money(half(taxTotal))}<br>SGST ${money(half(taxTotal))}` : `IGST ${money(taxTotal)}`}<br>
        <strong>Total ${money(grand)}</strong>
      </td>
    </tr>
  </table>
  <table>
    <tr>
      <td>Company's GSTIN: ${esc(ourGstin || "—")}</td>
      <td>Buyer's GSTIN: ${esc(buyerGstin || "—")}</td>
      <td>Company PAN: ${esc(ourPan || "—")}</td>
      <td>Buyer's PAN: ${esc(buyerPan || "—")}</td>
    </tr>
  </table>
  <table class="items">
    <tr>
      <th>HSN Codes</th>
      <th>Taxable Value</th>
      ${intra ? "<th>Central Tax Rate</th><th>Amount</th><th>State Tax Rate</th><th>Amount</th>" : "<th>Integrated Tax Rate</th><th>Amount</th><th></th><th></th>"}
      <th>Total Tax Amount</th>
    </tr>
    ${hsnRows || `<tr><td colspan="7" class="c">—</td></tr>`}
    <tr>
      <td class="r desc">Total</td>
      <td class="r">${money(taxableTotal)}</td>
      ${intra
        ? `<td></td><td class="r">${money(half(taxTotal))}</td><td></td><td class="r">${money(half(taxTotal))}</td>`
        : `<td></td><td class="r">${money(taxTotal)}</td><td></td><td></td>`}
      <td class="r">${money(taxTotal)}</td>
    </tr>
  </table>
  <table>
    <tr>
      <td class="foot" style="width:50%">
        <strong>Declaration:</strong><br>
        We declare that this debit note shows the actual price of the goods described and that all particulars are true and correct.
      </td>
      <td class="foot">
        <div>Received in Good Condition</div>
        <div class="signbox"></div>
        <div class="center">Buyer</div>
      </td>
      <td class="foot" style="width:28%">
        <div>For ${esc(org)}</div>
        <div class="signbox"></div>
        <div class="center">Authorised Signatory</div>
      </td>
    </tr>
  </table>
  <div class="center foot" style="padding:6px">This is Computer Generated Invoice no need Signature</div>
</div>
<script>window.onload = function () { setTimeout(function () { window.print(); }, 200); };</script>
</body></html>`;

  const w = window.open("", "_blank", "width=900,height=1100");
  if (!w) {
    alert("Allow pop-ups to print the debit note.");
    return;
  }
  w.document.write(html);
  w.document.close();
}
