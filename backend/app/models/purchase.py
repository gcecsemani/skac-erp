"""Purchase cycle: Purchase Order -> GRN -> Vendor Payment."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PurchaseOrderStatus
from app.models.mixins import PKMixin, TimestampMixin


class PurchaseOrder(Base, PKMixin, TimestampMixin):
    __tablename__ = "purchase_order"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    po_no: Mapped[str | None] = mapped_column(String(40))
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        SAEnum(PurchaseOrderStatus), default=PurchaseOrderStatus.draft, index=True
    )
    expected_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(String(255))

    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class PurchaseOrderItem(Base, PKMixin, TimestampMixin):
    __tablename__ = "purchase_order_item"

    order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_order.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    order: Mapped["PurchaseOrder"] = relationship(back_populates="items")


class GRN(Base, PKMixin, TimestampMixin):
    """Goods Receipt Note against a PO; captures batch/expiry at receipt."""

    __tablename__ = "grn"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False)
    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_order.id"))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    grn_no: Mapped[str | None] = mapped_column(String(40))
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    vendor_invoice_no: Mapped[str | None] = mapped_column(String(60))
    total_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    items: Mapped[list["GRNItem"]] = relationship(
        back_populates="grn", cascade="all, delete-orphan"
    )


class GRNItem(Base, PKMixin, TimestampMixin):
    __tablename__ = "grn_item"

    grn_id: Mapped[int] = mapped_column(ForeignKey("grn.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batch.id"))
    batch_no: Mapped[str] = mapped_column(String(80), nullable=False)
    mfg_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    grn: Mapped["GRN"] = relationship(back_populates="items")


class VendorPayment(Base, PKMixin, TimestampMixin):
    __tablename__ = "vendor_payment"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branch.id"))
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False, index=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="cash")
    note: Mapped[str | None] = mapped_column(String(255))
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reversed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    reversal_reason: Mapped[str | None] = mapped_column(String(255))


class PurchaseReturn(Base, PKMixin, TimestampMixin):
    """Debit note: return goods to a vendor against a GRN (immutable)."""

    __tablename__ = "purchase_return"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False, index=True)
    grn_id: Mapped[int] = mapped_column(ForeignKey("grn.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))

    note_no: Mapped[str | None] = mapped_column(String(40))
    note_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    items: Mapped[list["PurchaseReturnItem"]] = relationship(
        back_populates="purchase_return", cascade="all, delete-orphan"
    )


class PurchaseReturnItem(Base, PKMixin, TimestampMixin):
    __tablename__ = "purchase_return_item"

    purchase_return_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_return.id"), nullable=False, index=True
    )
    grn_item_id: Mapped[int] = mapped_column(ForeignKey("grn_item.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batch.id"))
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    batch_no: Mapped[str | None] = mapped_column(String(80))
    hsn_code: Mapped[str | None] = mapped_column(String(12))
    packing: Mapped[str | None] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))

    purchase_return: Mapped["PurchaseReturn"] = relationship(back_populates="items")
