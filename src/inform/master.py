from typing import Literal

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


class CoachingDraft(BaseModel):
    """Bounded, non-actionable prose returned by the LLM."""

    coaching_text: str = Field(..., min_length=1, max_length=1000)


class DailyPlan(BaseModel):
    """Final synthesized plan produced by Module 4.

    ``narrative_text`` combines an optional coaching note with deterministic facts.
    The echoed fields are copied from Module 2 and checked by ``validate_no_mutation``.
    """

    narrative_text: str = Field(
        ..., description="Optional coaching note plus deterministic plan facts."
    )
    narrative_source: Literal["generated", "fallback"]
    target_calories_kcal: float = Field(..., ge=0, description="Echoed daily calorie target.")
    protein_g: float = Field(..., ge=0, description="Echoed protein target in grams.")
    carbs_g: float = Field(..., ge=0, description="Echoed carbohydrate target in grams.")
    fats_g: float = Field(..., ge=0, description="Echoed fat target in grams.")
    fiber_g: float = Field(..., ge=0, description="Echoed fiber target in grams.")
