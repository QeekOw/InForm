from unittest.mock import MagicMock

import pytest

from inform.exercise import Exercise, ExercisePlan
from inform.inbody import InBodyPayload, SegmentalLean
from inform.master import DailyPlan, MasterPayload
from inform.nutrition import NutritionTargets
from inform.synthesis.generate import synthesize_plan
from inform.user import UserProfile


def _create_test_master(
    device: str = "inbody_570", visceral_fat: int | None = 6
) -> MasterPayload:
    seg = SegmentalLean(
        left_arm_kg=3.4,
        right_arm_kg=3.4,
        left_leg_kg=8.8,
        right_leg_kg=8.8,
        trunk_kg=25.5,
    )
    inbody = InBodyPayload(
        weight_kg=73.0,
        lean_body_mass_kg=59.9,
        percent_body_fat=17.9,
        skeletal_muscle_mass_kg=34.2,
        basal_metabolic_rate_kcal=1663.8,
        segmental_lean=seg,
        source_device=device,
        visceral_fat_level=visceral_fat,
    )
    user = UserProfile(
        age=27,
        biological_sex="female",
        activity_multiplier=1.35,
        fitness_goal="fat_loss",
    )
    nutrition = NutritionTargets(
        bmr_kcal=1663.8,
        tdee_kcal=2246.1,
        target_calories_kcal=1796.9,
        protein_g=135.0,
        carbs_g=180.0,
        fats_g=48.0,
        fiber_g=28.0,
    )
    exercises = ExercisePlan(
        exercises=[
            Exercise(
                name="Dumbbell Lunge",
                target="glutes",
                body_part="upper legs",
                equipment="dumbbell",
                secondary_muscles=["quads", "hamstrings"],
                movement_type="corrective_unilateral",
            )
        ],
        detected_imbalances=["Left/Right leg imbalance 6.1%"],
    )
    return MasterPayload(
        user=user,
        inbody=inbody,
        nutrition=nutrition,
        exercises=exercises,
    )


def test_synthesize_plan_with_mock_client_success():
    master = _create_test_master()

    mock_plan = DailyPlan(
        narrative_text="Hello! Welcome to your personalized fitness journey. We've included single-leg lunges to correct your leg balance...",
        target_calories_kcal=1796.9,
        protein_g=135.0,
        carbs_g=180.0,
        fats_g=48.0,
        fiber_g=28.0,
    )

    # Mock OpenAI completion response
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = mock_plan
    mock_client.beta.chat.completions.parse.return_value.choices = [mock_choice]

    result = synthesize_plan(master, client=mock_client)

    assert result.narrative_text == mock_plan.narrative_text
    assert result.target_calories_kcal == 1796.9
    assert result.protein_g == 135.0
    mock_client.beta.chat.completions.parse.assert_called_once()


def test_synthesize_plan_drops_on_llm_mutation_and_falls_back():
    master = _create_test_master()

    # LLM hallucinates different calories/protein
    mutated_plan = DailyPlan(
        narrative_text="I decided to give you fewer calories!",
        target_calories_kcal=1500.0,  # Mutated!
        protein_g=110.0,  # Mutated!
        carbs_g=180.0,
        fats_g=48.0,
        fiber_g=28.0,
    )

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = mutated_plan
    mock_client.beta.chat.completions.parse.return_value.choices = [mock_choice]

    result = synthesize_plan(master, client=mock_client)

    # Should have dropped the LLM text and safely fallen back to exact numbers
    assert result.target_calories_kcal == master.nutrition.target_calories_kcal
    assert result.protein_g == master.nutrition.protein_g
    assert "Daily Fitness & Nutrition Plan (Fat Loss)" in result.narrative_text
    assert "Dumbbell Lunge" in result.narrative_text


def test_synthesize_plan_handles_api_exception_gracefully():
    master = _create_test_master()

    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.side_effect = RuntimeError(
        "OpenAI API rate limit / network error"
    )

    result = synthesize_plan(master, client=mock_client)

    # Should catch the error and return a safe deterministic fallback
    assert result.target_calories_kcal == master.nutrition.target_calories_kcal
    assert result.protein_g == master.nutrition.protein_g
    assert "Daily Fitness & Nutrition Plan" in result.narrative_text


def test_synthesize_plan_inbody_270_no_visceral_fat():
    master = _create_test_master(device="inbody_270", visceral_fat=None)
    assert master.inbody.visceral_fat_level is None

    mock_plan = DailyPlan(
        narrative_text="InBody 270 scan personalized plan...",
        target_calories_kcal=1796.9,
        protein_g=135.0,
        carbs_g=180.0,
        fats_g=48.0,
        fiber_g=28.0,
    )

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.parsed = mock_plan
    mock_client.beta.chat.completions.parse.return_value.choices = [mock_choice]

    result = synthesize_plan(master, client=mock_client)
    assert result.target_calories_kcal == 1796.9
