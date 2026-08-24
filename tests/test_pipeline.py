from pathlib import Path

import pytest

from inform.engines.vlm import _RawExtraction
from inform.errors import IncompleteExtractionError
from inform.pipeline import run_pipeline

from tests.test_exercise_filter import _pool
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


def test_run_pipeline_assembles_master_payload(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, visceral_fat_level=7))
    user = _user(fitness_goal="fat_loss", activity_multiplier=1.55)

    master = run_pipeline(FIXTURE, user, _pool())

    assert master.inbody.lean_body_mass_kg == 58.0
    assert master.inbody.visceral_fat_level == 7
    assert master.nutrition.bmr_kcal == pytest.approx(1622.8)
    assert master.exercises.detected_imbalances == []  # default fixture is symmetric


def test_run_pipeline_wires_asymmetry_into_exercise_plan(fake_openai, raw_segmental):
    fake_openai(
        _raw(raw_segmental, segmental_lean=raw_segmental(left_leg_kg=8.0, right_leg_kg=9.0))
    )
    user = _user(fitness_goal="hypertrophy")

    master = run_pipeline(FIXTURE, user, _pool())

    assert master.exercises.detected_imbalances == ["L/R leg SMM deviation 11.1%"]
    assert master.exercises.exercises[0].name == "Bulgarian split squat"


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
