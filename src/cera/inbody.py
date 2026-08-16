from typing import Literal

from pydantic import BaseModel


class SegmentalLean(BaseModel):
    left_arm_kg: float
    right_arm_kg: float
    left_leg_kg: float
    right_leg_kg: float
    trunk_kg: float


class InBodyPayload(BaseModel):
    weight_kg: float
    # Authoritative LBM (ADR-0003): read directly off the sheet, not derived
    # from weight x (1 - PBF/100) — that derivation is a downstream cross-check only.
    lean_body_mass_kg: float
    percent_body_fat: float
    skeletal_muscle_mass_kg: float
    basal_metabolic_rate_kcal: float
    segmental_lean: SegmentalLean
    source_device: Literal["inbody_270", "inbody_570"]
    visceral_fat_level: int | None = None
