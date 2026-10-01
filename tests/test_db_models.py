"""Task 1 (accounts-and-history spec): Account/Scan ORM models against a real
Postgres, per issue #29's testing decision (no sqlite substitute). Each test
runs inside a transaction that is rolled back afterward (the `db` fixture in
tests/conftest.py), so nothing persists between test runs or pollutes the
real database.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from backend.db.models import Account, Scan


def _make_account(email: str = "person@example.com") -> Account:
    return Account(email=email, password_hash="not-a-real-hash")


def test_insert_and_read_back_account(db: Session):
    account = _make_account()
    db.add(account)
    db.commit()

    fetched = db.query(Account).filter_by(email="person@example.com").one()
    assert fetched.id == account.id
    assert fetched.email == "person@example.com"
    assert fetched.password_hash == "not-a-real-hash"
    assert fetched.created_at is not None


def test_account_email_unique(db: Session):
    db.add(_make_account("dup@example.com"))
    db.commit()

    db.add(_make_account("dup@example.com"))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_scan_requires_account_and_cascades_on_delete(db: Session):
    account = _make_account("scanner@example.com")
    db.add(account)
    db.commit()

    scan = Scan(
        account_id=account.id,
        source_device="inbody_270",
        sample_id="synthetic_270_clean",
        profile={"age": 30, "biological_sex": "female", "activity_multiplier": 1.55, "fitness_goal": "fat_loss"},
        measured={"weight_kg": 68.0},
        effective_inbody={"weight_kg": 68.0, "lean_body_mass_kg": 50.0},
        corrected_fields=[],
        confirmed_fields=[],
        nutrition={"bmr_kcal": 1450.0},
        exercises={"exercises": [], "detected_imbalances": []},
        narrative_text="Plain plan text.",
        narrative_source="fallback",
    )
    db.add(scan)
    db.commit()

    fetched = db.query(Scan).filter_by(account_id=account.id).one()
    assert fetched.profile["fitness_goal"] == "fat_loss"
    assert fetched.corrected_fields == []

    # No image field exists anywhere on the model (ADR-0011): confirm the ORM
    # mapper's columns don't include one, so a future accidental addition would
    # fail this test rather than slip in silently.
    column_names = {c.name for c in Scan.__table__.columns}
    assert not any("image" in name or "photo" in name for name in column_names)

    db.delete(account)
    db.commit()
    assert db.query(Scan).filter_by(id=scan.id).one_or_none() is None


def test_scan_missing_account_is_rejected(db: Session):
    orphan_scan = Scan(
        account_id=uuid.uuid4(),
        profile={},
        measured={},
        effective_inbody={},
        corrected_fields=[],
        confirmed_fields=[],
        nutrition={},
        exercises={},
        narrative_text="",
        narrative_source="fallback",
    )
    db.add(orphan_scan)
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


# --- Account profile defaults and credential rules -------------------------
#
# The new Account columns are pre-fill defaults only. What produced a plan is
# the Scan's own frozen `profile` snapshot, never these (issue #42).


def test_password_only_account_still_works(db: Session):
    """The existing shape of an account is unaffected by the delta."""
    account = _make_account("password-only@example.com")
    db.add(account)
    db.commit()

    fetched = db.query(Account).filter_by(email="password-only@example.com").one()
    assert fetched.password_hash == "not-a-real-hash"
    assert fetched.google_sub is None
    # Every new column is optional, so nothing is required of an existing caller.
    assert fetched.date_of_birth is None
    assert fetched.height_cm is None
    assert fetched.default_biological_sex is None
    assert fetched.default_activity_multiplier is None
    assert fetched.default_fitness_goal is None


def test_google_only_account_needs_no_password(db: Session):
    """password_hash is nullable so a Google-only identity is representable."""
    account = Account(email="google-only@example.com", google_sub="google-sub-123")
    db.add(account)
    db.commit()

    fetched = db.query(Account).filter_by(email="google-only@example.com").one()
    assert fetched.password_hash is None
    assert fetched.google_sub == "google-sub-123"


def test_account_with_neither_credential_is_rejected(db: Session):
    """The CHECK constraint refuses an account nobody could ever sign into."""
    db.add(Account(email="no-way-in@example.com"))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_google_sub_is_unique(db: Session):
    db.add(Account(email="first@example.com", google_sub="same-sub"))
    db.commit()

    db.add(Account(email="second@example.com", google_sub="same-sub"))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()


def test_profile_defaults_round_trip(db: Session):
    from datetime import date

    account = Account(
        email="defaults@example.com",
        password_hash="not-a-real-hash",
        date_of_birth=date(1995, 6, 15),
        height_cm=178.5,
        default_biological_sex="female",
        default_activity_multiplier=1.55,
        default_fitness_goal="hypertrophy",
    )
    db.add(account)
    db.commit()

    fetched = db.query(Account).filter_by(email="defaults@example.com").one()
    assert fetched.date_of_birth == date(1995, 6, 15)
    assert fetched.height_cm == 178.5
    assert fetched.default_biological_sex == "female"
    assert fetched.default_activity_multiplier == 1.55
    assert fetched.default_fitness_goal == "hypertrophy"


def test_scan_table_is_unchanged_by_the_account_delta():
    """Issue #42's guarantee is structural: the Scan table gains nothing here.

    Pinned as an exact set so adding a column to Scan has to be a deliberate act
    that updates this test, rather than something that slips through.
    """
    assert {c.name for c in Scan.__table__.columns} == {
        "id",
        "account_id",
        "created_at",
        "source_device",
        "sample_id",
        "profile",
        "measured",
        "effective_inbody",
        "corrected_fields",
        "confirmed_fields",
        "nutrition",
        "exercises",
        "narrative_text",
        "narrative_source",
    }


def test_changing_an_account_default_does_not_touch_a_saved_scan(db: Session):
    """Property 3: a past Scan never changes.

    The whole reason the defaults live on Account and the snapshot lives on Scan.
    """
    account = Account(
        email="frozen@example.com",
        password_hash="not-a-real-hash",
        default_fitness_goal="fat_loss",
        default_activity_multiplier=1.2,
    )
    db.add(account)
    db.commit()

    frozen_profile = {
        "age": 30,
        "biological_sex": "female",
        "activity_multiplier": 1.55,
        "fitness_goal": "fat_loss",
    }
    scan = Scan(
        account_id=account.id,
        profile=dict(frozen_profile),
        measured={"weight_kg": 68.0},
        effective_inbody={"weight_kg": 68.0, "lean_body_mass_kg": 50.0},
        corrected_fields=[],
        confirmed_fields=[],
        nutrition={"bmr_kcal": 1450.0, "target_calories_kcal": 2000.0},
        exercises={"exercises": [], "detected_imbalances": []},
        narrative_text="Plain plan text.",
        narrative_source="fallback",
    )
    db.add(scan)
    db.commit()

    # Change the person's mind about everything.
    account.default_fitness_goal = "hypertrophy"
    account.default_activity_multiplier = 1.9
    account.date_of_birth = None
    db.commit()
    db.expire_all()

    reloaded = db.query(Scan).filter_by(id=scan.id).one()
    assert reloaded.profile == frozen_profile
    assert reloaded.nutrition == {"bmr_kcal": 1450.0, "target_calories_kcal": 2000.0}
