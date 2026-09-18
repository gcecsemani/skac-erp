"""Batch/expiry tracking, per-branch stock, and stock movement ledger."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MovementType, StockDiscrepancyStatus
from app.models.mixins import PKMixin, TimestampMixin


class Batch(Base, PKMixin, TimestampMixin):
    """A manufactured lot of a product. Mandatory for agri-input traceability."""

    __tablename__ = "batch"
    __table_args__ = (
        UniqueConstraint("product_id", "batch_no", name="uq_batch_product_no"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id"), nullable=False, index=True
    )

    batch_no: Mapped[str] = mapped_column(String(80), nullable=False)
    mfg_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)

    # Cost captured at receipt (for FIFO valuation)
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))


class Stock(Base, PKMixin, TimestampMixin):
    """On-hand quantity of a batch at a branch."""

    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint("branch_id", "batch_id", name="uq_stock_branch_batch"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("product.id"), nullable=False, index=True
    )
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batch.id"), nullable=False, index=True
    )

    # Quantity is always stored in the product base unit.
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))

    batch: Mapped["Batch"] = relationship()


class StockMovement(Base, PKMixin, TimestampMixin):
    """Append-only ledger of every stock change (auditable)."""

    __tablename__ = "stock_movement"
    __table_args__ = (
        Index(
            "ix_stock_movement_org_prod_type_at",
            "organization_id", "product_id", "movement_type", "occurred_at",
        ),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False, index=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batch.id"), nullable=False)

    movement_type: Mapped[MovementType] = mapped_column(
        SAEnum(MovementType), nullable=False, index=True
    )
    # Positive for inflow, negative for outflow (in base units).
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)

    # Reference to the source document (invoice id, GRN id, transfer id, ...).
    ref_type: Mapped[str | None] = mapped_column(String(40))
    ref_id: Mapped[int | None] = mapped_column()
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(String(255))


class StockDiscrepancy(Base, PKMixin, TimestampMixin):
    """Physical count vs book qty — a case to trace missing (or extra) bags."""

    __tablename__ = "stock_discrepancy"
    __table_args__ = (
        Index("ix_stock_discrepancy_org_status", "organization_id", "status"),
        Index("ix_stock_discrepancy_org_product", "organization_id", "product_id", "branch_id"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False, index=True)

    count_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    book_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    counted_qty: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    variance: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)

    status: Mapped[StockDiscrepancyStatus] = mapped_column(
        SAEnum(StockDiscrepancyStatus), default=StockDiscrepancyStatus.open, nullable=False, index=True
    )
    note: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution: Mapped[str | None] = mapped_column(String(255))

    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    resolved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
