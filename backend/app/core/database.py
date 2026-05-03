"""SQLAlchemy engine and session factory (sync).

Uses SQLAlchemy 2.0 with the `postgresql+psycopg` driver. The shared `engine`
and `SessionLocal` back:

- **FastAPI:** `get_db()` yields one session per request (dependency injection).
- **Workers / scripts:** open `SessionLocal()` directly or use a context manager
  and close when done.

Keep sessions short-lived; pool sizing comes from `Settings.DB_*`.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
