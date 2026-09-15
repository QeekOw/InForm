from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app, get_llm_client
from inform.master import DailyPlan
from inform.samples import load_extractions

client = TestClient(app)

PROFILE = {
    "age": 30,
    "biological_sex": "female",
    "activity_multiplier": 1.55,
    "fitness_goal": "fat_loss",
}


def _post_clean_sample():
    return client.post("/plan", json={"user": PROFILE, "sample_id": "synthetic_270_clean"})


def _llm_returning(plan: DailyPlan) -> MagicMock:
    llm = MagicMock()
    llm.beta.chat.completions.parse.return_value.choices = [MagicMock(message=MagicMock(parsed=plan))]
    return llm


def _llm_raising() -> MagicMock:
    llm = MagicMock()
    llm.beta.chat.completions.parse.side_effect = RuntimeError("LLM unavailable")
    return llm


@pytest.fixture
def use_llm():
    def _install(llm: MagicMock) -> None:
        app.dependency_overrides[get_llm_client] = lambda: llm

    yield _install
    app.dependency_overrides.clear()


def test_clean_sample_produces_full_plan_with_no_human_input(use_llm):
    """AC: Picking a clean Sample sheet produces a full set of results with no human input."""
    use_llm(_llm_raising())
    response = _post_clean_sample()

    assert response.status_code == 200
    plan = response.json()

    # Katch-McArdle on the sheet's stored LBM of 39.0 kg: 370 + 21.6 * 39.0.
    assert plan["nutrition"]["bmr_kcal"] == pytest.approx(1212.4)
    assert plan["nutrition"]["tdee_kcal"] == pytest.approx(1212.4 * 1.55)
    for grams in ("protein_g", "carbs_g", "fats_g", "fiber_g"):
        assert plan["nutrition"][grams] > 0

    # Legs read 6.9 vs 6.4 kg, a deviation above the 5% threshold.
    assert plan["exercises"]["detected_imbalances"]
    exercises = plan["exercises"]["exercises"]
    assert exercises
    for ex in exercises:
        assert ex["name"] and ex["target"]
        assert ex["movement_type"] in ("corrective_unilateral", "bilateral_compound", "cardio_hiit")
    assert plan["narrative_text"]


def test_plan_needs_exactly_one_reading_source(use_llm):
    use_llm(_llm_raising())
    reading = client.get("/samples/synthetic_270_clean").json()["data"]

    neither = client.post("/plan", json={"user": PROFILE})
    both = client.post(
        "/plan", json={"user": PROFILE, "sample_id": "synthetic_270_clean", "inbody": reading}
    )

    assert neither.status_code == 422
    assert both.status_code == 422


def test_generated_narrative_is_returned_and_labelled_as_generated(use_llm):
    use_llm(_llm_raising())
    targets = _post_clean_sample().json()["nutrition"]

    use_llm(
        _llm_returning(
            DailyPlan(
                narrative_text="Keep your single-leg work steady this week.",
                target_calories_kcal=targets["target_calories_kcal"],
                protein_g=targets["protein_g"],
                carbs_g=targets["carbs_g"],
                fats_g=targets["fats_g"],
                fiber_g=targets["fiber_g"],
            )
        )
    )
    plan = _post_clean_sample().json()

    assert plan["narrative_text"] == "Keep your single-leg work steady this week."
    assert plan["narrative_source"] == "generated"


def test_narrative_failure_falls_back_to_plain_plan(use_llm):
    """AC: A failure to generate the narrative falls back to a safe plain plan."""
    use_llm(_llm_raising())
    plan = _post_clean_sample().json()

    assert plan["narrative_source"] == "fallback"
    assert f"{plan['nutrition']['target_calories_kcal']:.0f} kcal" in plan["narrative_text"]


def test_mutated_narrative_is_dropped_rather_than_shown(use_llm):
    """AC: ...rather than a wrong number."""
    use_llm(
        _llm_returning(
            DailyPlan(
                narrative_text="Eat 1500 kcal a day.",
                target_calories_kcal=1500.0,
                protein_g=1.0,
                carbs_g=1.0,
                fats_g=1.0,
                fiber_g=1.0,
            )
        )
    )
    plan = _post_clean_sample().json()

    assert plan["narrative_source"] == "fallback"
    assert "1500" not in plan["narrative_text"]
    assert plan["nutrition"]["target_calories_kcal"] != 1500.0


