"""Task 2 (accounts-and-history spec): password hashing and session-token
round-trip utilities. Pure unit tests, no HTTP and no database — those land
in Tasks 3-4.
"""

from datetime import datetime, timedelta, timezone
import uuid

import jwt
import pytest

from backend.auth import (
    JWT_ALGORITHM,
    SESSION_TOKEN_TTL_DAYS,
    create_session_token,
    decode_session_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_plain_text():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$2b$")  # bcrypt hash prefix


def test_verify_password_round_trip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_verify_password_rejects_malformed_hash():
    assert verify_password("anything", "not-a-real-bcrypt-hash") is False


def test_hash_password_uses_a_fresh_salt_each_time():
    # Two hashes of the same password must differ (salted), yet both verify.
    first = hash_password("same password")
    second = hash_password("same password")
    assert first != second
    assert verify_password("same password", first)
    assert verify_password("same password", second)


def test_create_and_decode_session_token_round_trip():
    account_id = uuid.uuid4()
    token = create_session_token(account_id)
    assert decode_session_token(token) == account_id


def test_decode_session_token_rejects_tampered_token():
    account_id = uuid.uuid4()
    token = create_session_token(account_id)
    # Flip a character in the payload segment (not the last char of the
    # signature): some trailing base64url characters only encode a couple of
    # bits, so flipping just the last char can decode to the same byte and
    # produce an identical (still-valid) signature — a flaky false negative.
    header, payload, signature = token.split(".")
    tampered_char = "a" if payload[0] != "a" else "b"
    tampered_payload = tampered_char + payload[1:]
    tampered = f"{header}.{tampered_payload}.{signature}"
    assert decode_session_token(tampered) is None


def test_decode_session_token_rejects_expired_token(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret-for-expiry-case")
    account_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(account_id),
        "iat": now - timedelta(days=SESSION_TOKEN_TTL_DAYS + 1),
        "exp": now - timedelta(days=1),
    }
    expired_token = jwt.encode(expired_payload, "test-secret-for-expiry-case", algorithm=JWT_ALGORITHM)
    assert decode_session_token(expired_token) is None


def test_decode_session_token_rejects_empty_or_none():
    assert decode_session_token("") is None


def test_decode_session_token_rejects_garbage_string():
    assert decode_session_token("not.a.jwt") is None
