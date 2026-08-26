"""Double-entry accounting: chart of accounts, journal entries and lines."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AccountType
from app.models.mixins import PKMixin, TimestampMixin


class LedgerAccount(Base, PKMixin, TimestampMixin):
    """A chart-of-accounts entry (e.g. Sales, Cash, GST Payable, Debtors)."""

    __tablename__ = "ledger_account"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_account_org_code"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[AccountType] = mapped_column(SAEnum(AccountType), nullable=False)
    is_system: Mapped[bool] = mapped_column(default=False)


class JournalEntry(Base, PKMixin, TimestampMixin):
    """A balanced journal entry auto-posted from a source transaction."""

    __tablename__ = "journal_entry"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branch.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    narration: Mapped[str | None] = mapped_column(String(255))
    ref_type: Mapped[str | None] = mapped_column(String(40), index=True)
    ref_id: Mapped[int | None] = mapped_column(index=True)

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan"
    )


class JournalLine(Base, PKMixin, TimestampMixin):
    __tablename__ = "journal_line"

    entry_id: Mapped[int] = mapped_column(
        ForeignKey("journal_entry.id"), nullable=False, index=True
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("ledger_account.id"), nullable=False, index=True
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
    account: Mapped["LedgerAccount"] = relationship()
