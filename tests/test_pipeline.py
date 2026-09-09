from pathlib import Path
from unittest.mock import MagicMock

import pytest

from inform.engines.vlm import _RawExtraction
from inform.errors import IncompleteExtractionError
from inform.inbody import SegmentalLean
from inform.master import DailyPlan, MasterPayload
from inform.pipeline import (
    assemble_master_payload,
    build_master_payload,
    build_plan,
    run_pipeline,
)
from tests.test_exercise_filter import _pool
from tests.test_master import _inbody
from tests.test_user import _user

FIXTURE = Path(__file__).parent / "fixtures" / "inbody_sample.png"


def _raw(raw_segmental, **overrides) -> _RawExtraction:
    fields = dict(
        is_inbody_sheet=True,
        weight_kg=70.0,
        lean_body_mass_kg=58.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=raw_segmental(),
        source_device="inbody_570",
    )
    fields.update(overrides)
    return _RawExtraction(**fields)


def test_assemble_master_payload(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, visceral_fat_level=7))
    user = _user(fitness_goal="fat_loss", activity_multiplier=1.55)

    master = assemble_master_payload(FIXTURE, user, _pool())

    assert isinstance(master, MasterPayload)
    assert master.inbody.lean_body_mass_kg == 58.0
    assert master.inbody.visceral_fat_level == 7
    assert master.nutrition.bmr_kcal == pytest.approx(1622.8)
    assert master.nutrition.target_calories_kcal == pytest.approx(2015.34)
    assert master.exercises.detected_imbalances == []  # default fixture is symmetric


def test_run_pipeline_end_to_end_synthesis(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, visceral_fat_level=7))
    user = _user(fitness_goal="fat_loss", activity_multiplier=1.55)

    mock_llm_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = DailyPlan(
        narrative_text="Here is your personalized fat loss coaching plan...",
        target_calories_kcal=2015.34,
        protein_g=139.2,
        carbs_g=238.68,
        fats_g=55.98,
        fiber_g=28.21,
    )
    mock_llm_client.beta.chat.completions.parse.return_value.choices = [mock_choice]

    plan = run_pipeline(FIXTURE, user, _pool(), llm_client=mock_llm_client)

    assert isinstance(plan, DailyPlan)
    assert plan.target_calories_kcal == pytest.approx(2015.34)
    assert plan.protein_g == pytest.approx(139.2)
    assert "personalized fat loss coaching plan" in plan.narrative_text


def test_run_pipeline_wires_asymmetry_into_exercise_plan(fake_openai, raw_segmental):
    fake_openai(
        _raw(raw_segmental, segmental_lean=raw_segmental(left_leg_kg=8.0, right_leg_kg=9.0))
    )
    user = _user(fitness_goal="hypertrophy")

    master = assemble_master_payload(FIXTURE, user, _pool())

    assert master.exercises.detected_imbalances == ["L/R leg lean-mass deviation 11.1%"]
    assert master.exercises.exercises[0].name == "Bulgarian split squat"


def test_run_pipeline_fallback_when_no_llm_client(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, visceral_fat_level=7))
    user = _user(fitness_goal="fat_loss", activity_multiplier=1.55)

    # Calling run_pipeline without OPENAI_API_KEY / mock falls back to deterministic DailyPlan
    plan = run_pipeline(FIXTURE, user, _pool())

    assert isinstance(plan, DailyPlan)
    assert plan.target_calories_kcal == pytest.approx(2015.34)
    assert "Daily Fitness & Nutrition Plan (Fat Loss)" in plan.narrative_text


def test_run_pipeline_rejects_incomplete_extraction(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, lean_body_mass_kg=None))
    user = _user()

    with pytest.raises(IncompleteExtractionError) as exc_info:
        run_pipeline(FIXTURE, user, _pool())

    assert "lean_body_mass_kg" in exc_info.value.unread


def test_run_pipeline_rejects_flagged_extraction(fake_openai, raw_segmental):
    # weight x (1 - PBF/100) = 70 x 0.829 = 58.03; 40.0 breaches tolerance.
    fake_openai(_raw(raw_segmental, lean_body_mass_kg=40.0, basal_metabolic_rate_kcal=1234.0))
    user = _user()

    with pytest.raises(IncompleteExtractionError) as exc_info:
        run_pipeline(FIXTURE, user, _pool())

    assert "lean_body_mass_kg" in exc_info.value.flagged


def test_build_master_payload_from_payload():
    inbody = _inbody(visceral_fat_level=7)
    user = _user(fitness_goal="fat_loss", activity_multiplier=1.55)

    master = build_master_payload(inbody, user, _pool())

    assert isinstance(master, MasterPayload)
    assert master.inbody.lean_body_mass_kg == 58.0
    assert master.inbody.visceral_fat_level == 7
    assert master.nutrition.bmr_kcal == pytest.approx(1622.8)
    assert master.nutrition.target_calories_kcal == pytest.approx(2015.34)
    assert master.exercises.detected_imbalances == []


def test_build_plan_from_payload_with_mock_llm():
    inbody = _inbody(visceral_fat_level=7)
    user = _user(fitness_goal="fat_loss", activity_multiplier=1.55)

    mock_llm_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = DailyPlan(
        narrative_text="Here is your coaching plan built directly from payload...",
        target_calories_kcal=2015.34,
        protein_g=139.2,
        carbs_g=238.68,
        fats_g=55.98,
        fiber_g=28.21,
    )
    mock_llm_client.beta.chat.completions.parse.return_value.choices = [mock_choice]

    plan = build_plan(inbody, user, _pool(), llm_client=mock_llm_client)

    assert isinstance(plan, DailyPlan)
    assert plan.target_calories_kcal == pytest.approx(2015.34)
    assert plan.protein_g == pytest.approx(139.2)
    assert "built directly from payload" in plan.narrative_text


def test_build_plan_from_payload_fallback():
    inbody = _inbody(visceral_fat_level=7)
    user = _user(fitness_goal="fat_loss", activity_multiplier=1.55)

    plan = build_plan(inbody, user, _pool())

    assert isinstance(plan, DailyPlan)
    assert plan.target_calories_kcal == pytest.approx(2015.34)
    assert "Daily Fitness & Nutrition Plan (Fat Loss)" in plan.narrative_text


def test_build_master_payload_wires_asymmetry_from_payload():
    inbody = _inbody(
        segmental_lean=SegmentalLean(
            left_arm_kg=3.2,
            right_arm_kg=3.3,
            left_leg_kg=8.0,
            right_leg_kg=9.0,
            trunk_kg=24.5,
        )
    )
    user = _user(fitness_goal="hypertrophy")

    master = build_master_payload(inbody, user, _pool())

    assert master.exercises.detected_imbalances == ["L/R leg lean-mass deviation 11.1%"]
    assert master.exercises.exercises[0].name == "Bulgarian split squat"


