"""Organization (tenant) and Branch masters."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, SoftDeleteMixin, TimestampMixin


class Organization(Base, PKMixin, TimestampMixin, SoftDeleteMixin):
    """The top-level tenant (the business). One today; FK exists everywhere."""

    __tablename__ = "organization"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(200))
    pan: Mapped[str | None] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(200))
    contact_phone: Mapped[str | None] = mapped_column(String(20))

    branches: Mapped[list["Branch"]] = relationship(back_populates="organization")


class Branch(Base, PKMixin, TimestampMixin, SoftDeleteMixin):
    """A physical selling location. Carries GST + agri-input license data."""

    __tablename__ = "branch"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. BR01
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Address
    address_line1: Mapped[str | None] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    state_code: Mapped[str | None] = mapped_column(String(4))  # GST state code
    pincode: Mapped[str | None] = mapped_column(String(10))
    phone: Mapped[str | None] = mapped_column(String(20))

    # GST
    gstin: Mapped[str | None] = mapped_column(String(20))

    # Agri-input licenses (regulatory — printed on invoices)
    fco_license_no: Mapped[str | None] = mapped_column(String(60))
    fco_license_valid_to: Mapped[date | None] = mapped_column(Date)
    pesticide_license_no: Mapped[str | None] = mapped_column(String(60))
    pesticide_license_valid_to: Mapped[date | None] = mapped_column(Date)
    seed_license_no: Mapped[str | None] = mapped_column(String(60))
    seed_license_valid_to: Mapped[date | None] = mapped_column(Date)

    # Receipt / thermal printer preference for this counter (OS print dialog).
    printer_name: Mapped[str | None] = mapped_column(String(120))
    printer_type: Mapped[str] = mapped_column(String(20), default="thermal")  # thermal | a4
    thermal_paper_mm: Mapped[int] = mapped_column(Integer, default=80)  # 58 or 80

    organization: Mapped["Organization"] = relationship(back_populates="branches")
