"""Database engine, session factory, and declarative base."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_url = settings.sqlalchemy_database_url
_kwargs: dict = {"pool_pre_ping": True, "future": True}
if _url.startswith("sqlite"):
    # FastAPI uses the engine from multiple threads.
    _kwargs["connect_args"] = {"check_same_thread": False}
else:
    _kwargs["pool_recycle"] = 1800

engine = create_engine(_url, **_kwargs)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, future=True
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator:
    """FastAPI dependency that yields a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
