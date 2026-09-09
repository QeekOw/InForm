from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from inform.errors import InBodyExtractionError
from inform.inbody import (
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    SEGMENTAL_FIELDS,
    InBodyExtraction,
    InBodyPayload,
)

# Image formats a labeled set may hold. Duplicated from
# inform.training.dataset.IMAGE_SUFFIXES so scoring stays importable without the
# training package; tests/test_evaluate.py asserts the two never drift.
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png")

# ponytail: fixed tolerances, not learned. Public because inform.holdout scores
# the real hand-labelled set by the same rules -- ADR-0006's synthetic-vs-real
# gap is only meaningful if "correct" means one thing.
FIELD_TOLERANCE = 0.1

# Segmental limbs need a relative bound as well (ADR-0006, amended). +/-0.1 kg
# is 0.1% of an 85 kg weight but 2.9% of a 3.5 kg arm, and exercise_filter
# fires on a bilateral asymmetry above 5%: a limb read that passes a 2.9% check
# can still fabricate the imbalance the user is shown. At 1% per limb the
# induced asymmetry error stays near 2 points, well inside the 5-point trigger.
SEGMENTAL_RELATIVE_TOLERANCE = 0.01

# Field names come from the schema (inform.inbody); only their *match semantics*
# are an eval concern: categorical fields compare by equality, numeric ones by
# tolerance. Optional fields (per ADR-0004/0009, absent only on some configs)
# are reported per-field but excluded from whole_sheet_accuracy, which gates on required
# fields only (ADR-0006: "% of sheets with every required field correct").
CATEGORICAL_FIELDS = ("source_device",)
_REQUIRED_NUMERIC_FIELDS = tuple(f for f in REQUIRED_FIELDS if f not in CATEGORICAL_FIELDS)
_OPTIONAL_NUMERIC_FIELDS = OPTIONAL_FIELDS
_SEGMENTAL_FIELDS = SEGMENTAL_FIELDS
_CRITICAL_FIELDS = ("lean_body_mass_kg",) + tuple(f"segmental_lean.{f}" for f in _SEGMENTAL_FIELDS)

LabeledSet = list[tuple[Path, InBodyPayload]]


class AccuracyReport(BaseModel):
    n_sheets: int
    per_field_accuracy: dict[str, float]
    critical_field_accuracy: dict[str, float]
    whole_sheet_accuracy: float


def load_labeled_set(data_dir: Path) -> LabeledSet:
    """Read a generate_dataset() output dir (image + ground-truth json pairs)
    into a LabeledSet — the held-out set an engine is scored against."""
    pairs: LabeledSet = []
    images = (p for p in Path(data_dir).glob("*") if p.suffix.lower() in IMAGE_SUFFIXES)
    for image_path in sorted(images):
        expected = InBodyPayload.model_validate_json(
            image_path.with_suffix(".json").read_text(encoding="utf-8")
        )
        pairs.append((image_path, expected))
    if not pairs:
        raise ValueError(f"No labeled image/.json pairs found in {data_dir}")
    return pairs


