"""Field visits: staff crop-complaint visits with GPS and photos."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import FieldVisitStatus
from app.models.mixins import PKMixin, TimestampMixin


class FieldVisit(Base, PKMixin, TimestampMixin):
    __tablename__ = "field_visit"
    __table_args__ = (
        Index("ix_field_visit_org_date", "organization_id", "visit_date"),
    )

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), nullable=False, index=True)
    visited_by_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customer.id"), index=True)

    visit_no: Mapped[str | None] = mapped_column(String(40))
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    farmer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    farmer_phone: Mapped[str | None] = mapped_column(String(20))
    village: Mapped[str | None] = mapped_column(String(120))

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    gps_accuracy: Mapped[float | None] = mapped_column(Float)  # metres
    gps_captured_at: Mapped[datetime | None] = mapped_column(DateTime)

    complaint_notes: Mapped[str | None] = mapped_column(Text)
    prescription_notes: Mapped[str | None] = mapped_column(Text)

    status: Mapped[FieldVisitStatus] = mapped_column(
        SAEnum(FieldVisitStatus), default=FieldVisitStatus.open, index=True
    )
    resolution_note: Mapped[str | None] = mapped_column(String(255))
    resolved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    photos: Mapped[list["FieldVisitPhoto"]] = relationship(
        back_populates="visit", cascade="all, delete-orphan"
    )


class FieldVisitPhoto(Base, PKMixin, TimestampMixin):
    __tablename__ = "field_visit_photo"

    visit_id: Mapped[int] = mapped_column(
        ForeignKey("field_visit.id"), nullable=False, index=True
    )
    stored_name: Mapped[str] = mapped_column(String(200), nullable=False)
    original_name: Mapped[str | None] = mapped_column(String(200))
    content_type: Mapped[str | None] = mapped_column(String(80))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)

    visit: Mapped["FieldVisit"] = relationship(back_populates="photos")
