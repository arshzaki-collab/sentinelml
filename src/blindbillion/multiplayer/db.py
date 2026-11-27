"""Database connection, session management, and lifecycle initialization."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from blindbillion.multiplayer.db_models import Base

DEFAULT_SQLITE_PATH = Path("data/multiplayer.db")


def normalize_database_url(url: str) -> str:
    """Normalize database URL for SQLAlchemy 2.0 with psycopg v3 driver support.

    Converts:
    - postgres://... -> postgresql+psycopg://...
    - postgresql://... -> postgresql+psycopg://... (if no driver specified)
    """
    trimmed = url.strip()
    if trimmed.startswith("postgres://"):
        return "postgresql+psycopg://" + trimmed[len("postgres://") :]
    if trimmed.startswith("postgresql://") and not trimmed.startswith("postgresql+"):
        return "postgresql+psycopg://" + trimmed[len("postgresql://") :]
    return trimmed


def get_database_url() -> str:
    """Retrieve configured database connection URL, defaulting to local SQLite."""
    env_url = os.environ.get("DATABASE_URL")
    if env_url and env_url.strip():
        return normalize_database_url(env_url)

    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_SQLITE_PATH}"


def create_db_engine(db_url: str | None = None) -> Engine:
    """Create SQLAlchemy engine configured for concurrency and connection safety."""
    url = normalize_database_url(db_url) if db_url else get_database_url()
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    # PostgreSQL / Supabase
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
    )


def init_db(engine: Engine) -> None:
    """Create all required tables if they do not already exist."""
    Base.metadata.create_all(engine)


# Global engine and sessionmaker instances for production runtime
_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Get or lazily initialize the singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = create_db_engine()
        init_db(_engine)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get or lazily initialize the sessionmaker."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a managed database session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
