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
  hand, so it has no ground truth at all. The outcome split (unverified /
  flagged / unread / refused) needs none and is reported over every sheet -- it
  is the one real-photo number that is free.

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
from typing import Callable, Iterable

from pydantic import BaseModel

from inform.errors import InBodyExtractionError
from inform.evaluate import (
    CATEGORICAL_FIELDS,
    CRITICAL_FIELDS,
    IMAGE_SUFFIXES,
    numeric_matches,
    segmental_matches,
)
from inform.inbody import (
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    SEGMENTAL_DOTTED_FIELDS,
    InBodyExtraction,
    PartialInBody,
    partial_field_value,
)

# Every field a hand label may carry. Required and optional scalars plus the
# dotted segmental limbs, in schema declaration order, so adding a field to
# InBodyPayload flows here without hand-editing (as in inform.evaluate).
SCORED_FIELDS: tuple[str, ...] = REQUIRED_FIELDS + OPTIONAL_FIELDS + SEGMENTAL_DOTTED_FIELDS

# The read outcomes (CONTEXT.md), in order of decreasing usefulness. `unread`
# is an incomplete read that no cross-check objected to; `flagged` outranks it
# because a cross-check breach is the stronger signal. `unverified` is named for
# the risk rather than the hope: the engine has no objection, which is not the
# same as the read being right.
_OUTCOMES = ("unverified", "flagged", "unread", "refused")

Holdout = list[tuple[Path, PartialInBody | None]]


class Score(BaseModel):
    """Matches over labelled opportunities.

    `labelled` is the denominator, so a field nobody hand-read is 0/0 and its
    accuracy is None, not 0.0. Unknown has to be distinguishable from wrong: a
    caller averaging per-field accuracy would otherwise pull the mean down with
    fields that were never read, which is the error the partial-truth
    denominator exists to prevent.
    """

    matched: int
    labelled: int

    @property
    def accuracy(self) -> float | None:
        return self.matched / self.labelled if self.labelled else None

    def __str__(self) -> str:
        return f"{self.matched}/{self.labelled}"


class SilentErrors(BaseModel):
    """Wrong values inside `unverified` reads -- the headline measure of an
    engine (CONTEXT.md, "Read outcomes").

    Every other failure announces itself: a refusal explains itself, a
    `flagged` value asks a person to check that value, an `unread` one asks
    them to supply it. A silent error is the only failure that arrives looking
    like a success, and the only thing standing between it and a plan is a
    person reading a confirmation screen carefully.

    Two cuts, because they answer different questions. `sheets_with_error` over
    `sheets` is the headline: a sheet is what reaches a person, and one wrong
    limb ruins it as surely as five. `field_errors` over `fields` is the
    diagnostic underneath.

    `unmeasurable` is the size of the blind spot, not part of either
    denominator: an `unverified` read of a sheet nobody has hand-labelled
    cannot be checked, and counting it clean would flatter the engine with
    precisely the sheets that carry no ground truth (issue #24). Report it
    beside the rate or the rate is not honest.

    `fields` counts labelled fields on `unverified` sheets only, not every
    labelled field in the set, so `field_rate` shares the headline's
    denominator rather than the per-field table's. The report labels it that
    way; read apart from that label it looks several times too small.
    """

    sheets: int
    sheets_with_error: int
    fields: int
    field_errors: int
    unmeasurable: int

    @property
    def sheet_rate(self) -> float | None:
        return self.sheets_with_error / self.sheets if self.sheets else None

    @property
    def field_rate(self) -> float | None:
        return self.field_errors / self.fields if self.fields else None


