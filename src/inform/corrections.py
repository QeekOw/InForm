"""Plausible range and unit validation, and correction application for InBody fields.

Enforces ADR-0008: fail-closed posture remains intact. A person can supply
values for unread fields off the sheet in hand, or correct misread fields,
but values are strictly validated for plausible physiological ranges and
units to prevent slipped decimals or wrong units from producing a nonsense plan.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field

from inform.inbody import (
    REQUIRED_DOTTED_FIELDS,
    InBodyPayload,
    PartialInBody,
    PartialSegmentalLean,
    SegmentalLean,
)

# Plausible clinical / physiological ranges for human InBody measurements
FIELD_RANGES: dict[str, tuple[float, float]] = {
    "weight_kg": (20.0, 300.0),
    "lean_body_mass_kg": (10.0, 250.0),
    "percent_body_fat": (3.0, 75.0),
    "skeletal_muscle_mass_kg": (5.0, 150.0),
    "basal_metabolic_rate_kcal": (500.0, 5000.0),
    "visceral_fat_level": (1.0, 30.0),
    "segmental_lean.left_arm_kg": (0.5, 15.0),
    "segmental_lean.right_arm_kg": (0.5, 15.0),
    "segmental_lean.left_leg_kg": (1.0, 35.0),
    "segmental_lean.right_leg_kg": (1.0, 35.0),
    "segmental_lean.trunk_kg": (5.0, 100.0),
}

FIELD_UNITS: dict[str, set[str]] = {
    "weight_kg": {"kg", "kg."},
    "lean_body_mass_kg": {"kg", "kg."},
    "percent_body_fat": {"%", "percent", "pct"},
    "skeletal_muscle_mass_kg": {"kg", "kg."},
    "basal_metabolic_rate_kcal": {"kcal", "cal", "calories", "kcal."},
    "visceral_fat_level": {"level", "lvl", ""},
    "segmental_lean.left_arm_kg": {"kg", "kg."},
    "segmental_lean.right_arm_kg": {"kg", "kg."},
    "segmental_lean.left_leg_kg": {"kg", "kg."},
    "segmental_lean.right_leg_kg": {"kg", "kg."},
    "segmental_lean.trunk_kg": {"kg", "kg."},
}

FIELD_LABELS: dict[str, str] = {
    "weight_kg": "Weight",
    "lean_body_mass_kg": "Lean Body Mass",
    "percent_body_fat": "Percent Body Fat",
    "skeletal_muscle_mass_kg": "Skeletal Muscle Mass",
    "basal_metabolic_rate_kcal": "Basal Metabolic Rate",
    "visceral_fat_level": "Visceral Fat Level",
    "segmental_lean.left_arm_kg": "Left Arm",
    "segmental_lean.right_arm_kg": "Right Arm",
    "segmental_lean.left_leg_kg": "Left Leg",
    "segmental_lean.right_leg_kg": "Right Leg",
    "segmental_lean.trunk_kg": "Trunk",
}


class CorrectionValue(BaseModel):
    """A value typed by a human to correct or fill an unread field."""

    value: float
    unit: str | None = None


class UnreadFieldsError(ValueError):
    """Raised when one or more required fields remain unread/unfilled."""

    def __init__(self, unread_fields: list[str]):
        self.unread_fields = unread_fields
        super().__init__(
            f"Building a plan is impossible while required fields remain unread: {', '.join(unread_fields)}"
        )


def coerce_correction(val: float | int | CorrectionValue | dict[str, Any]) -> CorrectionValue:
    """Coerce various input shapes to a CorrectionValue."""
    if isinstance(val, CorrectionValue):
        return val
    if isinstance(val, (int, float)):
        return CorrectionValue(value=float(val))
    if isinstance(val, dict):
        return CorrectionValue(value=float(val["value"]), unit=val.get("unit"))
    raise TypeError(f"Cannot coerce {type(val)} to CorrectionValue")


def validate_correction(field: str, correction: CorrectionValue) -> None:
    """Validate a single field's value for plausible range and unit."""
    label = FIELD_LABELS.get(field, field)
    if field not in FIELD_RANGES:
        raise ValueError(f"Unknown field '{field}'")

    # Unit validation
    if correction.unit is not None:
        unit_str = correction.unit.strip().lower()
        allowed_units = FIELD_UNITS[field]
        if unit_str not in allowed_units:
            expected = next(iter(allowed_units)) or "none"
            raise ValueError(
                f"Invalid unit '{correction.unit}' for {label} (expected '{expected}')"
            )

    # Range validation
    min_val, max_val = FIELD_RANGES[field]
    if not (min_val <= correction.value <= max_val):
        unit_suffix = f" {next(iter(FIELD_UNITS[field]))}" if next(iter(FIELD_UNITS[field])) else ""
        raise ValueError(
            f"{label} value {correction.value} is out of plausible range ({min_val} - {max_val}{unit_suffix})"
        )

    # Integer requirement for visceral fat
    if field == "visceral_fat_level":
        if not correction.value.is_integer():
            raise ValueError("Visceral Fat Level must be an integer")


