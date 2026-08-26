"""Users, roles, and branch-scope assignment (RBAC)."""
from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import PKMixin, SoftDeleteMixin, TimestampMixin

# Users may be scoped to one or many branches (Owner/Admin -> all branches).
user_branch = Table(
    "user_branch",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("branch_id", ForeignKey("branch.id"), primary_key=True),
)


class Role(Base, PKMixin, TimestampMixin):
    """A named role. Permission semantics live in app.core.rbac."""

    __tablename__ = "role"

    # Canonical keys: owner, cashier
    key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, PKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_user_org_email"),)

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organization.id"), nullable=False, index=True
    )
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), nullable=False)

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Two-factor (TOTP) — enforced for owner/admin in the auth flow.
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    role: Mapped["Role"] = relationship(back_populates="users")
    branches = relationship("Branch", secondary=user_branch, lazy="selectin")
