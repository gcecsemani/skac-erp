"""Seed the Owner login only. Branches, products, stock and other masters
are added from the UI.

Run: python -m app.seed
Idempotent: skips if the owner user already exists.
"""
from __future__ import annotations

from sqlalchemy import select, update

from app.core import rbac
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import Organization, Role, User  # noqa: F401  (metadata)

OWNER_EMAIL = "owner@skac.in"
OWNER_PASSWORD = "owner123"
OWNER_NAME = "Owner"


def ensure_roles(db) -> dict:
    """Keep only owner + cashier. Remap leftover roles on existing databases."""
    existing = {r.key: r for r in db.scalars(select(Role)).all()}
    roles: dict = {}
    for spec in rbac.DEFAULT_ROLES:
        role = existing.get(spec["key"])
        if role is None:
            role = Role(key=spec["key"], name=spec["name"], description=spec["description"])
            db.add(role)
            db.flush()
        else:
            role.name = spec["name"]
            role.description = spec["description"]
        roles[spec["key"]] = role
    db.flush()
    owner = roles[rbac.ROLE_OWNER]
    cashier = roles[rbac.ROLE_CASHIER]
    extras = [r for r in db.scalars(select(Role)).all() if r.key not in rbac.ALLOWED_ROLE_KEYS]
    owner_like = {"admin"}
    for extra in extras:
        new_id = owner.id if extra.key in owner_like else cashier.id
        db.execute(update(User).where(User.role_id == extra.id).values(role_id=new_id))
    db.flush()
    for extra in extras:
        db.delete(extra)
    db.flush()
    return roles


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        roles = ensure_roles(db)
        org = db.scalar(select(Organization))
        if org is None:
            org = Organization(name="Sri Kumaran Agri Clinic", legal_name="SKAC")
            db.add(org)
            db.flush()

        owner = db.scalar(select(User).where(User.email == OWNER_EMAIL))
        if owner is not None:
            db.commit()
            print("Owner already exists — skipping seed.")
            print(f"  Login: {OWNER_EMAIL} / {OWNER_PASSWORD}")
            return

        db.add(User(
            organization_id=org.id,
            role_id=roles[rbac.ROLE_OWNER].id,
            full_name=OWNER_NAME,
            email=OWNER_EMAIL,
            hashed_password=hash_password(OWNER_PASSWORD),
        ))
        db.commit()
        print("Seed complete (owner only).")
        print(f"  Login: {OWNER_EMAIL} / {OWNER_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
