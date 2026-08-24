from inform.inbody import InBodyPayload
from inform.nutrition import NutritionTargets
from inform.user import UserProfile

# Katch-McArdle: BMR = 370 + 21.6 x LBM_kg (ADR-0001 [reserved], CONTEXT.md).
_KATCH_MCARDLE_BASE_KCAL = 370.0
_KATCH_MCARDLE_LBM_COEFFICIENT = 21.6

# The paper (§3.1.2/§3.1.3.2) requires calorie/macro targets to differ by
# fitness_goal but does not specify magnitudes. These follow standard
# sports-nutrition ranges: a ~300 kcal lean-bulk surplus, a ~500 kcal/day
# deficit (~0.5 kg/week loss), and goal-tiered protein (g/kg LBM, not total
# weight) with fat-loss at the higher end to protect lean mass in a deficit.
_CALORIE_ADJUSTMENT_KCAL = {
    "hypertrophy": 300.0,
    "fat_loss": -500.0,
}
_PROTEIN_G_PER_LBM_KG = {
    "hypertrophy": 2.2,
    "fat_loss": 2.4,
}
_FAT_FRACTION_OF_CALORIES = 0.25
_FIBER_G_PER_1000_KCAL = 14.0

_KCAL_PER_G_PROTEIN = 4.0
_KCAL_PER_G_CARB = 4.0
_KCAL_PER_G_FAT = 9.0


def compute_targets(user: UserProfile, inbody: InBodyPayload) -> NutritionTargets:
    """Module 2: deterministic BMR/TDEE/macro targets.

    BMR is always recomputed from lean_body_mass_kg; InBodyPayload's own
    basal_metabolic_rate_kcal is a cross-check value only (ADR-0003,
    ADR-0008) and is never read here.
    """
    bmr_kcal = (
        _KATCH_MCARDLE_BASE_KCAL
        + _KATCH_MCARDLE_LBM_COEFFICIENT * inbody.lean_body_mass_kg
    )
    tdee_kcal = bmr_kcal * user.activity_multiplier
    target_calories_kcal = tdee_kcal + _CALORIE_ADJUSTMENT_KCAL[user.fitness_goal]

    protein_g = _PROTEIN_G_PER_LBM_KG[user.fitness_goal] * inbody.lean_body_mass_kg
    fat_g = (target_calories_kcal * _FAT_FRACTION_OF_CALORIES) / _KCAL_PER_G_FAT

    protein_kcal = protein_g * _KCAL_PER_G_PROTEIN
    fat_kcal = fat_g * _KCAL_PER_G_FAT
    # Clamped at zero: an extreme LBM/activity/goal combination could push
    # protein + fat calories above target_calories_kcal before carbs are
    # even considered. Rather than emit a negative gram count, carbs floor
    # at zero — protein and fat targets still hold.
    carb_kcal = max(0.0, target_calories_kcal - protein_kcal - fat_kcal)
    carbs_g = carb_kcal / _KCAL_PER_G_CARB

    fiber_g = _FIBER_G_PER_1000_KCAL * (target_calories_kcal / 1000.0)

    return NutritionTargets(
        bmr_kcal=bmr_kcal,
        tdee_kcal=tdee_kcal,
        target_calories_kcal=target_calories_kcal,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fats_g=fat_g,
        fiber_g=fiber_g,
    )
