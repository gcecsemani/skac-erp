"""Inter-branch stock transfer with an approval workflow."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import TransferStatus
from app.models.mixins import PKMixin, TimestampMixin


class StockTransfer(Base, PKMixin, TimestampMixin):
    __tablename__ = "stock_transfer"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    from_branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    to_branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    requested_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    transfer_no: Mapped[str | None] = mapped_column(String(40))
    transfer_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TransferStatus] = mapped_column(
        SAEnum(TransferStatus), default=TransferStatus.requested, index=True
    )
    notes: Mapped[str | None] = mapped_column(String(255))

    items: Mapped[list["StockTransferItem"]] = relationship(
        back_populates="transfer", cascade="all, delete-orphan"
    )


class StockTransferItem(Base, PKMixin, TimestampMixin):
    __tablename__ = "stock_transfer_item"

    transfer_id: Mapped[int] = mapped_column(
        ForeignKey("stock_transfer.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batch.id"))
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)

    transfer: Mapped["StockTransfer"] = relationship(back_populates="items")
