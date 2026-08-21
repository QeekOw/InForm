import pytest

from inform.exercise import Exercise, ExercisePlan
from inform.inbody import InBodyPayload, SegmentalLean
from inform.master import DailyPlan, MasterPayload
from inform.nutrition import NutritionTargets
from inform.synthesis.validate import (
    NumericalMutationError,
    generate_fallback_plan,
    validate_no_mutation,
)
from inform.user import UserProfile


def _sample_master() -> MasterPayload:
    seg = SegmentalLean(
        left_arm_kg=3.5,
        right_arm_kg=3.5,
        left_leg_kg=9.0,
        right_leg_kg=9.0,
        trunk_kg=26.0,
    )
    inbody = InBodyPayload(
        weight_kg=75.0,
        lean_body_mass_kg=61.0,
        percent_body_fat=18.6,
        skeletal_muscle_mass_kg=35.0,
        basal_metabolic_rate_kcal=1687.6,
        segmental_lean=seg,
        source_device="inbody_570",
        visceral_fat_level=6,
    )
    user = UserProfile(
        age=25,
        biological_sex="male",
        activity_multiplier=1.5,
        fitness_goal="hypertrophy",
    )
    nutrition = NutritionTargets(
        bmr_kcal=1687.6,
        tdee_kcal=2531.4,
        target_calories_kcal=2784.5,
        protein_g=175.0,
        carbs_g=330.0,
        fats_g=77.0,
        fiber_g=38.0,
    )
    exercises = ExercisePlan(
        exercises=[
            Exercise(
                name="Barbell Squat",
                target="quads",
                body_part="upper legs",
                equipment="barbell",
                secondary_muscles=["glutes"],
                movement_type="bilateral_compound",
            )
        ],
        detected_imbalances=["L/R Leg SMM deviation 6.2%"],
    )
    return MasterPayload(
        user=user,
        inbody=inbody,
        nutrition=nutrition,
        exercises=exercises,
    )


def test_validate_no_mutation_passes_on_matching_numbers():
    master = _sample_master()
    valid_plan = DailyPlan(
        narrative_text="Great work today! Here is your custom plan...",
        target_calories_kcal=2784.5,
        protein_g=175.0,
        carbs_g=330.0,
        fats_g=77.0,
        fiber_g=38.0,
    )
    result = validate_no_mutation(master, valid_plan)
    assert result == valid_plan


def test_validate_no_mutation_raises_on_tweaked_protein():
    master = _sample_master()
    mutated_plan = DailyPlan(
        narrative_text="AI tweaked protein...",
        target_calories_kcal=2784.5,
        protein_g=160.0,  # Expected 175.0!
        carbs_g=330.0,
        fats_g=77.0,
        fiber_g=38.0,
    )
    with pytest.raises(NumericalMutationError) as exc_info:
        validate_no_mutation(master, mutated_plan)
    assert exc_info.value.field_name == "protein_g"
    assert exc_info.value.expected == 175.0
    assert exc_info.value.actual == 160.0


def test_validate_no_mutation_raises_on_tweaked_calories():
    master = _sample_master()
    mutated_plan = DailyPlan(
        narrative_text="AI tweaked calories...",
        target_calories_kcal=2500.0,  # Expected 2784.5!
        protein_g=175.0,
        carbs_g=330.0,
        fats_g=77.0,
        fiber_g=38.0,
    )
    with pytest.raises(NumericalMutationError) as exc_info:
        validate_no_mutation(master, mutated_plan)
    assert exc_info.value.field_name == "target_calories_kcal"


def test_generate_fallback_plan_preserves_all_deterministic_numbers():
    master = _sample_master()
    fallback = generate_fallback_plan(master)

    # Validate that fallback plan satisfies validate_no_mutation without errors
    validated = validate_no_mutation(master, fallback)
    assert validated.target_calories_kcal == master.nutrition.target_calories_kcal
    assert validated.protein_g == master.nutrition.protein_g
    assert validated.carbs_g == master.nutrition.carbs_g
    assert validated.fats_g == master.nutrition.fats_g
    assert validated.fiber_g == master.nutrition.fiber_g

    # Check narrative content
    assert "Daily Fitness & Nutrition Plan (Muscle Hypertrophy)" in fallback.narrative_text
    assert "Barbell Squat" in fallback.narrative_text
    assert "L/R Leg SMM deviation 6.2%" in fallback.narrative_text
