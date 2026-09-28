"""Database engine and session factory (SQLite local by default)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import get_engine

engine: Engine = get_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_session(url: Optional[str] = None) -> Session:
    """Session on the default engine, or on a one-off engine for a custom URL
    (used by tests and temporary databases)."""
    if url is None:
        return SessionLocal()
    return sessionmaker(
        bind=get_engine(url),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )()
