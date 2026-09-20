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


def describe_shortfall(
    db: Session,
    exc: InsufficientStock,
    *,
    billed_unit: str | None = None,
    billed_qty: Decimal | None = None,
) -> str:
    from app.core.units import is_loose_sale, pack_info
    from app.models.product import Product

    product = db.get(Product, exc.product_id)
    name = product.name if product else "This item"
    billed_unit = billed_unit or getattr(exc, "billed_unit", None)
    billed_qty = billed_qty if billed_qty is not None else getattr(exc, "billed_qty", None)
    unit = (getattr(product, "sale_unit", None) or getattr(product, "base_unit", None) or "units")
    req = Decimal(exc.requested)
    avail = Decimal(exc.available)
    if product is not None and is_loose_sale(product, billed_unit):
        info = pack_info(product)
        unit = billed_unit or info.loose_unit or unit
        req = Decimal(billed_qty) if billed_qty is not None else (req * info.pack_size)
        avail = avail * info.pack_size
    if avail <= 0:
        return f"{name} is out of stock at this branch. Receive stock before billing it."

    def _fmt(n: Decimal) -> str:
        s = format(n.normalize(), "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s

    return (
        f"Not enough stock for {name}. You requested {_fmt(req)} {unit}, "
        f"but only {_fmt(avail)} {unit} is available at this branch."
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
    # Join the batch in and sort in SQL: earliest expiry first (None last),
    # then oldest batch. Reading batches through the relationship issued one
    # query per candidate batch.
    rows = db.execute(
        select(Stock, Batch)
        .join(Batch, Batch.id == Stock.batch_id)
        .where(
            Stock.branch_id == branch_id,
            Stock.product_id == product_id,
            Stock.quantity > 0,
        )
        .order_by(
            Batch.expiry_date.is_(None),
            Batch.expiry_date.asc(),
            Stock.batch_id.asc(),
        )
    ).all()

    remaining = Decimal(quantity)
    allocations: list[Allocation] = []
    for stock, batch in rows:
        if remaining <= 0:
            break
        take = min(stock.quantity, remaining)
        allocations.append(
            Allocation(
                batch_id=stock.batch_id,
                batch_no=batch.batch_no,
                mfg_date=batch.mfg_date,
                expiry_date=batch.expiry_date,
                quantity=take,
                purchase_price=batch.purchase_price,
            )
        )
        remaining -= take

    if remaining > 0 and not allow_oversell:
        raise InsufficientStock(
            product_id, Decimal(quantity), Decimal(quantity) - remaining
        )

    return allocations


def issue_from_batch(
    db: Session,
    *,
    organization_id: int,
    branch_id: int,
    product_id: int,
    batch_id: int,
    quantity: Decimal,
    movement_type: MovementType,
    ref_type: str | None = None,
    ref_id: int | None = None,
    note: str | None = None,
) -> None:
    """Issue a specific batch (purchase returns must go back on the GRN batch)."""
    stock = db.scalar(
        select(Stock).where(Stock.branch_id == branch_id, Stock.batch_id == batch_id)
    )
    available = stock.quantity if stock is not None else Decimal("0")
    qty = Decimal(quantity)
    if qty > available:
        raise InsufficientStock(product_id, qty, available)
    batch = db.get(Batch, batch_id)
    apply_issue(
        db,
        organization_id=organization_id,
        branch_id=branch_id,
        product_id=product_id,
        allocations=[
            Allocation(
                batch_id=batch_id,
                batch_no=batch.batch_no if batch else "",
                mfg_date=batch.mfg_date if batch else None,
                expiry_date=batch.expiry_date if batch else None,
                quantity=qty,
                purchase_price=batch.purchase_price if batch else Decimal("0"),
            )
        ],
        movement_type=movement_type,
        ref_type=ref_type,
        ref_id=ref_id,
        note=note,
    )


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
    note: str | None = None,
) -> None:
    """Decrement stock and write movement ledger rows for each allocation."""
    occurred_at = occurred_at or datetime.utcnow()
    batch_ids = {a.batch_id for a in allocations}
    stocks: dict[int, Stock] = (
        {
            s.batch_id: s
            for s in db.scalars(
                select(Stock).where(
                    Stock.branch_id == branch_id, Stock.batch_id.in_(batch_ids)
                )
            ).all()
        }
        if batch_ids
        else {}
    )
    for alloc in allocations:
        stock = stocks.get(alloc.batch_id)
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
                note=note,
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
    note: str | None = None,
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
            note=note,
        )
    )
    return stock
