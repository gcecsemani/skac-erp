"""Farmer / customer master with CRM and credit-account fields."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import PKMixin, SoftDeleteMixin, TimestampMixin


class Customer(Base, PKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint("organization_id", "phone", name="uq_customer_org_phone"),
        Index("ix_customer_org_name", "organization_id", "name"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), index=True)
    aadhaar_no: Mapped[str | None] = mapped_column(String(12), index=True)
    village: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))

    # Optional CRM
    land_holding_acres: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    gstin: Mapped[str | None] = mapped_column(String(20))

    # Credit account (khata)
    credit_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    # Running balance owed by the customer (positive = customer owes us).
    outstanding_balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0")
    )


class CustomerPayment(Base, PKMixin, TimestampMixin):
    """Cash/UPI/card collected later against a farmer's khata balance."""

    __tablename__ = "customer_payment"
    __table_args__ = (
        Index("ix_customer_payment_org_paid", "organization_id", "paid_at"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branch.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"), nullable=False, index=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="cash")
    note: Mapped[str | None] = mapped_column(String(255))
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reversed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    reversal_reason: Mapped[str | None] = mapped_column(String(255))


class CustomerPaymentAllocation(Base, PKMixin, TimestampMixin):
    """How a khata receipt was applied to invoices (needed to reverse exactly)."""

    __tablename__ = "customer_payment_allocation"

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("customer_payment.id"), nullable=False, index=True
    )
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoice.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
