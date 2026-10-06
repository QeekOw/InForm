"""Tasks 3-4 (accounts-and-history spec): signup, login, logout, /auth/me.

Exercised through the HTTP API via TestClient, per issue #29's testing
decision — the seam under test is what a caller of the API can see, not the
ORM session directly. The `db` fixture (tests/conftest.py) overrides the
app's get_db dependency so every request in a test runs inside the same
rolled-back transaction.
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


def test_signup_succeeds_and_sets_cookie(client: TestClient):
    resp = client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == EMAIL
    assert "id" in body
    assert "password" not in body
    assert "password_hash" not in body
    assert client.cookies.get("inform_session") is not None


def test_signup_duplicate_email_returns_409(client: TestClient):
    first = client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert first.status_code == 201

    second = client.post("/auth/signup", json={"email": EMAIL, "password": "a different password"})
    assert second.status_code == 409


def test_signup_duplicate_email_is_case_insensitive(client: TestClient):
    client.post("/auth/signup", json={"email": "Person@Example.com", "password": PASSWORD})
    second = client.post("/auth/signup", json={"email": "person@example.com", "password": PASSWORD})
    assert second.status_code == 409


def test_signup_rejects_malformed_email(client: TestClient):
    resp = client.post("/auth/signup", json={"email": "not-an-email", "password": PASSWORD})
    assert resp.status_code == 422


def test_signup_rejects_short_password(client: TestClient):
    resp = client.post("/auth/signup", json={"email": EMAIL, "password": "short"})
    assert resp.status_code == 422


def test_login_succeeds_with_correct_credentials(client: TestClient):
    client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    client.cookies.clear()

    resp = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 200
    assert resp.json()["email"] == EMAIL
    assert client.cookies.get("inform_session") is not None


def test_login_wrong_password_returns_401(client: TestClient):
    client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    client.cookies.clear()

    resp = client.post("/auth/login", json={"email": EMAIL, "password": "wrong password"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401_with_same_message_as_wrong_password(client: TestClient):
    client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    client.cookies.clear()

    wrong_password_resp = client.post("/auth/login", json={"email": EMAIL, "password": "wrong password"})
    unknown_email_resp = client.post("/auth/login", json={"email": "nobody@example.com", "password": PASSWORD})

    assert wrong_password_resp.status_code == 401
    assert unknown_email_resp.status_code == 401
    assert wrong_password_resp.json()["detail"] == unknown_email_resp.json()["detail"]


def test_me_returns_account_when_signed_in(client: TestClient):
    client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD})

    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == EMAIL


def test_me_returns_401_when_not_signed_in(client: TestClient):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_full_signup_logout_login_me_cycle(client: TestClient):
    signup_resp = client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert signup_resp.status_code == 201

    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 200

    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200

    me_after_logout = client.get("/auth/me")
    assert me_after_logout.status_code == 401

    login_resp = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert login_resp.status_code == 200

    me_after_login = client.get("/auth/me")
    assert me_after_login.status_code == 200
    assert me_after_login.json()["email"] == EMAIL

# --- Sign-up collects profile details in one form (Requirement 3.1-3.2) -----
#
# These are pre-fill defaults only. A Scan's own frozen profile snapshot stays
# the source of truth for what produced its plan (issue #42).

PROFILE_DEFAULTS = {
    "date_of_birth": "1995-06-15",
    "height_cm": 178.5,
    "default_biological_sex": "female",
    "default_activity_multiplier": 1.55,
    "default_fitness_goal": "hypertrophy",
}


def test_signup_persists_and_returns_profile_defaults(client: TestClient):
    """One form, one request: details given at sign-up come straight back."""
    resp = client.post(
        "/auth/signup",
        json={"email": EMAIL, "password": PASSWORD, **PROFILE_DEFAULTS},
    )
    assert resp.status_code == 201
    body = resp.json()
    for key, value in PROFILE_DEFAULTS.items():
        assert body[key] == value, key

    # And they survive the round trip, so the next Scan can pre-fill from them
    # without asking again (Requirement 3.2).
    me = client.get("/auth/me")
    assert me.status_code == 200
    for key, value in PROFILE_DEFAULTS.items():
        assert me.json()[key] == value, key


def test_signup_without_profile_details_still_works(client: TestClient):
    """Every profile field is optional; email and password remain the only must-haves."""
    resp = client.post("/auth/signup", json={"email": EMAIL, "password": PASSWORD})
    assert resp.status_code == 201
    body = resp.json()
    assert body["date_of_birth"] is None
    assert body["height_cm"] is None
    assert body["default_biological_sex"] is None
    assert body["default_activity_multiplier"] is None
    assert body["default_fitness_goal"] is None


def test_signup_never_returns_credentials(client: TestClient):
    """Neither the hash nor the Google subject is ever in a response body."""
    resp = client.post(
        "/auth/signup",
        json={"email": EMAIL, "password": PASSWORD, **PROFILE_DEFAULTS},
    )
    assert resp.status_code == 201
    for body in (resp.json(), client.get("/auth/me").json()):
        assert "password" not in body
        assert "password_hash" not in body
        assert "google_sub" not in body
        assert PASSWORD not in str(body)


@pytest.mark.parametrize(
    "dob",
    [
        "2024-01-01",  # far too young
        "1850-01-01",  # implausibly old
    ],
)
def test_signup_rejects_an_implausible_date_of_birth(client: TestClient, dob: str):
    """Requirement 3.4: rejected before an account is created, not after."""
    resp = client.post(
        "/auth/signup", json={"email": EMAIL, "password": PASSWORD, "date_of_birth": dob}
    )
    assert resp.status_code == 422

    # No account was created by the rejected request.
    assert client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD}).status_code == 401


@pytest.mark.parametrize("height", [17.0, 1780.0, -5.0])
def test_signup_rejects_an_implausible_height(client: TestClient, height: float):
    resp = client.post(
        "/auth/signup", json={"email": EMAIL, "password": PASSWORD, "height_cm": height}
    )
    assert resp.status_code == 422


def test_signup_rejects_an_unlisted_activity_multiplier(client: TestClient):
    resp = client.post(
        "/auth/signup",
        json={"email": EMAIL, "password": PASSWORD, "default_activity_multiplier": 12.0},
    )
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [("default_biological_sex", "other"), ("default_fitness_goal", "get_ripped")],
)
def test_signup_rejects_unknown_enum_values(client: TestClient, field: str, value: str):
    resp = client.post(
        "/auth/signup", json={"email": EMAIL, "password": PASSWORD, field: value}
    )
    assert resp.status_code == 422


def test_height_is_stored_but_never_reaches_a_plan(client: TestClient):
    """Requirement 3.5: height is display-only.

    Nothing in the plan request accepts it, so there is no route by which a
    stored height could influence a calorie target.
    """
    from backend.main import PlanRequest
    from inform.user import UserProfile

    assert "height_cm" not in PlanRequest.model_fields
    assert "height_cm" not in UserProfile.model_fields

    resp = client.post(
        "/auth/signup", json={"email": EMAIL, "password": PASSWORD, **PROFILE_DEFAULTS}
    )
    assert resp.json()["height_cm"] == 178.5
