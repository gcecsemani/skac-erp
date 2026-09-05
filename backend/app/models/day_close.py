"""End-of-day cashier checkout: counted cash / UPI vs SKAC expected."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import PKMixin, TimestampMixin


class DayClose(Base, PKMixin, TimestampMixin):
    __tablename__ = "day_close"
    __table_args__ = (
        UniqueConstraint("branch_id", "close_date", name="uq_day_close_branch_date"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    closed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    close_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    opening_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    cash_in: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    cash_out: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    expected_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    counted_cash: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    cash_variance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    digital_in: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    digital_out: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    expected_digital: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    counted_digital: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    digital_variance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    sales_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    collected_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    khata_new: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    expense_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    bill_count: Mapped[int] = mapped_column(Integer, default=0)

    note: Mapped[str | None] = mapped_column(String(255))
    breakdown: Mapped[str | None] = mapped_column(Text)
