"""Task 7 (accounts-and-history spec): POST /scans saves a signed-in person's
read as an immutable Scan (issue #42), reusing the same Modules 2->3->4
computation /plan already exercises (tests/test_api_plan.py) rather than
re-testing that logic here.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.db.models import Scan
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


@pytest.fixture
def signed_in_client(client: TestClient):
    resp = client.post("/auth/signup", json={"email": "scanner@example.com", "password": "password123"})
    assert resp.status_code == 201
    return client


def test_save_scan_requires_sign_in(client: TestClient):
    resp = client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    assert resp.status_code == 401


def test_save_scan_persists_and_returns_full_detail(signed_in_client: TestClient, db: Session):
    resp = signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    assert resp.status_code == 201
    body = resp.json()

    assert body["sample_id"] == "synthetic_270_clean"
    assert body["profile"] == PROFILE
    assert body["corrected_fields"] == []
    assert body["nutrition"]["target_calories_kcal"] > 0
    assert body["narrative_text"]
    assert body["narrative_source"] == "fallback"  # LLM stubbed to raise

    # Read back directly to confirm what actually persisted (issue #29 allows
    # this for state-verification, not as the primary behavioral assertion).
    scan = db.query(Scan).filter_by(id=body["id"]).one()
    assert scan.effective_inbody["weight_kg"] == body["effective_inbody"]["weight_kg"]
    assert scan.narrative_text == body["narrative_text"]
    # No image field anywhere on what got persisted (ADR-0011).
    assert not any("image" in k or "photo" in k for k in scan.effective_inbody)
    assert not any("image" in k or "photo" in k for k in scan.measured)


def test_save_scan_with_corrections_records_corrected_fields(signed_in_client: TestClient):
    resp = signed_in_client.post(
        "/scans",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "corrections": {"lean_body_mass_kg": 62.5},
            "confirmations": ["weight_kg", "percent_body_fat", "basal_metabolic_rate_kcal"],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["corrected_fields"] == ["lean_body_mass_kg"]
    assert sorted(body["confirmed_fields"]) == ["basal_metabolic_rate_kcal", "percent_body_fat", "weight_kg"]


def test_save_scan_refuses_flagged_sample_without_resolution(signed_in_client: TestClient):
    resp = signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "real_270_flagged"})
    assert resp.status_code == 409


def test_scanning_again_appends_rather_than_replaces(signed_in_client: TestClient, db: Session):
    first = signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    second = signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_570_clean"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]

    remaining_first = db.query(Scan).filter_by(id=first.json()["id"]).one()
    assert remaining_first.sample_id == "synthetic_270_clean"


def test_scan_survives_a_later_profile_change_unchanged(signed_in_client: TestClient):
    older_profile = {**PROFILE, "fitness_goal": "fat_loss"}
    first = signed_in_client.post("/scans", json={"user": older_profile, "sample_id": "synthetic_270_clean"})
    assert first.status_code == 201

    newer_profile = {**PROFILE, "fitness_goal": "hypertrophy"}
    second = signed_in_client.post("/scans", json={"user": newer_profile, "sample_id": "synthetic_570_clean"})
    assert second.status_code == 201

    # The first Scan's frozen profile is untouched by the "Profile change"
    # that produced the second Scan — there is no shared mutable Profile row
    # to have rewritten it (issue #29: frozen onto the Scan, not pointed at).
    assert first.json()["profile"]["fitness_goal"] == "fat_loss"


# --- Task 8: History endpoints ----------------------------------------------


def test_list_scans_is_empty_for_a_brand_new_account(signed_in_client: TestClient):
    resp = signed_in_client.get("/scans")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_scans_requires_sign_in(client: TestClient):
    resp = client.get("/scans")
    assert resp.status_code == 401


def test_list_scans_orders_newest_first_with_headline_numbers(signed_in_client: TestClient):
    first = signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    second = signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_570_clean"})
    assert first.status_code == 201
    assert second.status_code == 201

    resp = signed_in_client.get("/scans")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    # Newest first: the second Scan created comes first.
    assert rows[0]["id"] == second.json()["id"]
    assert rows[1]["id"] == first.json()["id"]
    for row in rows:
        assert row["target_calories_kcal"] > 0
        assert row["weight_kg"] > 0
        assert row["percent_body_fat"] > 0
        assert "has_corrections" in row


def test_list_scans_marks_corrected_fields_row(signed_in_client: TestClient):
    clean = signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    corrected = signed_in_client.post(
        "/scans",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "corrections": {"lean_body_mass_kg": 62.5},
            "confirmations": ["weight_kg", "percent_body_fat", "basal_metabolic_rate_kcal"],
        },
    )
    assert clean.status_code == 201
    assert corrected.status_code == 201

    rows = {row["id"]: row for row in signed_in_client.get("/scans").json()}
    assert rows[clean.json()["id"]]["has_corrections"] is False
    assert rows[corrected.json()["id"]]["has_corrections"] is True


def test_get_scan_returns_full_detail(signed_in_client: TestClient):
    created = signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    scan_id = created.json()["id"]

    resp = signed_in_client.get(f"/scans/{scan_id}")
    assert resp.status_code == 200
    assert resp.json() == created.json()


def test_get_scan_requires_sign_in(client: TestClient):
    resp = client.get("/scans/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 401


def test_get_scan_belonging_to_another_account_returns_404(client: TestClient):
    owner = client
    owner.post("/auth/signup", json={"email": "owner@example.com", "password": "password123"})
    created = owner.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    scan_id = created.json()["id"]
    owner.post("/auth/logout")

    other = client
    other.post("/auth/signup", json={"email": "other@example.com", "password": "password123"})
    resp = other.get(f"/scans/{scan_id}")
    assert resp.status_code == 404


def test_get_unknown_scan_returns_404(signed_in_client: TestClient):
    resp = signed_in_client.get("/scans/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# --- Task 10: server-side staleness ------------------------------------------

from datetime import datetime, timedelta, timezone

from backend.main import STALENESS_DAYS


def _seed_scan_at_age(db: Session, account_id, days_old: int) -> None:
    """Directly seed a Scan with a specific created_at, bypassing the
    /scans endpoint (which always uses "now") — this is the state-setup
    issue #29 allows reaching into the ORM for, distinct from the behavior
    assertions themselves, which stay on the HTTP seam."""
    scan = Scan(
        account_id=account_id,
        source_device="inbody_270",
        sample_id="synthetic_270_clean",
        profile=PROFILE,
        measured={"weight_kg": 56.7},
        effective_inbody={
            "weight_kg": 56.7,
            "lean_body_mass_kg": 39.0,
            "percent_body_fat": 31.2,
            "skeletal_muscle_mass_kg": 20.0,
            "basal_metabolic_rate_kcal": 1212.4,
            "segmental_lean": {
                "left_arm_kg": 2.0,
                "right_arm_kg": 2.0,
                "left_leg_kg": 6.0,
                "right_leg_kg": 6.0,
                "trunk_kg": 18.0,
            },
            "source_device": "inbody_270",
            "visceral_fat_level": None,
        },
        corrected_fields=[],
        confirmed_fields=[],
        nutrition={
            "bmr_kcal": 1212.4,
            "tdee_kcal": 1879.2,
            "target_calories_kcal": 1500.0,
            "protein_g": 100.0,
            "carbs_g": 150.0,
            "fats_g": 50.0,
            "fiber_g": 30.0,
        },
        exercises={"exercises": [], "detected_imbalances": [], "unconfirmed_imbalance_pairs": []},
        narrative_text="Plain plan text.",
        narrative_source="fallback",
    )
    db.add(scan)
    db.flush()
    db.query(Scan).filter_by(id=scan.id).update(
        {Scan.created_at: datetime.now(timezone.utc) - timedelta(days=days_old)}
    )
    db.commit()


def test_current_scan_returns_404_for_account_with_no_scans(signed_in_client: TestClient):
    resp = signed_in_client.get("/scans/current")
    assert resp.status_code == 404


def test_current_scan_requires_sign_in(client: TestClient):
    resp = client.get("/scans/current")
    assert resp.status_code == 401


def test_current_scan_within_threshold_is_not_stale(signed_in_client: TestClient, db: Session):
    from backend.db.models import Account

    account = db.query(Account).filter_by(email="scanner@example.com").one()
    _seed_scan_at_age(db, account.id, days_old=STALENESS_DAYS - 1)

    resp = signed_in_client.get("/scans/current")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_stale"] is False
    assert body["age_days"] == STALENESS_DAYS - 1
    # Still a full plan, not a stripped-down response.
    assert body["nutrition"]["target_calories_kcal"] > 0
    assert body["narrative_text"]


def test_current_scan_past_threshold_is_stale_but_still_full(signed_in_client: TestClient, db: Session):
    from backend.db.models import Account

    account = db.query(Account).filter_by(email="scanner@example.com").one()
    _seed_scan_at_age(db, account.id, days_old=STALENESS_DAYS + 1)

    resp = signed_in_client.get("/scans/current")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_stale"] is True
    assert body["age_days"] == STALENESS_DAYS + 1
    # Stale is never hidden, expired, or recomputed (issue #43 AC4) — the
    # exact same full plan content as the non-stale case.
    assert body["nutrition"]["target_calories_kcal"] > 0
    assert body["narrative_text"]


def test_current_scan_exactly_at_threshold_is_not_yet_stale(signed_in_client: TestClient, db: Session):
    """AC: the boundary behaves correctly either side of the threshold — at
    exactly STALENESS_DAYS old, "past 30 days" hasn't happened yet."""
    from backend.db.models import Account

    account = db.query(Account).filter_by(email="scanner@example.com").one()
    _seed_scan_at_age(db, account.id, days_old=STALENESS_DAYS)

    resp = signed_in_client.get("/scans/current")
    assert resp.status_code == 200
    assert resp.json()["is_stale"] is False


