"""SKAC FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal, Base, engine
import app.models  # noqa: F401  (register ORM metadata)

app = FastAPI(
    title="SKAC — Sri Kumaran Agri Clinic",
    description=(
        "Enterprise cloud multi-branch billing & inventory platform for "
        "fertilizer / pesticide / seed retail."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
def _ensure_schema() -> None:
    """Create any missing tables/columns (local SQLite / first-run convenience)."""
    Base.metadata.create_all(engine)
    _add_column_if_missing("product", "is_favorite", "is_favorite BOOLEAN NOT NULL DEFAULT 0")
    _add_column_if_missing("customer", "aadhaar_no", "aadhaar_no VARCHAR(12)")
    _add_column_if_missing("branch", "printer_name", "printer_name VARCHAR(120)")
    _add_column_if_missing("branch", "printer_type", "printer_type VARCHAR(20) DEFAULT 'thermal'")
    _add_column_if_missing("branch", "thermal_paper_mm", "thermal_paper_mm INTEGER NOT NULL DEFAULT 80")
    _add_column_if_missing("purchase_return_item", "hsn_code", "hsn_code VARCHAR(12)")
    _add_column_if_missing("purchase_return_item", "packing", "packing VARCHAR(20)")
    _add_column_if_missing("purchase_return_item", "gst_rate", "gst_rate NUMERIC(5, 2) NOT NULL DEFAULT 0")
    _add_column_if_missing("purchase_return_item", "taxable_value", "taxable_value NUMERIC(14, 2) NOT NULL DEFAULT 0")
    _add_column_if_missing("purchase_return_item", "tax_amount", "tax_amount NUMERIC(14, 2) NOT NULL DEFAULT 0")
    _add_index_if_missing("customer", "ix_customer_aadhaar_no", "aadhaar_no")
    db = SessionLocal()
    try:
        from app.seed import ensure_roles
        from app.services.config_defaults import ensure_config_defaults
        ensure_roles(db)
        ensure_config_defaults(db)
        db.commit()
    finally:
        db.close()


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def _add_index_if_missing(table: str, name: str, column: str) -> None:
    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    existing = {idx["name"] for idx in insp.get_indexes(table)}
    if name in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"CREATE INDEX {name} ON {table} ({column})"))


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


@app.get("/", tags=["system"])
def root() -> dict:
    return {
        "app": "SKAC",
        "docs": "/docs",
        "api": settings.api_v1_prefix,
    }
