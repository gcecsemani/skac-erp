"""Inventory service: FIFO / expiry-first batch allocation and stock updates."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MovementType
from app.models.inventory import Batch, Stock, StockMovement


@dataclass
class Allocation:
    """A slice of a requested quantity taken from a specific batch."""

    batch_id: int
    batch_no: str
    mfg_date: date | None
    expiry_date: date | None
    quantity: Decimal
    purchase_price: Decimal


class InsufficientStock(Exception):
    def __init__(self, product_id: int, requested: Decimal, available: Decimal):
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product {product_id}: "
            f"requested {requested}, available {available}"
        )


def describe_shortfall(db: Session, exc: InsufficientStock) -> str:
    from app.models.product import Product

    product = db.get(Product, exc.product_id)
    name = product.name if product else "This item"
    unit = (getattr(product, "base_unit", None) or "units")
    req = f"{exc.requested:g}"
    avail = f"{exc.available:g}"
    if exc.available <= 0:
        return f"{name} is out of stock at this branch. Receive stock before billing it."
    return (
        f"Not enough stock for {name}. You requested {req} {unit}, "
        f"but only {avail} {unit} is available at this branch."
    )


def available_quantity(db: Session, branch_id: int, product_id: int) -> Decimal:
    rows = db.scalars(
        select(Stock.quantity).where(
            Stock.branch_id == branch_id, Stock.product_id == product_id
        )
    ).all()
    return sum(rows, Decimal("0"))


def allocate_fifo(
    db: Session,
    *,
    branch_id: int,
    product_id: int,
    quantity: Decimal,
    allow_oversell: bool = False,
) -> list[Allocation]:
    """Allocate `quantity` across batches, expiry-first then oldest-received.

    Expiry-first satisfies the regulatory intent (sell soon-to-expire stock
    before it becomes unsaleable). Batches with no expiry sort last.
    """
    stocks = db.scalars(
        select(Stock)
        .join(Batch, Batch.id == Stock.batch_id)
        .where(
            Stock.branch_id == branch_id,
            Stock.product_id == product_id,
            Stock.quantity > 0,
        )
    ).all()

    # Sort: earliest expiry first (None last), then oldest batch id.
    far_future = date.max

    def sort_key(s: Stock):
        exp = s.batch.expiry_date or far_future
        return (exp, s.batch_id)

    stocks.sort(key=sort_key)

    remaining = Decimal(quantity)
    allocations: list[Allocation] = []
    for stock in stocks:
        if remaining <= 0:
            break
        take = min(stock.quantity, remaining)
        allocations.append(
            Allocation(
                batch_id=stock.batch_id,
                batch_no=stock.batch.batch_no,
                mfg_date=stock.batch.mfg_date,
                expiry_date=stock.batch.expiry_date,
                quantity=take,
                purchase_price=stock.batch.purchase_price,
            )
        )
        remaining -= take

    if remaining > 0 and not allow_oversell:
        raise InsufficientStock(
            product_id, Decimal(quantity), Decimal(quantity) - remaining
        )

    return allocations


def apply_issue(
    db: Session,
    *,
    organization_id: int,
    branch_id: int,
    product_id: int,
    allocations: list[Allocation],
    movement_type: MovementType,
    ref_type: str | None = None,
    ref_id: int | None = None,
    occurred_at: datetime | None = None,
) -> None:
    """Decrement stock and write movement ledger rows for each allocation."""
    occurred_at = occurred_at or datetime.utcnow()
    for alloc in allocations:
        stock = db.scalar(
            select(Stock).where(
                Stock.branch_id == branch_id, Stock.batch_id == alloc.batch_id
            )
        )
        if stock is not None:
            stock.quantity = stock.quantity - alloc.quantity
        db.add(
            StockMovement(
                organization_id=organization_id,
                branch_id=branch_id,
                product_id=product_id,
                batch_id=alloc.batch_id,
                movement_type=movement_type,
                quantity=-alloc.quantity,
                ref_type=ref_type,
                ref_id=ref_id,
                occurred_at=occurred_at,
            )
        )


def receive_stock(
    db: Session,
    *,
    organization_id: int,
    branch_id: int,
    product_id: int,
    batch_id: int,
    quantity: Decimal,
    movement_type: MovementType = MovementType.grn,
    ref_type: str | None = None,
    ref_id: int | None = None,
    occurred_at: datetime | None = None,
) -> Stock:
    """Increment (or create) stock for a batch and write an inflow movement."""
    occurred_at = occurred_at or datetime.utcnow()
    stock = db.scalar(
        select(Stock).where(Stock.branch_id == branch_id, Stock.batch_id == batch_id)
    )
    if stock is None:
        stock = Stock(
            organization_id=organization_id,
            branch_id=branch_id,
            product_id=product_id,
            batch_id=batch_id,
            quantity=Decimal("0"),
        )
        db.add(stock)
    stock.quantity = stock.quantity + Decimal(quantity)

    db.add(
        StockMovement(
            organization_id=organization_id,
            branch_id=branch_id,
            product_id=product_id,
            batch_id=batch_id,
            movement_type=movement_type,
            quantity=Decimal(quantity),
            ref_type=ref_type,
            ref_id=ref_id,
            occurred_at=occurred_at,
        )
    )
    return stock
