import pytest
from pydantic import ValidationError

from inform.exercise import Exercise, ExercisePlan


def _exercise(**overrides) -> Exercise:
    fields = dict(
        name="Single-leg press",
        target="quadriceps",
        body_part="upper legs",
        equipment="leverage machine",
        secondary_muscles=["glutes", "hamstrings"],
        movement_type="corrective_unilateral",
    )
    fields.update(overrides)
    return Exercise(**fields)


def _plan(**overrides) -> ExercisePlan:
    fields = dict(
        exercises=[_exercise()],
        detected_imbalances=["L/R leg lean-mass deviation 7%"],
    )
    fields.update(overrides)
    return ExercisePlan(**fields)


def test_valid_exercise_plan():
    plan = _plan()
    assert plan.exercises[0].movement_type == "corrective_unilateral"
    assert plan.detected_imbalances == ["L/R leg lean-mass deviation 7%"]


def test_invalid_movement_type_rejected():
    with pytest.raises(ValidationError):
        _exercise(movement_type="cardio_steady_state")


def test_empty_exercise_plan_is_valid():
    plan = _plan(exercises=[], detected_imbalances=[])
    assert plan.exercises == []
    assert plan.detected_imbalances == []


def test_exercise_plan_round_trips_through_json():
    original = _plan()
    restored = ExercisePlan.model_validate_json(original.model_dump_json())
    assert restored == original
