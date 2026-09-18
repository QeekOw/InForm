from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import app, get_llm_client
from inform.master import DailyPlan
from inform.samples import load_extractions
from tests.test_master import _inbody

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

    assert plan["exercises"]["detected_imbalances"] == []
    assert plan["exercises"]["unconfirmed_imbalance_pairs"] == ["arm", "leg"]
    assert "not assessed for the arm and leg" in plan["narrative_text"]
    exercises = plan["exercises"]["exercises"]
    assert exercises
    for ex in exercises:
        assert ex["name"] and ex["target"]
        assert ex["movement_type"] in ("corrective_unilateral", "bilateral_compound", "cardio_hiit")
    assert plan["narrative_text"]


def test_confirmed_clean_sample_reports_imbalance(use_llm):
    use_llm(_llm_raising())
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "sample_id": "synthetic_270_clean",
            "confirmations": [
                "segmental_lean.left_arm_kg",
                "segmental_lean.right_arm_kg",
                "segmental_lean.left_leg_kg",
                "segmental_lean.right_leg_kg",
            ],
        },
    )

    assert response.status_code == 200
    exercises = response.json()["exercises"]
    assert exercises["detected_imbalances"]
    assert exercises["unconfirmed_imbalance_pairs"] == []


def test_corrected_segmental_value_counts_as_confirmed(use_llm):
    use_llm(_llm_raising())
    inbody = _inbody(
        segmental_lean=_inbody().segmental_lean.model_copy(
            update={"left_leg_kg": 7.9, "right_leg_kg": 9.0}
        )
    )
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "inbody": inbody.model_dump(),
            "corrections": {"segmental_lean.left_leg_kg": 8.0},
            "confirmations": ["segmental_lean.right_leg_kg"],
        },
    )

    assert response.status_code == 200
    exercises = response.json()["exercises"]
    assert exercises["detected_imbalances"] == ["L/R leg lean-mass deviation 11.1%"]
    assert exercises["unconfirmed_imbalance_pairs"] == ["arm"]


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
    detail = response.json()["detail"]
    assert detail["error"] == "not_an_inbody_sheet"
    assert "does not appear to be an inbody" in detail["message"].lower()


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
            "confirmations": ["weight_kg", "percent_body_fat", "basal_metabolic_rate_kcal"],
        },
    )

    assert response.status_code == 200
    plan = response.json()
    assert plan["corrected_fields"] == ["lean_body_mass_kg"]
    assert sorted(plan["confirmed_fields"]) == ["basal_metabolic_rate_kcal", "percent_body_fat", "weight_kg"]
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
    detail = response.json()["detail"]
    assert detail["error"] == "not_an_inbody_sheet"
    assert "does not appear to be an inbody" in detail["message"].lower()


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


def test_confirming_unchanged_flagged_sample_lets_plan_proceed(use_llm):
    """AC: Confirming an unchanged flagged value lets the plan proceed; value stays measured."""
    use_llm(_llm_raising())
    flagged = ["weight_kg", "percent_body_fat", "lean_body_mass_kg", "basal_metabolic_rate_kcal"]
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "confirmations": flagged,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert sorted(data["confirmed_fields"]) == sorted(flagged)
    assert data["corrected_fields"] == []
    # Value stays measured (76.0 kg)
    assert data["measured"]["lean_body_mass_kg"] == 76.0


def test_partially_confirmed_flagged_sample_returns_409(use_llm):
    """AC: Building a plan is impossible while a flagged field is unresolved."""
    use_llm(_llm_raising())
    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "sample_id": "real_270_flagged",
            "confirmations": ["weight_kg"],
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "lean_body_mass_kg" in detail["flagged"]


def test_inbody_with_unresolved_flags_rejected_with_409(use_llm):
    """Note from #36 / PR #57: sending inbody directly with suspect values cannot bypass cross-check."""
    use_llm(_llm_raising())
    clean_sample = load_extractions().extractions["synthetic_270_clean"]
    flagged_inbody = clean_sample.data.model_dump()
    flagged_inbody["lean_body_mass_kg"] = 7.0  # Misread like real_270_clean

    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "inbody": flagged_inbody,
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "lean_body_mass_kg" in detail["flagged"]


def test_inbody_with_confirmed_flags_proceeds_with_200(use_llm):
    """AC: Confirming a flagged value passed via inbody lets plan proceed."""
    use_llm(_llm_raising())
    flagged_read = load_extractions().extractions["real_270_flagged"]
    inbody_data = flagged_read.data.model_dump()
    flagged = flagged_read.flagged

    response = client.post(
        "/plan",
        json={
            "user": PROFILE,
            "inbody": inbody_data,
            "confirmations": flagged,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert sorted(data["confirmed_fields"]) == sorted(flagged)
    assert data["corrected_fields"] == []