def evaluate(
    extractor: Callable[[Path], InBodyExtraction], labeled_set: LabeledSet
) -> AccuracyReport:
    """Score `extractor` against known ground truth (ADR-0006).

    `extractor` returns an InBodyExtraction (ADR-0008 amended: partial reads).
    Exact numeric accuracy, not text similarity: a field counts as correct only
    within +/-0.1 unit of ground truth. Partial reads are credited per field —
    each field read AND correct scores, so a partially-read sheet no longer
    zeroes its good fields. `whole_sheet` requires every required field read and
    correct AND no cross-check flags. `labeled_set` is homogeneous — call once
    per ground-truth source (synthetic, real hold-out) and report separately.
    """
    all_fields = _REQUIRED_NUMERIC_FIELDS + _OPTIONAL_NUMERIC_FIELDS + CATEGORICAL_FIELDS
    field_matches: dict[str, list[bool]] = {field: [] for field in all_fields}
    for field in _SEGMENTAL_FIELDS:
        field_matches[f"segmental_lean.{field}"] = []
    whole_sheet_matches: list[bool] = []

    for image_path, expected in labeled_set:
        try:
            result = extractor(image_path)
        except InBodyExtractionError:
            # A hard reject (non-InBody input, or the floor case where nothing
            # readable came back) reads no value, so every required and
            # segmental field scores wrong. The OPTIONAL visceral field is
            # scored against truth the same way as on the success path: a reject
            # on a 270 (truth None) is not a visceral miss (ADR-0004; matches
            # numeric_matches(None, None)).
            for field in field_matches:
                if field in _OPTIONAL_NUMERIC_FIELDS:
                    field_matches[field].append(numeric_matches(None, getattr(expected, field)))
                else:
                    field_matches[field].append(False)
            whole_sheet_matches.append(False)
            continue

        predicted = result.data  # PartialInBody: unread fields are None
        sheet_matches: list[bool] = []

        for field in _REQUIRED_NUMERIC_FIELDS:
            match = numeric_matches(getattr(predicted, field), getattr(expected, field))
            field_matches[field].append(match)
            sheet_matches.append(match)

        for field in _OPTIONAL_NUMERIC_FIELDS:
            match = numeric_matches(getattr(predicted, field), getattr(expected, field))
            field_matches[field].append(match)

        for field in CATEGORICAL_FIELDS:
            match = getattr(predicted, field) == getattr(expected, field)
            field_matches[field].append(match)
            sheet_matches.append(match)

        for field in _SEGMENTAL_FIELDS:
            predicted_value = (
                None if predicted.segmental_lean is None
                else getattr(predicted.segmental_lean, field)
            )
            match = segmental_matches(predicted_value, getattr(expected.segmental_lean, field))
            field_matches[f"segmental_lean.{field}"].append(match)
            sheet_matches.append(match)

        # A flagged (cross-check-suspect) sheet is never a whole-sheet success,
        # even if the flagged values happen to match truth.
        whole_sheet_matches.append(all(sheet_matches) and not result.flagged)

    per_field_accuracy = {field: _match_rate(matches) for field, matches in field_matches.items()}
    return AccuracyReport(
        n_sheets=len(labeled_set),
        per_field_accuracy=per_field_accuracy,
        critical_field_accuracy={field: per_field_accuracy[field] for field in _CRITICAL_FIELDS},
        whole_sheet_accuracy=_match_rate(whole_sheet_matches),
    )


def segmental_matches(predicted: float | None, expected: float | None) -> bool:
    """Correct within *both* the absolute and the relative bound (ADR-0006).

    A limb spans an order of magnitude on one sheet -- a 3.5 kg arm beside a
    28 kg trunk -- so a single absolute tolerance is either useless on the arm
    or unreachable on the trunk. Requiring both means whichever is tighter at
    that magnitude binds. See SEGMENTAL_RELATIVE_TOLERANCE.
    """
    if not numeric_matches(predicted, expected):
        return False
    if expected is None or predicted is None or expected == 0:
        return True  # absence, and the degenerate case, settled by the line above
    return abs(predicted - expected) / abs(expected) <= SEGMENTAL_RELATIVE_TOLERANCE


def numeric_matches(predicted: float | int | None, expected: float | int | None) -> bool:
    """Exact within tolerance (ADR-0006). Note the None semantics: here a None
    expectation means the field is legitimately absent on this device
    (ADR-0004), so an unread None *matches* it. inform.holdout, where a None
    label instead means nobody hand-read the field, filters those out before
    calling this."""
    if expected is None or predicted is None:
        return predicted == expected
    return abs(predicted - expected) <= FIELD_TOLERANCE


def _match_rate(matches: list[bool]) -> float:
    return sum(matches) / len(matches) if matches else 0.0
