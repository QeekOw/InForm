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


# Field-name lists derived from the schema, so adding a field to the models
# above flows to every consumer (VLM parser, eval harness) without hand-editing
# each — the schema is the single source of truth. Order follows declaration.
SEGMENTAL_FIELDS: tuple[str, ...] = tuple(SegmentalLean.model_fields)
_SCALAR_FIELDS = [n for n in InBodyPayload.model_fields if n != "segmental_lean"]
REQUIRED_FIELDS: tuple[str, ...] = tuple(
    n for n in _SCALAR_FIELDS if InBodyPayload.model_fields[n].is_required()
)
OPTIONAL_FIELDS: tuple[str, ...] = tuple(
    n for n in _SCALAR_FIELDS if not InBodyPayload.model_fields[n].is_required()
)
