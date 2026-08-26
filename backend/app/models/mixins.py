"""Reusable SQLAlchemy column mixins."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

# BIGINT on MySQL/Postgres; INTEGER on SQLite (SQLite only autoincrements
# INTEGER PRIMARY KEY). Keeps the schema portable for local dev + tests.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class PKMixin:
    """Integer surrogate primary key."""

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)


class TimestampMixin:
    """Created/updated audit timestamps (used for delta sync watermarks too)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """Soft delete so finalized/audited records are never physically removed."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OrgScopedMixin:
    """Every tenant-owned row carries the organization id."""

    organization_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("organization.id"), nullable=False, index=True
    )


class BranchScopedMixin(OrgScopedMixin):
    """Transactional rows are additionally scoped to a branch."""

    branch_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("branch.id"), nullable=False, index=True
    )
