# SKAC Architecture

## 1. Design Principles

1. **Multi-branch from day one.** Every transactional row is scoped by
   `branch_id`; the schema never assumes a single branch. Adding branch #21
   is a data operation, not a migration.
2. **Offline-first POS.** A branch must be able to keep billing during an
   internet outage. The POS caches masters (products, prices, customers) and
   queues invoices locally, then syncs when connectivity resumes.
3. **Immutable finance.** A finalized invoice is never edited in place.
   Corrections happen via credit notes. Every mutation is audit-logged.
4. **Compliance is first-class.** Batch number, mfg/expiry date, and license
   numbers are required data on the relevant flows and printed invoices.
5. **Provider-agnostic AI, zero raw SQL.** The LLM can only call a fixed set of
   vetted, parameterized query functions ("tools"). It never sees or writes SQL.

## 2. High-Level Topology

```
                         ┌────────────────────────────┐
   Branch POS (React) ───┤  IndexedDB cache + sync     │
   Branch POS (React) ───┤  (offline queue)            │
                         └──────────────┬─────────────┘
                                        │ HTTPS/JSON (JWT)
                              ┌─────────▼─────────┐
                              │   FastAPI API      │  (stateless, horizontally
                              │   - Auth / RBAC    │   scalable behind LB)
                              │   - Domain modules │
                              │   - AI tool layer  │
                              └─────────┬─────────┘
                                        │ SQLAlchemy
                              ┌─────────▼─────────┐
                              │     MySQL 8        │  (managed DB, daily
                              │  (single source    │   backups + PITR)
                              │   of truth)        │
                              └────────────────────┘
```

## 3. Multi-Tenancy Model

SKAC is a single-organization-with-many-branches product, architected so it can
become full multi-tenant SaaS later:

- `organization` — the top tenant (the business). One row today; the FK exists
  everywhere so a second org can be onboarded without schema change.
- `branch` — belongs to an organization; carries GSTIN and FCO/pesticide/seed
  license numbers + validity dates.
- **Row-level scoping:** transactional tables (`invoice`, `stock`,
  `stock_movement`, `ledger_entry`, …) carry `organization_id` + `branch_id`.
  API queries are always filtered by the caller's allowed branch scope.
- **Access scope:** a user has a role and a set of branches they may act in.
  Owner/Admin sees all branches (consolidated dashboards); a Cashier is pinned
  to one branch.

Rationale: shared-schema, row-scoped tenancy gives the cheapest path to
consolidated cross-branch reporting (`SUM ... GROUP BY branch_id`) and the
easiest ops story for a small team, while the pervasive `organization_id`
keeps a true multi-tenant future open.

## 4. Offline-First POS Sync

- **Masters pull:** on login/online, POS pulls product/price/customer masters
  into IndexedDB with an `updated_at` watermark (delta sync).
- **Offline billing:** invoices are created against cached masters and stored in
  an outbox with a **client-generated UUID** (`client_uuid`).
- **Sync on reconnect:** the outbox is POSTed to `/sync/invoices`. The server
  upserts by `client_uuid` (idempotent), assigns the authoritative invoice
  number, decrements stock with **FIFO/expiry-first batch allocation**, and
  returns the canonical records.
- **Conflict policy:** invoices are append-only, so there is no edit conflict.
  Stock oversell during offline windows is surfaced as a reconciliation alert
  rather than silently rejected (a finalized farmer invoice is not voided by
  the system).

## 5. Security

- **AuthN:** JWT access + refresh tokens; passwords hashed with bcrypt (passlib).
- **2FA:** TOTP (pyotp) required for Owner/Admin accounts.
- **AuthZ:** role-based (Owner/Admin, Branch Manager, Cashier, Accountant,
  Auditor read-only) + branch scope + field-level guards (e.g. cashier cannot
  edit MRP or delete invoices).
- **Audit trail:** every create/update/delete on business entities writes an
  `audit_log` row (actor, action, entity, before/after diff, ip, timestamp).
- **AI safety:** tool-based DB access only; parameterized queries; per-tool
  branch-scope enforcement; the raw model output is never used to build SQL.

## 6. Performance & NFRs

- Invoice generation target < 1s: single transaction, indexed batch lookup,
  precomputed tax lines.
- Consolidated dashboard < 2s: summary aggregates are indexed by
  `(organization_id, branch_id, date)`; heavy analytics can move to
  materialized summary tables as volume grows.
- **Backup/DR:** managed MySQL daily backups + point-in-time recovery.
  Target RPO ≤ 24h (≤ 5 min with PITR), RTO ≤ 1h.
- **Scalability:** stateless API scales horizontally; DB read replicas can be
  added for reporting without schema change.

## 7. Module Map (backend)

```
app/
├── core/        config, database, security, rbac, audit, deps
├── models/      SQLAlchemy models (one file per domain area)
├── schemas/     Pydantic request/response models
├── api/v1/      routers: auth, branches, products, inventory,
│                customers, vendors, sales, accounting, ai, sync
└── services/    business logic: inventory (FIFO), billing, accounting,
                 ai (provider, assistant, tools, forecasting)
```
