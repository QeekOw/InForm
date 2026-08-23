import pytest
from pydantic import ValidationError

from inform.nutrition import NutritionTargets


def _targets(**overrides) -> NutritionTargets:
    fields = dict(
        bmr_kcal=1622.8,
        tdee_kcal=2515.3,
        target_calories_kcal=2015.3,
        protein_g=145.0,
        carbs_g=180.0,
        fats_g=60.0,
        fiber_g=30.0,
    )
    fields.update(overrides)
    return NutritionTargets(**fields)


def test_valid_nutrition_targets():
    targets = _targets()
    assert targets.bmr_kcal == 1622.8
    assert targets.target_calories_kcal == 2015.3


def test_missing_required_field_rejected():
    with pytest.raises(ValidationError):
        NutritionTargets(
            bmr_kcal=1622.8,
            tdee_kcal=2515.3,
            target_calories_kcal=2015.3,
            protein_g=145.0,
            carbs_g=180.0,
            fats_g=60.0,
        )


def test_nutrition_targets_round_trips_through_json():
    original = _targets()
    restored = NutritionTargets.model_validate_json(original.model_dump_json())
    assert restored == original
