"""Test fixtures. Uses a throwaway SQLite file so tests never touch MySQL."""
import os
import tempfile

os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/skac_test.db"
)
# Keep the settings cache from picking up a developer's real .env.
os.environ.pop("DB_HOST", None)
os.environ.pop("DB_NAME", None)

from datetime import date  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.models  # noqa: F401,E402  (register ORM metadata)
from app.core.database import Base  # noqa: E402
from app.models.enums import ProductCategory  # noqa: E402
from app.models.inventory import Batch  # noqa: E402
from app.models.organization import Branch, Organization  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.services import inventory as inv  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False, future=True)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def org(db):
    o = Organization(name="Test Agri")
    db.add(o)
    db.flush()
    return o


@pytest.fixture()
def branch(db, org):
    b = Branch(organization_id=org.id, code="BR01", name="Main")
    db.add(b)
    db.flush()
    return b


@pytest.fixture()
def make_product(db, org):
    def _make(name="Urea 50 KGS", sku="SKU1", gst_rate="5", sale_price="300", **kw):
        p = Product(
            organization_id=org.id,
            sku=sku,
            name=name,
            category=ProductCategory.fertilizer,
            gst_rate=Decimal(gst_rate),
            sale_price=None if sale_price is None else Decimal(sale_price),
            purchase_price=Decimal(str(kw.pop("purchase_price", "250"))),
            base_unit=kw.pop("base_unit", "bag"),
            **kw,
        )
        db.add(p)
        db.flush()
        return p

    return _make


@pytest.fixture()
def receive(db, org, branch):
    """Put `qty` of a product into stock on a batch with the given expiry."""

    def _receive(product, batch_no, qty, expiry=None, purchase_price="250"):
        b = Batch(
            organization_id=org.id,
            product_id=product.id,
            batch_no=batch_no,
            expiry_date=expiry,
            mfg_date=date(2026, 1, 1),
            purchase_price=Decimal(purchase_price),
        )
        db.add(b)
        db.flush()
        inv.receive_stock(
            db,
            organization_id=org.id,
            branch_id=branch.id,
            product_id=product.id,
            batch_id=b.id,
            quantity=Decimal(qty),
        )
        db.flush()
        return b

    return _receive
