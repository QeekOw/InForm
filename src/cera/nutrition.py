from pydantic import BaseModel


class NutritionTargets(BaseModel):
    # Recomputed via Katch-McArdle (370 + 21.6 x lean_body_mass_kg) — never read
    # from InBodyPayload.basal_metabolic_rate_kcal, which is a cross-check only.
    bmr_kcal: float
    tdee_kcal: float  # bmr_kcal x UserProfile.activity_multiplier
    target_calories_kcal: float  # tdee_kcal adjusted for UserProfile.fitness_goal
    protein_g: float
    carbs_g: float
    fats_g: float
    fiber_g: float
