"""Figma redesign: Account display name, and changing email/password.

Through the HTTP API, like the rest of the auth tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.main import app

EMAIL = "person@example.com"
PASSWORD = "correct horse battery staple"


@pytest.fixture
def client(db: Session):
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _signup(client: TestClient, **extra):
    resp = client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- name -------------------------------------------------------------------


def test_signup_stores_and_returns_name(client: TestClient):
    body = _signup(client, name="  John   Doe ")
    assert body["name"] == "John Doe"
    assert client.get("/auth/me").json()["name"] == "John Doe"


def test_name_is_optional(client: TestClient):
    assert _signup(client)["name"] is None


def test_blank_name_is_stored_as_none(client: TestClient):
    assert _signup(client, name="   ")["name"] is None


def test_overlong_name_is_rejected(client: TestClient):
    resp = client.post(
        "/auth/signup", json={"email": EMAIL, "password": PASSWORD, "name": "x" * 81}
    )
    assert resp.status_code == 422


def test_profile_update_changes_name(client: TestClient):
    _signup(client, name="John")
    resp = client.patch("/auth/me", json={"name": "Jane"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Jane"


# --- credentials --------------------------------------------------------------


def test_change_password_then_login_with_new_one(client: TestClient):
    _signup(client)
    resp = client.patch(
        "/auth/credentials",
        json={"current_password": PASSWORD, "new_password": "a brand new password"},
    )
    assert resp.status_code == 200

    client.cookies.clear()
    assert client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 401
    assert (
        client.post(
            "/auth/login", json={"email": EMAIL, "password": "a brand new password"}
        ).status_code
        == 200
    )


def test_change_email_normalizes_and_allows_login(client: TestClient):
    _signup(client)
    resp = client.patch(
        "/auth/credentials",
        json={"current_password": PASSWORD, "new_email": "New@Example.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "new@example.com"

    client.cookies.clear()
    assert (
        client.post(
            "/auth/login", json={"email": "new@example.com", "password": PASSWORD}
        ).status_code
        == 200
    )


def test_wrong_current_password_is_rejected(client: TestClient):
    _signup(client)
    resp = client.patch(
        "/auth/credentials",
        json={"current_password": "not my password", "new_password": "whatever12345"},
    )
    assert resp.status_code == 403


def test_nothing_to_change_is_rejected(client: TestClient):
    _signup(client)
    resp = client.patch("/auth/credentials", json={"current_password": PASSWORD})
    assert resp.status_code == 422


def test_short_new_password_is_rejected(client: TestClient):
    _signup(client)
    resp = client.patch(
        "/auth/credentials", json={"current_password": PASSWORD, "new_password": "short"}
    )
    assert resp.status_code == 422


def test_credentials_require_sign_in(client: TestClient):
    resp = client.patch(
        "/auth/credentials", json={"current_password": PASSWORD, "new_password": "whatever12345"}
    )
    assert resp.status_code == 401


def test_change_email_to_taken_email_returns_409(client: TestClient):
    client.post("/auth/signup", json={"email": "other@example.com", "password": PASSWORD})
    client.cookies.clear()
    _signup(client)
    resp = client.patch(
        "/auth/credentials",
        json={"current_password": PASSWORD, "new_email": "other@example.com"},
    )
    assert resp.status_code == 409
