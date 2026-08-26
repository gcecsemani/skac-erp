"""Sales returns as immutable credit notes (invoices are never edited)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, TimestampMixin


class CreditNote(Base, PKMixin, TimestampMixin):
    __tablename__ = "credit_note"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"), nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customer.id"))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    note_no: Mapped[str | None] = mapped_column(String(40))
    note_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    items: Mapped[list["CreditNoteItem"]] = relationship(
        back_populates="credit_note", cascade="all, delete-orphan"
    )


class CreditNoteItem(Base, PKMixin, TimestampMixin):
    __tablename__ = "credit_note_item"

    credit_note_id: Mapped[int] = mapped_column(
        ForeignKey("credit_note.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batch.id"))
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    credit_note: Mapped["CreditNote"] = relationship(back_populates="items")