class HoldoutReport(BaseModel):
    """The silent-error rate, per-field accuracy over the hand-labelled sheets,
    and the outcome split over all of them.

    There is deliberately no whole-sheet figure. ADR-0006 calls it the headline
    number and defines it as "every required field correct", which this set
    cannot answer: `source_device` is unlabelled on every sheet, so "every
    required field" is not available to check. A whole-sheet number computed
    over labelled fields only would carry the same name as the synthetic one
    with a different denominator, and would invite exactly the comparison
    ADR-0006 exists to make honest. The critical cut is reported instead.

    ADR-0006's headline is superseded in any case: `silent` is what judges an
    engine now, and per-field accuracy is a diagnostic beneath it (CONTEXT.md).
    """

    n_sheets: int
    n_labelled: int
    outcome_split: dict[str, int]
    per_field: dict[str, Score]
    core: Score
    segmental: Score
    critical: Score
    silent: SilentErrors


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
    silent = SilentErrors(sheets=0, sheets_with_error=0, fields=0, field_errors=0, unmeasurable=0)

    for image_path, label in holdout:
        try:
            result = extractor(image_path)
        except InBodyExtractionError:
            outcome, result = "refused", None
        else:
            outcome = _outcome(result)
        outcomes[outcome] += 1

        # A silent error can only live in an `unverified` read, and can only be
        # seen on a labelled sheet. An unlabelled one is the blind spot, not a
        # pass, so it is counted apart from either denominator.
        unverified = outcome == "unverified"
        if unverified and label is None:
            silent.unmeasurable += 1
        elif unverified:
            silent.sheets += 1
        sheet_errors = 0

        if label is None:
            continue
        for field in SCORED_FIELDS:
            expected = partial_field_value(label, field)
            if expected is None:  # not hand-read: unknown, not wrong
                continue
            labelled[field] += 1
            if unverified:
                silent.fields += 1
            predicted = None if result is None else partial_field_value(result.data, field)
            if _matches(field, predicted, expected):
                matched[field] += 1
            elif unverified:
                sheet_errors += 1
        if unverified:
            silent.field_errors += sheet_errors
            silent.sheets_with_error += 1 if sheet_errors else 0

    return HoldoutReport(
        n_sheets=len(holdout),
        n_labelled=sum(1 for _, label in holdout if label is not None),
        outcome_split=outcomes,
        per_field={f: Score(matched=matched[f], labelled=labelled[f]) for f in SCORED_FIELDS},
        core=_total(
            matched, labelled, [f for f in SCORED_FIELDS if f not in SEGMENTAL_DOTTED_FIELDS]
        ),
        segmental=_total(matched, labelled, SEGMENTAL_DOTTED_FIELDS),
        critical=_total(matched, labelled, CRITICAL_FIELDS),
        silent=silent,
    )


def _outcome(result: InBodyExtraction) -> str:
    if result.flagged:
        return "flagged"
    if result.unread:
        return "unread"
    return "unverified"


def _matches(field: str, predicted: float | str | None, expected: float | str) -> bool:
    if predicted is None:
        return False  # unread against a known value is a miss, not a pass
    if field in CATEGORICAL_FIELDS:
        return predicted == expected
    if field in SEGMENTAL_DOTTED_FIELDS:
        return segmental_matches(predicted, expected)
    return numeric_matches(predicted, expected)


def _total(
    matched: dict[str, int], labelled: dict[str, int], fields: Iterable[str]
) -> Score:
    return Score(
        matched=sum(matched[f] for f in fields), labelled=sum(labelled[f] for f in fields)
    )


def format_report(report: HoldoutReport) -> str:
    width = max(len(f) for f in SCORED_FIELDS) + 2
    lines = [f"{report.n_sheets} sheets, {report.n_labelled} hand-labelled", ""]

    lines += _silent_lines(report.silent, width)

    lines.append("outcome split (needs no labels)")
    for outcome in _OUTCOMES:
        lines.append(f"  {outcome.ljust(width - 2)}{report.outcome_split[outcome]:>8}")
    lines += ["", "per-field accuracy (labelled sheets only)"]

    for field in SCORED_FIELDS:
        entry = report.per_field[field]
        lines.append(f"  {field.ljust(width)}{str(entry):>8}{_rate(entry):>9}")

    lines.append("  " + "-" * (width + 16))
    for name, entry in (
        ("core fields", report.core),
        ("segmental lean", report.segmental),
        ("critical (LBM + limbs)", report.critical),
    ):
        lines.append(f"  {name.ljust(width)}{str(entry):>8}{_rate(entry):>9}")
    return "\n".join(lines)


def _silent_lines(silent: SilentErrors, width: int) -> list[str]:
    """The headline, printed as counts first.

    The denominator is small enough that a bare percentage would be read as a
    rate it cannot support, so the raw counts lead and the percentage is
    suppressed entirely when there is nothing to divide by. `unmeasurable` is
    printed unconditionally: a reader who does not see it will mistake the
    blind spot for a clean result.
    """
    sheets = f"{silent.sheets_with_error}/{silent.sheets}"
    fields = f"{silent.field_errors}/{silent.fields}"
    return [
        "silent errors -- wrong values inside unverified reads (headline)",
        f"  {'unverified sheets, >=1 wrong'.ljust(width)}{sheets:>8}{_pct(silent.sheet_rate):>9}",
        f"  {'their fields, wrong'.ljust(width)}{fields:>8}{_pct(silent.field_rate):>9}",
        f"  {'unverified, unlabellable'.ljust(width)}{silent.unmeasurable:>8}"
        "   not measurable",
        "",
    ]


def _pct(rate: float | None) -> str:
    return "     --" if rate is None else f"{rate:6.1%}"


def _rate(entry: Score) -> str:
    return "     --" if entry.accuracy is None else f"{entry.accuracy:6.1%}"


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