def test_current_scan_returns_the_most_recent_of_several(signed_in_client: TestClient, db: Session):
    from backend.db.models import Account

    account = db.query(Account).filter_by(email="scanner@example.com").one()
    _seed_scan_at_age(db, account.id, days_old=10)
    _seed_scan_at_age(db, account.id, days_old=2)
    _seed_scan_at_age(db, account.id, days_old=40)

    resp = signed_in_client.get("/scans/current")
    assert resp.status_code == 200
    assert resp.json()["age_days"] == 2


# --- Widened ScanSummary feeds the Dashboard charts (Requirement 6.2) -------


def test_list_scans_returns_the_charted_metrics(signed_in_client: TestClient):
    """Each row carries what the trend charts plot, not just the headline figures."""
    created = signed_in_client.post(
        "/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"}
    )
    assert created.status_code == 201

    row = signed_in_client.get("/scans").json()[0]
    for field in (
        "weight_kg",
        "percent_body_fat",
        "lean_body_mass_kg",
        "skeletal_muscle_mass_kg",
        "bmr_kcal",
        "target_calories_kcal",
    ):
        assert isinstance(row[field], (int, float)), field
        assert row[field] > 0, field


def test_summary_metrics_come_from_the_scans_own_frozen_snapshot(signed_in_client: TestClient):
    """Nothing in the summary is recomputed, so a row can't drift from its Scan.

    Each value is asserted against the same Scan's stored detail rather than
    against a literal, which is what makes this a statement about the two
    agreeing rather than about one particular sample's numbers.
    """
    created = signed_in_client.post(
        "/scans", json={"user": PROFILE, "sample_id": "synthetic_570_clean"}
    )
    assert created.status_code == 201
    detail = created.json()

    row = next(r for r in signed_in_client.get("/scans").json() if r["id"] == detail["id"])

    assert row["weight_kg"] == detail["effective_inbody"]["weight_kg"]
    assert row["percent_body_fat"] == detail["effective_inbody"]["percent_body_fat"]
    assert row["lean_body_mass_kg"] == detail["effective_inbody"]["lean_body_mass_kg"]
    assert row["skeletal_muscle_mass_kg"] == detail["effective_inbody"]["skeletal_muscle_mass_kg"]
    assert row["bmr_kcal"] == detail["nutrition"]["bmr_kcal"]
    assert row["target_calories_kcal"] == detail["nutrition"]["target_calories_kcal"]


def test_a_corrected_value_is_what_the_chart_plots(signed_in_client: TestClient):
    """The trend follows the plan's effective reading, not the raw misread one.

    `real_270_flagged`'s stored lean body mass is the misread value; correcting it
    is what the plan was computed from, so it must also be what the chart shows.
    """
    corrected = signed_in_client.post(
        "/scans",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "corrections": {"lean_body_mass_kg": 62.5},
            "confirmations": ["weight_kg", "percent_body_fat", "basal_metabolic_rate_kcal"],
        },
    )
    assert corrected.status_code == 201

    row = next(
        r for r in signed_in_client.get("/scans").json() if r["id"] == corrected.json()["id"]
    )
    assert row["lean_body_mass_kg"] == 62.5
    assert row["has_corrections"] is True


def test_summary_never_exposes_a_sheet_image(signed_in_client: TestClient):
    """ADR-0011, restated at the widened seam: no key here carries image data."""
    signed_in_client.post("/scans", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})
    row = signed_in_client.get("/scans").json()[0]
    assert not any("image" in key or "photo" in key for key in row)
