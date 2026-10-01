"""Task 12 (accounts-and-history spec): DELETE /account permanently removes
the signed-in person's Account and every Scan belonging to it (issue #44),
with no soft delete or retained copy anywhere (ADR-0011).
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.models import Account, Scan
from backend.db.session import get_db
from backend.main import app, get_llm_client

PROFILE = {
    "age": 30,
    "biological_sex": "female",
    "activity_multiplier": 1.55,
    "fitness_goal": "fat_loss",
}


def _llm_raising() -> MagicMock:
    llm = MagicMock()
    llm.beta.chat.completions.parse.side_effect = RuntimeError("LLM unavailable")
    return llm


@pytest.fixture
def client(db: Session):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_llm_client] = lambda: _llm_raising()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_llm_client, None)


def test_delete_account_requires_sign_in(client: TestClient):
    resp = client.delete("/account")
    assert resp.status_code == 401


def test_delete_account_removes_account_and_scans(client: TestClient, db: Session):
    client.post("/auth/signup", json={"email": "leaving@example.com", "password": "password123"})
    client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_570_clean"})

    account_id = db.query(Account).filter_by(email="leaving@example.com").one().id
    assert db.query(Scan).filter_by(account_id=account_id).count() == 2

    resp = client.delete("/account")
    assert resp.status_code == 204

    # Nothing retained: no soft-delete flag, no orphaned/retained copy
    # anywhere — the row itself is gone, not marked deleted (ADR-0011).
    assert db.query(Account).filter_by(id=account_id).one_or_none() is None
    assert db.query(Scan).filter_by(account_id=account_id).count() == 0


def test_after_deletion_the_old_session_cannot_authenticate(client: TestClient):
    client.post("/auth/signup", json={"email": "leaving2@example.com", "password": "password123"})
    delete_resp = client.delete("/account")
    assert delete_resp.status_code == 204

    # The TestClient still holds whatever cookie it had (deletion clears it
    # server-side via Set-Cookie, but assert the *authentication* result
    # regardless of whether the client-side cookie jar honored the clear).
    me_resp = client.get("/auth/me")
    assert me_resp.status_code == 401

    scans_resp = client.get("/scans")
    assert scans_resp.status_code == 401


def test_deleting_one_account_does_not_affect_another(client: TestClient, db: Session):
    client.post("/auth/signup", json={"email": "leaving3@example.com", "password": "password123"})
    client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    client.post("/auth/logout")

    client.post("/auth/signup", json={"email": "staying@example.com", "password": "password123"})
    staying_scan = client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    assert staying_scan.status_code == 201
    client.post("/auth/logout")

    client.post("/auth/login", json={"email": "leaving3@example.com", "password": "password123"})
    delete_resp = client.delete("/account")
    assert delete_resp.status_code == 204

    # The other account's Scan and ability to sign in are untouched.
    staying_account = db.query(Account).filter_by(email="staying@example.com").one_or_none()
    assert staying_account is not None
    assert db.query(Scan).filter_by(account_id=staying_account.id).count() == 1

    login_resp = client.post("/auth/login", json={"email": "staying@example.com", "password": "password123"})
    assert login_resp.status_code == 200
    scans_resp = client.get("/scans")
    assert scans_resp.status_code == 200
    assert len(scans_resp.json()) == 1
