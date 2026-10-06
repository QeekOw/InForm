import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from backend import google_oauth
from backend import main
from backend.db.models import Account
from backend.db.session import get_db
from backend.main import app


class _MemoryQuery:
    def __init__(self, accounts: list[Account]):
        self.accounts = accounts
        self.filters: dict[str, object] = {}

    def filter_by(self, **filters):
        self.filters = filters
        return self

    def _matches(self) -> list[Account]:
        return [
            account
            for account in self.accounts
            if all(getattr(account, key) == value for key, value in self.filters.items())
        ]

    def one_or_none(self):
        matches = self._matches()
        assert len(matches) <= 1
        return matches[0] if matches else None

    def one(self):
        matches = self._matches()
        assert len(matches) == 1
        return matches[0]

    def count(self) -> int:
        return len(self._matches())


class _MemoryDB:
    def __init__(self):
        self.accounts: list[Account] = []

    def query(self, model):
        assert model is Account
        return _MemoryQuery(self.accounts)

    def add(self, account: Account):
        account.id = account.id or uuid.uuid4()
        account.created_at = account.created_at or datetime.now(timezone.utc)
        self.accounts.append(account)

    def get(self, model, account_id):
        assert model is Account
        return next((account for account in self.accounts if account.id == account_id), None)

    def commit(self):
        pass

    def rollback(self):
        pass


@pytest.fixture
def db():
    return _MemoryDB()


@pytest.fixture
def client(db: _MemoryDB, monkeypatch):
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(main, "_COOKIES_OVER_HTTP", True)
    monkeypatch.setenv("SESSION_SECRET", "test-google-oauth-session-secret")
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    try:
        yield TestClient(app, base_url="https://testserver", follow_redirects=False)
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def google_config(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI", "https://api.example.test/auth/google/callback"
    )


def _start_google_sign_in(client: TestClient, redirect: str | None = None) -> str:
    response = client.get(
        "/auth/google/start",
        params={"redirect": redirect} if redirect else None,
    )
    assert response.status_code == 302
    return parse_qs(urlsplit(response.headers["location"]).query)["state"][0]


def _finish_google_sign_in(
    client: TestClient,
    state: str,
    code: str = "test-code",
):
    return client.get(
        "/auth/google/callback",
        params={"code": code, "state": state},
    )


def _install_verified_claims(monkeypatch, **overrides):
    claims = {
        "sub": "google-subject-1",
        "email": "person@example.com",
        "email_verified": True,
        "name": "Test Person",
    }
    claims.update(overrides)
    monkeypatch.setattr(
        main,
        "exchange_authorization_code",
        lambda code, settings: "test-id-token",
    )
    monkeypatch.setattr(
        main,
        "verify_identity_token",
        lambda identity_token, client_id: claims,
    )
    return claims


def test_unconfigured_google_sign_in_returns_plain_unavailable_status(
    client: TestClient, monkeypatch
):
    for key in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"):
        monkeypatch.delenv(key, raising=False)

    response = client.get("/auth/google/start")

    assert response.status_code == 302
    assert "google=unavailable" in response.headers["location"]


def test_google_start_sets_state_cookie_and_uses_requested_redirect(
    client: TestClient, google_config
):
    response = client.get("/auth/google/start", params={"redirect": "/history"})

    assert response.status_code == 302
    location = urlsplit(response.headers["location"])
    params = parse_qs(location.query)
    assert location.netloc == "accounts.google.com"
    assert params["client_id"] == ["test-client-id"]
    assert params["redirect_uri"] == ["https://api.example.test/auth/google/callback"]
    assert params["scope"] == ["openid email profile"]
    assert client.cookies.get(main._GOOGLE_STATE_COOKIE) == params["state"][0]
    assert client.cookies.get(main._GOOGLE_REDIRECT_COOKIE).strip('"') == "/history"


@pytest.mark.parametrize("redirect", ["https://evil.example", "//evil.example", "/\\evil.example"])
def test_google_start_rejects_external_redirect(client: TestClient, google_config, redirect: str):
    response = client.get("/auth/google/start", params={"redirect": redirect})
    assert response.status_code == 400


def test_id_token_verification_is_bound_to_the_google_client_id(monkeypatch):
    captured = {}

    def verify(token, request, audience):
        captured.update(token=token, request=request, audience=audience)
        return {"sub": "verified-subject"}

    monkeypatch.setattr(google_oauth.id_token, "verify_oauth2_token", verify)

    claims = google_oauth.verify_identity_token("signed-id-token", "expected-client-id")

    assert claims == {"sub": "verified-subject"}
    assert captured["token"] == "signed-id-token"
    assert captured["audience"] == "expected-client-id"
    assert isinstance(captured["request"], google_oauth.GoogleRequest)


