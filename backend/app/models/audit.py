"""Immutable audit log for every create/update/delete on business entities."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import PKMixin


class AuditLog(Base, PKMixin):
    __tablename__ = "audit_log"

    organization_id: Mapped[int | None] = mapped_column(index=True)
    branch_id: Mapped[int | None] = mapped_column(index=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), index=True)

    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create/update/delete
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(40), index=True)

    # Before/after snapshots for field-level change tracking.
    changes: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
