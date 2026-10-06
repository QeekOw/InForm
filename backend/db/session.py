"""SQLAlchemy engine and session wiring for Accounts & History (issues #41-#44).

DATABASE_URL is read from the environment (see backend/.env.example). No default
value is assumed here — a missing DATABASE_URL fails loudly at import time rather
than silently falling back to sqlite, since the project's testing decisions
(issue #29) require exercising a real Postgres, not a substitute.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Loads backend/.env explicitly (by path, not cwd-relative search) so this
# module behaves the same whether imported from `uvicorn` (cwd=backend/),
# `alembic` (cwd=backend/), or pytest (cwd=repo root). A no-op if the file
# doesn't exist, e.g. in deployment where real env vars are set directly.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def normalize_database_url(url: str) -> str:
    """Force the psycopg3 dialect (`postgresql+psycopg://`) regardless of how the
    URL was written. Neon and most providers hand out a bare `postgresql://`
    connection string, which SQLAlchemy would otherwise resolve to the psycopg2
    dialect (not installed here — psycopg[binary] is psycopg3)."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy backend/.env.example to backend/.env "
            "and fill in a Postgres connection string (see the accounts-and-history "
            "spec's Task 1 for a free Neon setup walkthrough)."
        )
    return normalize_database_url(url)


# pool_pre_ping guards against Neon's serverless connections going stale between
# requests on a free tier; created lazily via a module-level singleton so importing
# this module doesn't require DATABASE_URL until it's actually used.
_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_database_url(), pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


def get_db():
    """FastAPI dependency yielding a Session, closed after the request."""
    db: Session = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
