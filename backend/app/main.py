"""SKAC FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

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

app.add_middleware(GZipMiddleware, minimum_size=1000)
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
    """Create any missing tables/columns/indexes (local SQLite / first-run convenience)."""
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    columns = {t: {c["name"] for c in insp.get_columns(t)} for t in tables}
    indexes = {t: {idx["name"] for idx in insp.get_indexes(t)} for t in tables}

    def add_column(table: str, column: str, ddl: str) -> None:
        if table not in tables or column in columns.get(table, set()):
            return
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
        columns.setdefault(table, set()).add(column)

    def add_index(table: str, name: str, cols: str) -> None:
        if table not in tables or name in indexes.get(table, set()):
            return
        try:
            with engine.begin() as conn:
                conn.execute(text(f"CREATE INDEX {name} ON {table} ({cols})"))
        except Exception:
            return
        indexes.setdefault(table, set()).add(name)

    add_column("product", "is_favorite", "is_favorite BOOLEAN NOT NULL DEFAULT 0")
    add_column("customer", "aadhaar_no", "aadhaar_no VARCHAR(12)")
    add_column("branch", "printer_name", "printer_name VARCHAR(120)")
    add_column("branch", "printer_type", "printer_type VARCHAR(20) DEFAULT 'thermal'")
    add_column("branch", "thermal_paper_mm", "thermal_paper_mm INTEGER NOT NULL DEFAULT 80")
    add_column("purchase_return_item", "hsn_code", "hsn_code VARCHAR(12)")
    add_column("purchase_return_item", "packing", "packing VARCHAR(20)")
    add_column("purchase_return_item", "gst_rate", "gst_rate NUMERIC(5, 2) NOT NULL DEFAULT 0")
    add_column("purchase_return_item", "taxable_value", "taxable_value NUMERIC(14, 2) NOT NULL DEFAULT 0")
    add_column("customer_payment", "reversed_at", "reversed_at DATETIME")
    add_column("customer_payment", "reversed_by_user_id", "reversed_by_user_id BIGINT")
    add_column("customer_payment", "reversal_reason", "reversal_reason VARCHAR(255)")
    add_column("vendor_payment", "reversed_at", "reversed_at DATETIME")
    add_column("vendor_payment", "reversed_by_user_id", "reversed_by_user_id BIGINT")
    add_column("vendor_payment", "reversal_reason", "reversal_reason VARCHAR(255)")
    add_index("customer", "ix_customer_aadhaar_no", "aadhaar_no")
    add_index("customer", "ix_customer_name", "name")
    add_index("customer", "ix_customer_org_name", "organization_id, name")
    add_index("customer_payment", "ix_customer_payment_paid_at", "paid_at")
    add_index("customer_payment", "ix_customer_payment_org_paid", "organization_id, paid_at")
    add_index("invoice", "ix_invoice_org_status_date", "organization_id, status, invoice_date")
    add_index("invoice", "ix_invoice_org_date_id", "organization_id, invoice_date, id")
    add_index("invoice_item", "ix_invoice_item_product_id", "product_id")
    add_index("invoice_item", "ix_invoice_item_batch_no", "batch_no")
    add_index("stock_movement", "ix_stock_movement_product_id", "product_id")
    add_index("stock_movement", "ix_stock_movement_occurred_at", "occurred_at")
    add_index(
        "stock_movement",
        "ix_stock_movement_org_prod_type_at",
        "organization_id, product_id, movement_type, occurred_at",
    )
    db = SessionLocal()
    try:
        from app.seed import ensure_roles
        from app.services.config_defaults import ensure_config_defaults
        ensure_roles(db)
        ensure_config_defaults(db)
        db.commit()
    finally:
        db.close()


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
