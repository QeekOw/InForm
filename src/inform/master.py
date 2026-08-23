from pydantic import BaseModel

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
