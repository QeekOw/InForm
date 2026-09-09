"""Score an engine against the hand-labelled real-photo hold-out (ADR-0006).

ADR-0006 asks for two ground-truth sources: the synthetic set, where every value
is known by construction (ADR-0007), and a small real-photo hold-out
hand-labelled off the printouts as the honest test of the synthetic->real gap.
`inform.evaluate` covers the first. This covers the second, which differs in two
ways that make it a sibling scorer rather than a flag on `evaluate()`:

* **Truth is partial.** A person reads a dozen fields off a photo, not the whole
  schema. An unlabelled field is *unknown*, not wrong, so it leaves the
  denominator instead of scoring zero. `evaluate()` cannot express that: there,
  a None expectation means "legitimately absent on this device" (ADR-0004's
  visceral fat on a 270) and scores as a match.
* **Not every sheet is labelled.** A refused sheet produced no read to check by
  hand, so it has no ground truth at all. The outcome split (usable / flagged /
  unread / refused) needs none and is reported over every sheet -- it is the one
  real-photo number that is free.

Match semantics are imported from `inform.evaluate`, so "correct" means the same
thing here as on the synthetic set: within +/-0.1 unit, plus a 1% relative bound
on segmental limbs, and equality for categorical fields. Comparability between
the two sources is the whole point of the protocol.

    python -m inform.holdout --data-dir data/real_holdout \\
        --labels data/real_holdout/labels.json --donut-checkpoint <ckpt>

`--reads` scores a recorded read file (image name -> PartialInBody) instead of
running a model, so a published baseline stays reproducible on any machine
without the checkpoint or a GPU.

Real hold-out sheets and their labels are one consenting subject's health
records. They live outside the repo under `data/` (gitignored) and must not be
committed. The labels file is a JSON object keyed by image stem, holding the
schema's own field names; keys beginning with "_" are provenance notes and are
ignored:

    {
      "_note": "hand-read off the printouts, 2026-09-09",
      "sheet_05": {"weight_kg": 85.5, "segmental_lean": {"right_arm_kg": 3.68}},
      "_unlabelled": ["sheet_01"]
    }
"""
import argparse
import json
from pathlib import Path
from typing import Callable

from pydantic import BaseModel

from inform.errors import InBodyExtractionError
from inform.evaluate import (
    CATEGORICAL_FIELDS,
    IMAGE_SUFFIXES,
    numeric_matches,
    segmental_matches,
)
from inform.inbody import (
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    SEGMENTAL_FIELDS,
    InBodyExtraction,
    PartialInBody,
    partial_field_value,
)

# Every field a hand label may carry. Required and optional scalars plus the
# dotted segmental limbs, in schema declaration order, so adding a field to
# InBodyPayload flows here without hand-editing (as in inform.evaluate).
_SEGMENTAL_DOTTED = tuple(f"segmental_lean.{f}" for f in SEGMENTAL_FIELDS)
SCORED_FIELDS: tuple[str, ...] = REQUIRED_FIELDS + OPTIONAL_FIELDS + _SEGMENTAL_DOTTED

# The buckets a real sheet's read falls into, in order of decreasing usefulness.
# `unread` is an incomplete read that no cross-check objected to; `flagged`
# outranks it because a cross-check breach is the stronger signal.
_OUTCOMES = ("usable", "flagged", "unread", "refused")

Holdout = list[tuple[Path, PartialInBody | None]]


class Score(BaseModel):
    """Matches over labelled opportunities. `labelled` is the denominator, so a
    field nobody hand-read reads 0/0 rather than 0%."""

    matched: int
    labelled: int

    @property
    def accuracy(self) -> float:
        return self.matched / self.labelled if self.labelled else 0.0

    def __str__(self) -> str:
        return f"{self.matched}/{self.labelled}"


class HoldoutReport(BaseModel):
    n_sheets: int
    n_labelled: int
    outcome_split: dict[str, int]
    per_field: dict[str, Score]
    core: Score
    segmental: Score


def load_labels(labels_path: Path) -> dict[str, PartialInBody]:
    """Read the hand-label file into partial payloads keyed by image stem."""
    raw = json.loads(Path(labels_path).read_text(encoding="utf-8"))
    return {
        stem: PartialInBody.model_validate(fields)
        for stem, fields in raw.items()
        if not stem.startswith("_")
    }


