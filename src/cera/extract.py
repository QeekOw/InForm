from pathlib import Path
from typing import Callable

from cera.engines import vlm
from cera.errors import MissingRequiredFieldsError
from cera.inbody import (
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


def extract_inbody(image_path: Path, engine: Engine = vlm.extract) -> InBodyExtraction:
    """The single production seam: image in, InBodyExtraction out.

    Partial extraction (ADR-0008 amended): return every field the engine read,
    plus the required fields it could not (`unread`) and the fields a cross-check
    found suspect (`flagged`). Never fabricates — unread carry no value, flagged
    are real reads marked low-confidence. Two hard-reject paths remain: the
    engine raises NotAnInBodySheetError for a non-sheet, and this seam raises
    MissingRequiredFieldsError when *nothing* readable came back (the floor case).
    """
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
        recomputed_bmr = 370 + 21.6 * lbm
        if abs(bmr - recomputed_bmr) > _BMR_TOLERANCE_KCAL:
            flagged += ["basal_metabolic_rate_kcal", "lean_body_mass_kg"]

    return list(dict.fromkeys(flagged))  # de-dup, preserve order
