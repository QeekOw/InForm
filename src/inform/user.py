from typing import Literal

from pydantic import BaseModel


class UserProfile(BaseModel):
    # Collected for goal/activity context and a possible future Mifflin-St Jeor
    # fallback (ADR-0001, reserved) — NOT used by Katch-McArdle BMR, which is
    # LBM-based only.
    age: int
    biological_sex: Literal["male", "female"]
    activity_multiplier: float
    fitness_goal: Literal["hypertrophy", "fat_loss"]