def load_holdout(data_dir: Path, labels_path: Path) -> Holdout:
    """Pair every hold-out image with its hand label, or None when unlabelled.

    Unlabelled sheets are kept deliberately: they carry the outcome split even
    though they cannot be scored per-field.
    """
    labels = load_labels(labels_path)
    images = sorted(
        p for p in Path(data_dir).glob("*") if p.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        raise ValueError(f"No hold-out images ({', '.join(IMAGE_SUFFIXES)}) found in {data_dir}")
    unknown = set(labels) - {p.stem for p in images}
    if unknown:
        raise ValueError(
            f"Labels name sheets with no image in {data_dir}: {', '.join(sorted(unknown))}"
        )
    return [(image, labels.get(image.stem)) for image in images]


def replay_engine(reads_path: Path) -> Callable[[Path], PartialInBody]:
    """An Engine that replays recorded reads, keyed by image name or stem.

    Scoring a checkpoint means loading it and running inference; scoring a
    *recorded* run means neither. That is what keeps a published baseline
    checkable after the checkpoint itself has moved on.
    """
    reads = json.loads(Path(reads_path).read_text(encoding="utf-8"))

    def engine(image_path: Path) -> PartialInBody:
        for key in (image_path.name, image_path.stem):
            if key in reads:
                return PartialInBody.model_validate(reads[key])
        raise KeyError(f"{reads_path} has no recorded read for {image_path.name}")

    return engine


def score(
    extractor: Callable[[Path], InBodyExtraction], holdout: Holdout
) -> HoldoutReport:
    """Score `extractor` against partial hand labels, plus the outcome split.

    Per-field accuracy counts only labelled fields on labelled sheets. A refusal
    or an unread field on a labelled sheet scores wrong -- otherwise a
    checkpoint that reads nothing would score perfectly.
    """
    matched = dict.fromkeys(SCORED_FIELDS, 0)
    labelled = dict.fromkeys(SCORED_FIELDS, 0)
    outcomes = dict.fromkeys(_OUTCOMES, 0)

    for image_path, label in holdout:
        try:
            result = extractor(image_path)
        except InBodyExtractionError:
            outcomes["refused"] += 1
            result = None
        else:
            outcomes[_outcome(result)] += 1

        if label is None:
            continue
        for field in SCORED_FIELDS:
            expected = partial_field_value(label, field)
            if expected is None:  # not hand-read: unknown, not wrong
                continue
            labelled[field] += 1
            predicted = None if result is None else partial_field_value(result.data, field)
            if _matches(field, predicted, expected):
                matched[field] += 1

    return HoldoutReport(
        n_sheets=len(holdout),
        n_labelled=sum(1 for _, label in holdout if label is not None),
        outcome_split=outcomes,
        per_field={f: Score(matched=matched[f], labelled=labelled[f]) for f in SCORED_FIELDS},
        core=_total(matched, labelled, [f for f in SCORED_FIELDS if f not in _SEGMENTAL_DOTTED]),
        segmental=_total(matched, labelled, _SEGMENTAL_DOTTED),
    )


def _outcome(result: InBodyExtraction) -> str:
    if result.flagged:
        return "flagged"
    if result.unread:
        return "unread"
    return "usable"


def _matches(field: str, predicted, expected) -> bool:
    if predicted is None:
        return False  # unread against a known value is a miss, not a pass
    if field in CATEGORICAL_FIELDS:
        return predicted == expected
    if field in _SEGMENTAL_DOTTED:
        return segmental_matches(predicted, expected)
    return numeric_matches(predicted, expected)


def _total(matched: dict[str, int], labelled: dict[str, int], fields) -> Score:
    return Score(
        matched=sum(matched[f] for f in fields), labelled=sum(labelled[f] for f in fields)
    )


def format_report(report: HoldoutReport) -> str:
    width = max(len(f) for f in SCORED_FIELDS) + 2
    lines = [f"{report.n_sheets} sheets, {report.n_labelled} hand-labelled", ""]

    lines.append("outcome split (needs no labels)")
    for outcome in _OUTCOMES:
        lines.append(f"  {outcome.ljust(width - 2)}{report.outcome_split[outcome]:>8}")
    lines += ["", "per-field accuracy (labelled sheets only)"]

    for field in SCORED_FIELDS:
        entry = report.per_field[field]
        rate = "     --" if not entry.labelled else f"{entry.accuracy:6.1%}"
        lines.append(f"  {field.ljust(width)}{str(entry):>8}{rate:>9}")

    lines.append("  " + "-" * (width + 16))
    for name, entry in (("core fields", report.core), ("segmental lean", report.segmental)):
        rate = "     --" if not entry.labelled else f"{entry.accuracy:6.1%}"
        lines.append(f"  {name.ljust(width)}{str(entry):>8}{rate:>9}")
    return "\n".join(lines)


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data-dir", type=Path, required=True, help="Hold-out images")
    parser.add_argument("--labels", type=Path, required=True, help="Hand-label JSON")
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--donut-checkpoint",
        type=Path,
        help="Checkpoint to score; omit to use the default engine (ADR-0010)",
    )
    source.add_argument(
        "--reads", type=Path, help="Score a recorded read file instead of running a model"
    )
    args = parser.parse_args()

    from functools import partial

    from inform.extract import extract_inbody

    engine = None
    if args.reads is not None:
        engine = replay_engine(args.reads)
    elif args.donut_checkpoint is not None:
        from inform.engines import donut

        engine = donut.load_engine(args.donut_checkpoint)

    holdout = load_holdout(args.data_dir, args.labels)
    print(format_report(score(partial(extract_inbody, engine=engine), holdout)))


if __name__ == "__main__":
    _main()
