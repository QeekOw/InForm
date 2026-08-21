from pydantic import BaseModel

from cera.exercise import ExercisePlan
from cera.inbody import InBodyPayload
from cera.nutrition import NutritionTargets
from cera.user import UserProfile


class MasterPayload(BaseModel):
    """Consolidated output of Modules 1-3; the sole input to Module 4 (issue #15)."""

    user: UserProfile
    inbody: InBodyPayload
    nutrition: NutritionTargets
    exercises: ExercisePlan
