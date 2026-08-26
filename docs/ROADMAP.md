# SKAC Delivery Roadmap

This is a large enterprise platform. Delivery is phased so each phase is
independently runnable and testable. The schema and module boundaries are laid
out up front so later phases add features, not rewrites.

Legend: ✅ done in this repo · 🚧 partial/scaffolded · ⬜ planned

## Phase 0 — Foundation
- ✅ Monorepo structure, docs, Docker Compose (MySQL + API)
- ✅ FastAPI app skeleton, config, DB session, health checks
- ✅ Alembic migrations wired to models
- ✅ Base model mixins (ids, timestamps, org/branch scope, soft-delete)

## Phase 1 — Identity, Tenancy & Security
- ✅ Organization + Branch masters (GSTIN, FCO/pesticide/seed licenses + validity)
- ✅ Users, Roles, RBAC scopes, branch assignment
- ✅ JWT auth (access/refresh), password hashing
- 🚧 TOTP 2FA for admin/owner (enrol + verify endpoints)
- ✅ Audit-log model + service hook

## Phase 2 — Product & Inventory
- ✅ Product master + category-specific attributes (fertilizer NPK, pesticide
  toxicity class, seed lot/germination %)
- ✅ HSN codes, units + conversion factors
- ✅ Batch + expiry tracking, per-branch stock
- 🚧 FIFO / expiry-first issuance service
- ⬜ Supplier master, Purchase Orders, GRN with batch capture
- ⬜ Reorder / low-stock / near-expiry alerts (push/email/SMS)
- ⬜ Inter-branch stock transfer with approval workflow

## Phase 3 — Sales / POS
- ✅ Customer (farmer) master with CRM + credit account fields
- 🚧 GST-compliant invoice model (CGST/SGST/IGST), immutable finalization
- 🚧 Batch/mfg/expiry/license on invoice lines (data model ready)
- ⬜ Keyboard-first POS UI, barcode entry, PDF/print with regional language
- ⬜ Payment modes (cash/credit/part/UPI/card), farmer khata ledger
- ⬜ Sales returns + credit notes, discount/scheme rules
- 🚧 Offline billing + `/sync` endpoint (design + stub)

## Phase 4 — Purchase & Accounting
- ⬜ PO → GRN → vendor invoice → payment cycle, purchase returns
- ⬜ Double-entry ledger auto-posting from sales/purchases
- ⬜ Day-book, cash-book, bank-book
- ⬜ Receivables/payables aging
- ⬜ GSTR-1 / GSTR-3B summaries
- ⬜ P&L by branch / category / season

## Phase 5 — Compliance & Reporting
- ⬜ License expiry tracking + renewal alerts
- ⬜ Batch/lot traceability (which farmer bought which batch)
- ⬜ Statutory register exports (Excel/PDF)
- ⬜ Stock valuation, fast/slow-moving, seasonal trend reports

## Phase 6 — AI
- ✅ Provider-agnostic LLM client (Gemini/Groq free tiers) + safe fallback
- ✅ Secure tool/function registry (no raw SQL) for NL business Q&A
- 🚧 NL reporting → controlled query mapping
- 🚧 Demand forecasting service (avg daily/weekly/monthly, trend, stock-out
  date, reorder point, recommended purchase qty)
- ⬜ AI Purchase Recommendation screen → convert to PO

## Current status of this repo
Phases 0–1 are functionally in place; Phase 2 core models + FIFO service and
Phase 6 AI tool layer + forecasting core are scaffolded and runnable. The
remaining items are wired into the module structure so they can be filled in
without schema/architecture changes.
