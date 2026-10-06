"""Password hashing and session-token utilities for Accounts & History (issue #41).

Self-rolled, smallest-credible-thing per issue #41: bcrypt for password hashing
(via the `bcrypt` package directly, not passlib — passlib's bcrypt backend has
had version-compatibility friction with modern bcrypt releases), JWTs for
session tokens with a 30-day expiry so a signed-in person stays signed in on
their next visit.

No HTTP here — this module is pure functions plus the FastAPI dependency that
reads the session cookie. Endpoints are wired in main.py (Tasks 3-4).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

# See the matching comment in main.py: this module is imported both as
# top-level `auth` (uvicorn, cwd=backend/) and as `backend.auth` (pytest, cwd
# = repo root). Using whichever import form matches keeps db.models/db.session
# resolving to the *same* module object as everywhere else in backend/ —
# important here specifically because FastAPI's dependency-override lookup in
# tests matches get_db by identity.
try:
    from .db.models import Account
    from .db.session import get_db
except ImportError:
    from db.models import Account
    from db.session import get_db

# A signed-in person stays signed in on their next visit (issue #41, AC4) for
# up to this long; matches the session cookie's Max-Age (wired in Task 5).
SESSION_TOKEN_TTL_DAYS = 30

JWT_ALGORITHM = "HS256"

# Name shared by every endpoint that sets or reads the session cookie.
SESSION_COOKIE_NAME = "inform_session"


def _session_secret() -> str:
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        raise RuntimeError(
            "SESSION_SECRET is not set. Copy backend/.env.example to backend/.env "
            "and set a random value (see the comment there for how to generate one)."
        )
    return secret


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt. Never store the plain value."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # A malformed/corrupt hash should never be treated as a match.
        return False


def create_session_token(account_id: uuid.UUID) -> str:
    """Create a signed JWT session token for account_id, expiring in
    SESSION_TOKEN_TTL_DAYS days."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(account_id),
        "iat": now,
        "exp": now + timedelta(days=SESSION_TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, _session_secret(), algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> uuid.UUID | None:
    """Decode a session token to its account id, or None if the token is
    missing, malformed, tampered with, or expired.

    Returns None rather than raising so callers (the get_current_account
    dependency) can turn any failure into a clean 401 without a chain of
    except clauses for each jwt.* exception type.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, _session_secret(), algorithms=[JWT_ALGORITHM])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def get_current_account(request: Request, db: Session = Depends(get_db)) -> Account:
    """FastAPI dependency resolving the signed-in Account from the Authorization
    header or session cookie. Raises 401 if the token is missing, invalid or
    expired, or the account no longer exists (e.g. it was deleted, issue #44)."""
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer ") :].strip()
    if not token:
        token = request.cookies.get(SESSION_COOKIE_NAME)

    account_id = decode_session_token(token) if token else None
    if account_id is None:
        raise HTTPException(status_code=401, detail="Not signed in.")

    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=401, detail="Not signed in.")
    return account