def flatten_corrections(
    corrections: dict[str, float | int | CorrectionValue | dict[str, Any]]
) -> dict[str, CorrectionValue]:
    """Flatten nested dicts (e.g. segmental_lean dict) into dotted notation."""
    flattened: dict[str, CorrectionValue] = {}
    for k, v in corrections.items():
        if k == "segmental_lean" and isinstance(v, dict):
            for sub_k, sub_v in v.items():
                dotted = f"segmental_lean.{sub_k}"
                flattened[dotted] = coerce_correction(sub_v)
        else:
            flattened[k] = coerce_correction(v)
    return flattened


def apply_corrections(
    measured: PartialInBody,
    corrections: dict[str, float | int | CorrectionValue | dict[str, Any]],
    source_device: Literal["inbody_270", "inbody_570"] = "inbody_270",
) -> tuple[InBodyPayload, list[str]]:
    """Validate and apply human corrections over a measured PartialInBody.

    Returns (InBodyPayload, corrected_field_names).
    Does NOT mutate the original measured object.
    Raises ValueError if any correction is out-of-range or wrong-unit,
    or if cross-field physiological plausibility fails.
    Raises UnreadFieldsError if any required field is still unread (None).
    """
    flat = flatten_corrections(corrections)

    # Validate each correction individually
    for field, corr in flat.items():
        validate_correction(field, corr)

    # Build effective payload dictionary starting from measured
    data = measured.model_dump()

    # Apply corrections onto a copy of the data
    corrected_keys: list[str] = []
    for field, corr in flat.items():
        corrected_keys.append(field)
        val = int(corr.value) if field == "visceral_fat_level" else corr.value
        if field.startswith("segmental_lean."):
            sub = field.split(".", 1)[1]
            if data.get("segmental_lean") is None:
                data["segmental_lean"] = {}
            data["segmental_lean"][sub] = val
        else:
            data[field] = val

    if data.get("source_device") is None:
        data["source_device"] = source_device

    # Cross-check physiological plausibility
    weight = data.get("weight_kg")
    lbm = data.get("lean_body_mass_kg")
    smm = data.get("skeletal_muscle_mass_kg")

    if weight is not None and lbm is not None and lbm > weight:
        raise ValueError("Lean Body Mass cannot exceed total Weight")
    if lbm is not None and smm is not None and smm > lbm:
        raise ValueError("Skeletal Muscle Mass cannot exceed Lean Body Mass")

    # Check for any remaining unread required fields
    remaining_unread: list[str] = []
    for dotted in REQUIRED_DOTTED_FIELDS:
        if dotted.startswith("segmental_lean."):
            sub = dotted.split(".", 1)[1]
            seg = data.get("segmental_lean")
            if seg is None or seg.get(sub) is None:
                remaining_unread.append(dotted)
        else:
            if data.get(dotted) is None:
                remaining_unread.append(dotted)

    if remaining_unread:
        raise UnreadFieldsError(remaining_unread)

    # Build validated InBodyPayload
    payload = InBodyPayload.model_validate(data)
    return payload, sorted(corrected_keys)
