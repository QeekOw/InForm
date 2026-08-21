from pydantic import BaseModel, Field

from inform.exercise import ExercisePlan
from inform.inbody import InBodyPayload
from inform.nutrition import NutritionTargets
from inform.user import UserProfile


class MasterPayload(BaseModel):
    """Consolidated output of Modules 1-3; the sole input to Module 4 (issue #15)."""

    user: UserProfile
    inbody: InBodyPayload
    nutrition: NutritionTargets
    exercises: ExercisePlan


class DailyPlan(BaseModel):
    """Final synthesized plan produced by Module 4.

    ``narrative_text`` is the LLM's linguistic output (the only generative field).
    The echoed deterministic fields let ``validate_no_mutation`` confirm the LLM
    did not alter any calculated number from Module 2.
    """

    narrative_text: str = Field(..., description="The LLM-generated empathetic coaching narrative.")
    target_calories_kcal: float = Field(..., ge=0, description="Echoed daily calorie target.")
    protein_g: float = Field(..., ge=0, description="Echoed protein target in grams.")
    carbs_g: float = Field(..., ge=0, description="Echoed carbohydrate target in grams.")
    fats_g: float = Field(..., ge=0, description="Echoed fat target in grams.")
    fiber_g: float = Field(..., ge=0, description="Echoed fiber target in grams.")
