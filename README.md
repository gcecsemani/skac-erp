# SKAC — Sri Kumaran Agri Clinic

**Enterprise Cloud Multi-Branch Billing & Inventory Platform for Fertilizer / Pesticide / Seed Retail**

SKAC is a cloud-hosted, multi-branch, multi-user billing platform for regulated
agri-input retail (fertilizers, pesticides, seeds). It replaces manual/legacy
billing with GST-compliant invoicing, batch/expiry-aware inventory, double-entry
accounting, statutory compliance reporting, and an AI business assistant.

> This repository is architected for **N branches from day one** and is designed
> to scale from 2 branches to 20+ without schema redesign.

---

## Tech Stack

| Layer            | Choice                                   |
| ---------------- | ---------------------------------------- |
| Backend API      | Python **FastAPI** (SQLAlchemy 2.0)      |
| Database         | **MySQL 8**                              |
| Migrations       | Alembic                                  |
| Frontend         | **React** (Vite + TypeScript)            |
| Offline POS      | IndexedDB (browser) + sync-on-reconnect  |
| Reporting/BI     | React dashboard + charts (Recharts)      |
| AI               | Provider-agnostic LLM (Gemini/Groq free tiers) via a **secure tool/function layer** — no raw SQL from the model |
| Cloud            | DigitalOcean Linux droplet (Docker)      |

**Stack deviations:** none from the requested stack. Notes:
- We use **SQLAlchemy 2.0 + Alembic** on top of MySQL for typed models and safe
  schema evolution.
- The AI layer is **provider-agnostic** so you can point it at any free-tier LLM
  (Google Gemini, Groq, etc.) via environment config, and it **never executes
  model-generated SQL** — the model can only call a fixed catalogue of vetted
  read functions.

---

## Repository Layout

```
SKAC/
├── backend/        FastAPI service (API, domain models, AI, services)
├── frontend/       React + Vite + TypeScript app (POS, dashboards)
├── deploy/         Docker Compose, Dockerfiles, DigitalOcean notes
└── docs/           Architecture, data model, roadmap, compliance notes
```

---

## Quick Start (local, Docker)

```bash
cp backend/.env.example backend/.env
cd deploy
docker compose up --build
```

- API:      http://localhost:8000  (docs at `/docs`)
- Frontend: http://localhost:5173

Then seed demo data (org, 2 branches, roles, sample products):

```bash
docker compose exec api python -m app.seed
```

## Quick Start (local, no Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # point DATABASE_URL at your MySQL
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload

# Frontend
cd ../frontend
npm install
npm run dev
```

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — system design, multi-tenancy, offline sync, security
- [Roadmap](docs/ROADMAP.md) — phased delivery plan and current status
- [Data Model](docs/DATA_MODEL.md) — core entities and relationships
- [AI Assistant](docs/AI.md) — secure tool-based NL querying + demand forecasting

## License / Compliance

This software is built for agri-input retail regulated under India's Fertilizer
Control Order, Insecticides Act, and Seeds Act. Batch/expiry tracking, license
numbers on invoices, and batch traceability are treated as **first-class
requirements**, not optional features.
