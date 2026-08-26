"""Org-level picklists: districts, villages, units, GST, HSN, expenses, payments."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import PKMixin, SoftDeleteMixin, TimestampMixin

KIND_DISTRICT = "district"
KIND_VILLAGE = "village"
KIND_UNIT = "unit"
KIND_GST = "gst_rate"
KIND_HSN = "hsn"
KIND_EXPENSE = "expense_category"
KIND_TOXICITY = "toxicity_class"
KIND_PAYMENT = "payment_mode"
KIND_STATE = "state"

ALL_KINDS = (
    KIND_DISTRICT, KIND_VILLAGE, KIND_UNIT, KIND_GST, KIND_HSN,
    KIND_EXPENSE, KIND_TOXICITY, KIND_PAYMENT, KIND_STATE,
)


class ConfigItem(Base, PKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "config_item"
    __table_args__ = (
        Index("ix_config_org_kind", "organization_id", "kind"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("config_item.id"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