def test_invalid_id_token_is_rejected(monkeypatch):
    def reject(token, request, audience):
        raise ValueError("invalid signature")

    monkeypatch.setattr(google_oauth.id_token, "verify_oauth2_token", reject)

    with pytest.raises(google_oauth.GoogleOAuthError):
        google_oauth.verify_identity_token("invalid-id-token", "expected-client-id")


@pytest.mark.parametrize("state", [None, "wrong-state"])
def test_google_callback_rejects_missing_or_mismatched_state(
    client: TestClient, google_config, state: str | None
):
    _start_google_sign_in(client)
    params = {"code": "test-code"}
    if state:
        params["state"] = state
    response = client.get("/auth/google/callback", params=params)
    assert response.status_code == 302
    assert "google=error" in response.headers["location"]
    assert client.cookies.get("inform_session") is None


def test_google_sign_in_creates_google_only_account_and_reuses_stable_subject(
    client: TestClient, db: _MemoryDB, google_config, monkeypatch
):
    _install_verified_claims(monkeypatch)
    state = _start_google_sign_in(client, "/history")

    first = _finish_google_sign_in(client, state)

    assert first.status_code == 302
    assert "google=success" in first.headers["location"]
    assert parse_qs(urlsplit(first.headers["location"]).query)["redirect"] == ["/history"]
    assert client.cookies.get("inform_session")
    account = db.query(Account).filter_by(google_sub="google-subject-1").one()
    account_id = account.id
    assert account.password_hash is None
    assert account.email == "person@example.com"
    assert account.name == "Test Person"
    assert client.get("/auth/me").json()["id"] == str(account_id)

    state = _start_google_sign_in(client)
    second = _finish_google_sign_in(client, state)

    assert second.status_code == 302
    assert db.query(Account).filter_by(google_sub="google-subject-1").count() == 1
    assert db.query(Account).filter_by(google_sub="google-subject-1").one().id == account_id


def test_google_email_change_keeps_the_account_matched_by_subject(
    client: TestClient, db: _MemoryDB, google_config, monkeypatch
):
    claims = _install_verified_claims(monkeypatch)
    state = _start_google_sign_in(client)
    _finish_google_sign_in(client, state)
    account_id = db.query(Account).filter_by(google_sub="google-subject-1").one().id
    claims["email"] = "new-address@example.com"

    state = _start_google_sign_in(client)
    response = _finish_google_sign_in(client, state)

    account = db.query(Account).filter_by(google_sub="google-subject-1").one()
    assert response.status_code == 302
    assert account.id == account_id
    assert account.email == "new-address@example.com"
    assert db.query(Account).count() == 1


def test_verified_google_email_links_existing_password_account(
    client: TestClient, db: _MemoryDB, google_config, monkeypatch
):
    account = Account(
        id=uuid.uuid4(),
        email="person@example.com",
        password_hash="existing-password-hash",
    )
    db.add(account)
    account = db.query(Account).filter_by(email="person@example.com").one()
    account_id = account.id
    _install_verified_claims(monkeypatch)

    state = _start_google_sign_in(client)
    response = _finish_google_sign_in(client, state)

    assert response.status_code == 302
    account = db.query(Account).filter_by(id=account_id).one()
    assert account.google_sub == "google-subject-1"
    assert account.password_hash == "existing-password-hash"
    assert db.query(Account).count() == 1


def test_unverified_google_email_is_not_linked_or_created(
    client: TestClient, db: _MemoryDB, google_config, monkeypatch
):
    db.add(
        Account(
            id=uuid.uuid4(),
            email="person@example.com",
            password_hash="existing-password-hash",
        )
    )
    _install_verified_claims(monkeypatch, email_verified=False)

    state = _start_google_sign_in(client)
    response = _finish_google_sign_in(client, state)

    assert response.status_code == 302
    assert "google=error" in response.headers["location"]
    assert db.query(Account).filter_by(google_sub="google-subject-1").count() == 0
    assert db.query(Account).filter_by(email="person@example.com").one().google_sub is None


def test_google_only_account_cannot_use_password_login(
    client: TestClient, db: _MemoryDB, google_config, monkeypatch
):
    _install_verified_claims(monkeypatch)
    state = _start_google_sign_in(client)
    _finish_google_sign_in(client, state)
    client.cookies.clear()

    response = client.post(
        "/auth/login",
        json={"email": "person@example.com", "password": "password123"},
    )

    assert response.status_code == 401
