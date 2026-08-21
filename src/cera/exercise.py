from typing import Literal

from pydantic import BaseModel


class Exercise(BaseModel):
    # Fields mirror the hasaneyldrm/exercises-dataset taxonomy (target,
    # bodyPart, equipment, secondaryMuscles) so entries can be looked up
    # directly from that dataset without a translation layer.
    name: str
    target: str
    body_part: str
    equipment: str
    secondary_muscles: list[str]
    movement_type: Literal[
        "corrective_unilateral", "bilateral_compound", "cardio_hiit"
    ]


class ExercisePlan(BaseModel):
    exercises: list[Exercise]
    # Human-readable, e.g. "L/R leg SMM deviation 7%" — surfaced directly in
    # Module 4's narrative and echoed back for dual-validation (issue #15).
    detected_imbalances: list[str]
