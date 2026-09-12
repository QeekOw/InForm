import os
from pathlib import Path
from typing import Callable

from inform.engines import donut
from inform.errors import DonutCheckpointError, MissingRequiredFieldsError
from inform.formulas import katch_mcardle_bmr
from inform.inbody import (
    REQUIRED_DOTTED_FIELDS,
    InBodyExtraction,
    PartialInBody,
    partial_field_value,
)

Engine = Callable[[Path], PartialInBody]

# ponytail: fixed calibration knobs, not learned. Tune against real
# misread cases if the gate proves too tight/loose in practice.
_LBM_TOLERANCE_KG = 2.0
_BMR_TOLERANCE_KCAL = 100.0

# Where the default (Donut) engine finds its fine-tuned checkpoint (ADR-0010).
# A local checkpoint dir, defaulting to the Kaggle output folder name so a local
# download works without extra config. (Hub-id support is a future option; it
# needs the loader to stop Path-wrapping, which mangles "org/name" on Windows.)
_DONUT_CKPT_ENV = "INFORM_DONUT_CKPT"
_DEFAULT_DONUT_CKPT = "models/donut-both-v5"


def default_engine() -> Engine:
    """Build the default runtime engine: self-hosted Donut (ADR-0010).

    Points at INFORM_DONUT_CKPT (default `models/donut-both-v5`). Fails loudly
    (DonutCheckpointError) when the checkpoint is absent or the training extra
    (torch/transformers) is not installed. It never silently falls back to the
    cloud VLM, which ADR-0005 forbids from ever seeing real PHI. The VLM remains
    reachable only as an explicitly-passed engine (the eval oracle).
    """
    ckpt = Path(os.environ.get(_DONUT_CKPT_ENV, _DEFAULT_DONUT_CKPT))
    # The local checkpoint dir must exist before we hand it to the (heavy)
    # loader; a missing dir fails loudly rather than silently using the VLM.
    if not ckpt.exists():
        raise DonutCheckpointError(ckpt)
    try:
        return donut.load_engine(ckpt)
    except ImportError as exc:  # torch/transformers absent (the training extra)
        raise DonutCheckpointError(ckpt, missing_training_extra=True) from exc


def extract_inbody(image_path: Path, engine: Engine | None = None) -> InBodyExtraction:
    """The single production seam: image in, InBodyExtraction out.

    Partial extraction (ADR-0008 amended): return every field the engine read,
    plus the required fields it could not (`unread`) and the fields a cross-check
    found suspect (`flagged`). Never fabricates — unread carry no value, flagged
    are real reads marked low-confidence. Two hard-reject paths remain: the
    engine raises NotAnInBodySheetError for a non-sheet, and this seam raises
    MissingRequiredFieldsError when *nothing* readable came back (the floor case).

    `engine` defaults to the self-hosted Donut engine (ADR-0010); the VLM is
    reachable only by passing it explicitly (the eval oracle).
    """
    if engine is None:
        engine = default_engine()
    partial = engine(image_path)
    unread = [f for f in REQUIRED_DOTTED_FIELDS if partial_field_value(partial, f) is None]
    if len(unread) == len(REQUIRED_DOTTED_FIELDS):
        raise MissingRequiredFieldsError(unread)
    flagged = _cross_check(partial)
    return InBodyExtraction(data=partial, unread=unread, flagged=flagged)


def _cross_check(payload: PartialInBody) -> list[str]:
    """Return the fields implicated by a failed cross-check (ADR-0003), or [].

    Each check runs only when its inputs are all present. A breach can't isolate
    the single misread, so every field feeding the check is flagged "verify".
    """
    flagged: list[str] = []

    weight, pbf, lbm = payload.weight_kg, payload.percent_body_fat, payload.lean_body_mass_kg
    if None not in (weight, pbf, lbm):
        derived_lbm = weight * (1 - pbf / 100)
        if abs(lbm - derived_lbm) > _LBM_TOLERANCE_KG:
            flagged += ["weight_kg", "percent_body_fat", "lean_body_mass_kg"]

    bmr = payload.basal_metabolic_rate_kcal
    if None not in (bmr, lbm):
        recomputed_bmr = katch_mcardle_bmr(lbm)
        if abs(bmr - recomputed_bmr) > _BMR_TOLERANCE_KCAL:
            flagged += ["basal_metabolic_rate_kcal", "lean_body_mass_kg"]

    return list(dict.fromkeys(flagged))  # de-dup, preserve order