def test_flagged_sample_is_not_planned_without_a_person(use_llm):
    """Fail-closed (ADR-0008): a flagged read never reaches a plan on its own."""
    use_llm(_llm_raising())
    response = client.post("/plan", json={"user": PROFILE, "sample_id": "real_270_flagged"})

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "lean_body_mass_kg" in detail["flagged"]
    assert detail["unread"] == []


def test_refused_sample_is_not_planned(use_llm):
    use_llm(_llm_raising())
    response = client.post("/plan", json={"user": PROFILE, "sample_id": "refused_non_sheet"})

    assert response.status_code == 409
    assert "weight_kg" in response.json()["detail"]["unread"]


def test_unknown_sample_returns_404(use_llm):
    use_llm(_llm_raising())
    response = client.post("/plan", json={"user": PROFILE, "sample_id": "nonexistent_id"})

    assert response.status_code == 404


def test_corrections_allow_flagged_or_unread_sample_to_proceed(use_llm):
    """AC: A typed value lets the plan proceed; corrected fields are recorded alongside measured fields."""
    use_llm(_llm_raising())
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "corrections": {"lean_body_mass_kg": 62.5},
        },
    )

    assert response.status_code == 200
    plan = response.json()
    assert plan["corrected_fields"] == ["lean_body_mass_kg"]
    # BMR recomputed on the corrected LBM: 370 + 21.6 * 62.5 = 1720.0
    assert plan["nutrition"]["bmr_kcal"] == pytest.approx(1720.0)


def test_out_of_range_correction_returns_422(use_llm):
    """AC: An out-of-range value is rejected before the plan is computed."""
    use_llm(_llm_raising())
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "corrections": {"lean_body_mass_kg": 500.0},
        },
    )

    assert response.status_code == 422
    assert "out of plausible range" in response.text


def test_wrong_unit_correction_returns_422(use_llm):
    """AC: A wrong-unit value is rejected before the plan is computed."""
    use_llm(_llm_raising())
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "corrections": {"lean_body_mass_kg": {"value": 62.5, "unit": "lbs"}},
        },
    )

    assert response.status_code == 422
    assert "Invalid unit 'lbs'" in response.text


def test_plan_fails_when_required_field_remains_unread(use_llm):
    """AC: Building a plan is impossible while a required field remains unread."""
    use_llm(_llm_raising())
    partial_measured = {
        "weight_kg": 70.0,
        "percent_body_fat": 20.0,
        "source_device": "inbody_270",
    }
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "measured": partial_measured,
            "corrections": {"skeletal_muscle_mass_kg": 30.0},
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "lean_body_mass_kg" in detail["unread"]


def test_refused_sample_with_corrections_is_hard_refused(use_llm):
    """ADR-0008 Amendment §3: Non-InBody refusal sheet cannot be planned around."""
    use_llm(_llm_raising())
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "sample_id": "refused_non_sheet",
            "corrections": {"weight_kg": 70.0},
        },
    )
    assert response.status_code == 409
    assert "refused" in response.json()["detail"]["message"].lower()


def test_plan_with_measured_and_corrections_proceeds(use_llm):
    """AC: A typed value lets the plan proceed; measured is returned unmerged alongside corrected_fields."""
    use_llm(_llm_raising())
    clean_sample = load_extractions().extractions["synthetic_270_clean"]
    measured_data = clean_sample.data.model_dump()
    measured_data["lean_body_mass_kg"] = None  # simulate unread LBM

    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "measured": measured_data,
            "corrections": {"lean_body_mass_kg": 39.0},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["corrected_fields"] == ["lean_body_mass_kg"]
    assert data["measured"]["weight_kg"] == 56.7
    assert data["measured"]["lean_body_mass_kg"] is None  # unmerged!


def test_unresolved_cross_check_flags_rejected_by_plan(use_llm):
    """ADR-0008 §2: Unresolved cross-check violations are rejected with 409."""
    use_llm(_llm_raising())
    # real_270_flagged has mismatched LBM. Correcting only visceral fat leaves it flagged.
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "corrections": {"visceral_fat_level": 8},
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "lean_body_mass_kg" in detail["flagged"]

