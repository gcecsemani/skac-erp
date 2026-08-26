"""Operating expenses (transport, salary, rent, etc.) posted to the ledger."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import PKMixin, TimestampMixin


class Expense(Base, PKMixin, TimestampMixin):
    __tablename__ = "expense"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    payee: Mapped[str | None] = mapped_column(String(150))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="cash")
    note: Mapped[str | None] = mapped_column(String(255))
