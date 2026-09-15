"""Product master with category-specific attributes and unit conversions."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ProductCategory
from app.models.mixins import PKMixin, SoftDeleteMixin, TimestampMixin


class Product(Base, PKMixin, TimestampMixin, SoftDeleteMixin):
    """Org-level product master. Stock is tracked per branch/batch separately."""

    __tablename__ = "product"
    __table_args__ = (
        UniqueConstraint("organization_id", "sku", name="uq_product_org_sku"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )

    sku: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    barcode: Mapped[str | None] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[ProductCategory] = mapped_column(
        SAEnum(ProductCategory), nullable=False, index=True
    )
    brand: Mapped[str | None] = mapped_column(String(120))
    manufacturer: Mapped[str | None] = mapped_column(String(160))

    # GST / units
    hsn_code: Mapped[str | None] = mapped_column(String(12))
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))
    base_unit: Mapped[str] = mapped_column(String(20), default="unit")  # kg/bag/litre/packet

    # Pricing (per base unit)
    mrp: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sale_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    reorder_level: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --- Category-specific attributes ---
    # Fertilizer NPK composition
    npk_n: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    npk_p: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    npk_k: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    # Pesticide
    toxicity_class: Mapped[str | None] = mapped_column(String(40))  # e.g. Class II
    # Seed
    germination_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    seed_lot: Mapped[str | None] = mapped_column(String(60))

    # Free-form extensibility for future category attributes
    attributes: Mapped[dict | None] = mapped_column(JSON)

    units: Mapped[list["ProductUnit"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def packing(self) -> str | None:
        extra = self.attributes if isinstance(self.attributes, dict) else {}
        pack = str((extra or {}).get("packing") or "").strip()
        if pack and pack.upper() not in {"UNIT", "UNITS"}:
            return pack
        return None

    @property
    def sale_unit(self) -> str:
        from app.core.units import pack_info

        return pack_info(self).sale_unit

    @property
    def pack_size(self):
        from app.core.units import pack_info

        return pack_info(self).pack_size

    @property
    def loose_unit(self) -> str | None:
        from app.core.units import pack_info

        return pack_info(self).loose_unit

    @property
    def allows_loose(self) -> bool:
        from app.core.units import pack_info

        return pack_info(self).allows_loose


class ProductUnit(Base, PKMixin, TimestampMixin):
    """Alternate saleable units with conversion factor to the base unit.

    Example: base_unit='kg', unit='bag', factor_to_base=50  (1 bag = 50 kg).
    """

    __tablename__ = "product_unit"
    __table_args__ = (
        UniqueConstraint("product_id", "unit", name="uq_product_unit"),
    )

    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    factor_to_base: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="units")
