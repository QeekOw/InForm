from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from cera.inbody import InBodyPayload

# ponytail: fixed tolerance, not learned. Matches ADR-0006's default.
_FIELD_TOLERANCE = 0.1

_REQUIRED_NUMERIC_FIELDS = (
    "weight_kg",
    "lean_body_mass_kg",
    "percent_body_fat",
    "skeletal_muscle_mass_kg",
    "basal_metabolic_rate_kcal",
)
# Optional per ADR-0004 (absent on the InBody 270) — reported per-field but
# excluded from whole_sheet_accuracy, which only gates on required fields
# (ADR-0006: "% of sheets with every required field correct").
_OPTIONAL_NUMERIC_FIELDS = ("visceral_fat_level",)
_CATEGORICAL_FIELDS = ("source_device",)
_SEGMENTAL_FIELDS = ("left_arm_kg", "right_arm_kg", "left_leg_kg", "right_leg_kg", "trunk_kg")
_CRITICAL_FIELDS = ("lean_body_mass_kg",) + tuple(f"segmental_lean.{f}" for f in _SEGMENTAL_FIELDS)

LabeledSet = list[tuple[Path, InBodyPayload]]


class AccuracyReport(BaseModel):
    n_sheets: int
    per_field_accuracy: dict[str, float]
    critical_field_accuracy: dict[str, float]
    whole_sheet_accuracy: float


def evaluate(engine: Callable[[Path], InBodyPayload], labeled_set: LabeledSet) -> AccuracyReport:
    """Score `engine` against known ground truth (ADR-0006).

    Exact numeric accuracy, not text similarity: a field counts as correct
    only within +/-0.1 unit of ground truth. `labeled_set` is homogeneous —
    call this once per ground-truth source (synthetic, real hold-out) and
    report the two separately, per ADR-0006's dual-ground-truth protocol.
    """
    all_fields = _REQUIRED_NUMERIC_FIELDS + _OPTIONAL_NUMERIC_FIELDS + _CATEGORICAL_FIELDS
    field_matches: dict[str, list[bool]] = {field: [] for field in all_fields}
    for field in _SEGMENTAL_FIELDS:
        field_matches[f"segmental_lean.{field}"] = []
    whole_sheet_matches: list[bool] = []

    for image_path, expected in labeled_set:
        predicted = engine(image_path)
        sheet_matches: list[bool] = []

        for field in _REQUIRED_NUMERIC_FIELDS:
            match = _numeric_matches(getattr(predicted, field), getattr(expected, field))
            field_matches[field].append(match)
            sheet_matches.append(match)

        for field in _OPTIONAL_NUMERIC_FIELDS:
            match = _numeric_matches(getattr(predicted, field), getattr(expected, field))
            field_matches[field].append(match)

        for field in _CATEGORICAL_FIELDS:
            match = getattr(predicted, field) == getattr(expected, field)
            field_matches[field].append(match)
            sheet_matches.append(match)

        for field in _SEGMENTAL_FIELDS:
            match = _numeric_matches(
                getattr(predicted.segmental_lean, field), getattr(expected.segmental_lean, field)
            )
            field_matches[f"segmental_lean.{field}"].append(match)
            sheet_matches.append(match)

        whole_sheet_matches.append(all(sheet_matches))

    per_field_accuracy = {field: _match_rate(matches) for field, matches in field_matches.items()}
    return AccuracyReport(
        n_sheets=len(labeled_set),
        per_field_accuracy=per_field_accuracy,
        critical_field_accuracy={field: per_field_accuracy[field] for field in _CRITICAL_FIELDS},
        whole_sheet_accuracy=_match_rate(whole_sheet_matches),
    )


def _numeric_matches(predicted: float | int | None, expected: float | int | None) -> bool:
    if expected is None or predicted is None:
        return predicted == expected
    return abs(predicted - expected) <= _FIELD_TOLERANCE


def _match_rate(matches: list[bool]) -> float:
    return sum(matches) / len(matches) if matches else 0.0
