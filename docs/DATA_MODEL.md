# SKAC Data Model

All tenant-owned tables carry `organization_id`; transactional tables also carry
`branch_id`. This is what makes N-branch scaling and consolidated reporting a
query concern, not a schema concern.

## Entities

### Tenancy & Identity
- **organization** — the business (top tenant).
- **branch** — selling location; GSTIN + FCO/pesticide/seed license numbers and
  validity dates (printed on invoices, drive renewal alerts).
- **role** — canonical roles: owner, admin, branch_manager, cashier, accountant, auditor.
- **user** — belongs to an organization + role; `totp_secret`/`totp_enabled` for 2FA.
- **user_branch** — many-to-many branch scope (owner/admin implicitly see all).

### Product & Inventory
- **product** — org-level master. `category` ∈ {fertilizer, pesticide, seed} with
  category-specific columns:
  - fertilizer: `npk_n`, `npk_p`, `npk_k`
  - pesticide: `toxicity_class`
  - seed: `germination_pct`, `seed_lot`
  - plus `hsn_code`, `gst_rate`, pricing, `reorder_level`, and a JSON `attributes`
    escape hatch.
- **product_unit** — alternate units + `factor_to_base` (e.g. 1 bag = 50 kg).
- **batch** — `batch_no`, `mfg_date`, `expiry_date`, `purchase_price`. Mandatory
  for regulatory traceability.
- **stock** — on-hand quantity per (branch, batch), in base units.
- **stock_movement** — append-only ledger of every inflow/outflow with
  `movement_type`, signed `quantity`, and a `ref_type`/`ref_id` back to the
  source document. This is the single source of truth for stock analytics and
  batch traceability.

### Sales
- **customer** — farmer master + CRM (village, district, land holding) + credit
  account (`credit_allowed`, `credit_limit`, `outstanding_balance`).
- **invoice** — GST invoice; `status` (draft→finalized→cancelled), `tax_type`
  (intra/inter), `payment_mode`, money totals, `client_uuid` (offline
  idempotency), per-branch `invoice_no`. Finalized invoices are immutable.
- **invoice_item** — one line per batch split. Snapshots `product_name`,
  `hsn_code`, `batch_no`, `mfg_date`, `expiry_date` so the printed record is
  permanent, plus tax breakup fields.

### Purchase & Finance (scaffolded)
- **vendor** — supplier master + `outstanding_balance` (payables).
- *(Phase 4)* purchase_order, grn, vendor_invoice, payment, ledger_account,
  journal_entry — hooks and module boundaries are in place.

### Audit
- **audit_log** — immutable: actor, action (create/update/delete), entity type/id,
  JSON before/after `changes`, ip, timestamp. Written by `core.audit.record_audit`
  from every mutating service/endpoint.

## Key Invariants
1. Stock is only ever changed through `stock_movement` + `stock` together
   (see `services/inventory.py`), never ad-hoc.
2. Issuance is **expiry-first, then oldest batch** (regulatory FIFO).
3. Invoices are **append-only**; corrections are credit notes (Phase 3), never
   in-place edits.
4. Money is stored as `NUMERIC` (no floats); rounding to 2 dp at line level.
