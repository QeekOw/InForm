"""Plausible range and unit validation, and correction application for InBody fields.

Enforces ADR-0008: fail-closed posture remains intact. A person can supply
values for unread fields off the sheet in hand, or correct misread fields,
but values are strictly validated for plausible physiological ranges and
units to prevent slipped decimals or wrong units from producing a nonsense plan.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field

from inform.extract import _cross_check
from inform.inbody import (
    REQUIRED_DOTTED_FIELDS,
    InBodyPayload,
    PartialInBody,
    PartialSegmentalLean,
    SegmentalLean,
)


class FieldSpec(BaseModel):
    """Clinical / physiological constraints and metadata for an InBody field."""

    label: str
    min_value: float
    max_value: float
    allowed_units: set[str]
    is_integer: bool = False


# Unified field specifications avoiding data clumps (Refactoring Ch. 3)
FIELD_SPECS: dict[str, FieldSpec] = {
    "weight_kg": FieldSpec(
        label="Weight",
        min_value=20.0,
        max_value=300.0,
        allowed_units={"kg", "kg."},
    ),
    "lean_body_mass_kg": FieldSpec(
        label="Lean Body Mass",
        min_value=10.0,
        max_value=250.0,
        allowed_units={"kg", "kg."},
    ),
    "percent_body_fat": FieldSpec(
        label="Percent Body Fat",
        min_value=3.0,
        max_value=75.0,
        allowed_units={"%", "percent", "pct"},
    ),
    "skeletal_muscle_mass_kg": FieldSpec(
        label="Skeletal Muscle Mass",
        min_value=5.0,
        max_value=150.0,
        allowed_units={"kg", "kg."},
    ),
    "basal_metabolic_rate_kcal": FieldSpec(
        label="Basal Metabolic Rate",
        min_value=500.0,
        max_value=5000.0,
        allowed_units={"kcal", "cal", "calories", "kcal."},
    ),
    "visceral_fat_level": FieldSpec(
        label="Visceral Fat Level",
        min_value=1.0,
        max_value=30.0,
        allowed_units={"level", "lvl", ""},
        is_integer=True,
    ),
    "segmental_lean.left_arm_kg": FieldSpec(
        label="Left Arm",
        min_value=0.5,
        max_value=15.0,
        allowed_units={"kg", "kg."},
    ),
    "segmental_lean.right_arm_kg": FieldSpec(
        label="Right Arm",
        min_value=0.5,
        max_value=15.0,
        allowed_units={"kg", "kg."},
    ),
    "segmental_lean.left_leg_kg": FieldSpec(
        label="Left Leg",
        min_value=1.0,
        max_value=35.0,
        allowed_units={"kg", "kg."},
    ),
    "segmental_lean.right_leg_kg": FieldSpec(
        label="Right Leg",
        min_value=1.0,
        max_value=35.0,
        allowed_units={"kg", "kg."},
    ),
    "segmental_lean.trunk_kg": FieldSpec(
        label="Trunk",
        min_value=5.0,
        max_value=100.0,
        allowed_units={"kg", "kg."},
    ),
}

# Backward-compatibility projections
FIELD_RANGES: dict[str, tuple[float, float]] = {
    k: (spec.min_value, spec.max_value) for k, spec in FIELD_SPECS.items()
}
FIELD_UNITS: dict[str, set[str]] = {k: spec.allowed_units for k, spec in FIELD_SPECS.items()}
FIELD_LABELS: dict[str, str] = {k: spec.label for k, spec in FIELD_SPECS.items()}


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


class CrossCheckFlaggedError(ValueError):
    """Raised when ADR-0008 §2 cross-check gate fails on the effective reading."""

    def __init__(self, flagged_fields: list[str]):
        self.flagged_fields = flagged_fields
        super().__init__(
            f"Cross-check failed for fields: {', '.join(flagged_fields)}. Please verify or correct these values."
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
    spec = FIELD_SPECS.get(field)
    if not spec:
        raise ValueError(f"Unknown field '{field}'")

    # Unit validation
    if correction.unit is not None:
        unit_str = correction.unit.strip().lower()
        if unit_str not in spec.allowed_units:
            expected = next(iter(spec.allowed_units)) or "none"
            raise ValueError(
                f"Invalid unit '{correction.unit}' for {spec.label} (expected '{expected}')"
            )

    # Range validation
    if not (spec.min_value <= correction.value <= spec.max_value):
        unit_suffix = f" {next(iter(spec.allowed_units))}" if next(iter(spec.allowed_units)) else ""
        raise ValueError(
            f"{spec.label} value {correction.value} is out of plausible range ({spec.min_value} - {spec.max_value}{unit_suffix})"
        )

    # Integer requirement
    if spec.is_integer and not correction.value.is_integer():
        raise ValueError(f"{spec.label} must be an integer")


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
    source_device: Literal["inbody_270", "inbody_570"] | None = None,
    confirmed_fields: set[str] | None = None,
) -> tuple[InBodyPayload, list[str]]:
    """Validate and apply human corrections over a measured PartialInBody.

    Returns (InBodyPayload, corrected_field_names).
    Does NOT mutate the original measured object.
    Raises ValueError if any correction is out-of-range or wrong-unit.
    Raises CrossCheckFlaggedError if ADR-0008 §2 cross-check gate fails and
    the person has not explicitly confirmed the remaining flagged fields.
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

    # Resolve source device: never guess or fabricate (ADR-0008 §1)
    effective_device = data.get("source_device") or source_device
    if effective_device is not None:
        data["source_device"] = effective_device

    # Physiological boundary check
    weight = data.get("weight_kg")
    lbm = data.get("lean_body_mass_kg")
    if weight is not None and lbm is not None and lbm > weight:
        raise ValueError("Lean Body Mass cannot exceed total Weight")

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

    if data.get("source_device") is None:
        remaining_unread.append("source_device")

    if remaining_unread:
        raise UnreadFieldsError(sorted(dict.fromkeys(remaining_unread)))

    # ADR-0008 §2: Re-run cross-check gate on the effective reading
    effective_partial = PartialInBody.model_validate(data)
    remaining_flags = _cross_check(effective_partial)
    unresolved_flags = [
        field for field in remaining_flags if field not in (confirmed_fields or set())
    ]
    if unresolved_flags:
        raise CrossCheckFlaggedError(unresolved_flags)

    # Build validated InBodyPayload
    payload = InBodyPayload.model_validate(data)
    return payload, sorted(corrected_keys)
