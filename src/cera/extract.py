from pathlib import Path

from cera.engines import vlm
from cera.errors import CrossCheckFailedError
from cera.inbody import InBodyPayload

# ponytail: fixed calibration knobs, not learned. Tune against real
# misread cases if the gate proves too tight/loose in practice.
_LBM_TOLERANCE_KG = 2.0
_BMR_TOLERANCE_KCAL = 100.0


def extract_inbody(image_path: Path) -> InBodyPayload:
    """The single production seam: image in, validated InBodyPayload out.

    Backed by one swappable extraction engine at a time (ADR-0002) —
    currently the VLM baseline. Never fabricates a number: the engine fails
    closed on unreadable fields or non-InBody input, and this seam applies
    the sheet's own redundancy as a cross-check gate (ADR-0003, ADR-0008).
    """
    payload = vlm.extract(image_path)
    _cross_check(payload)
    return payload


def _cross_check(payload: InBodyPayload) -> None:
    derived_lbm = payload.weight_kg * (1 - payload.percent_body_fat / 100)
    if abs(payload.lean_body_mass_kg - derived_lbm) > _LBM_TOLERANCE_KG:
        raise CrossCheckFailedError(
            "lbm_vs_weight_pbf", derived_lbm, payload.lean_body_mass_kg, _LBM_TOLERANCE_KG
        )

    recomputed_bmr = 370 + 21.6 * payload.lean_body_mass_kg
    if abs(payload.basal_metabolic_rate_kcal - recomputed_bmr) > _BMR_TOLERANCE_KCAL:
        raise CrossCheckFailedError(
            "bmr_vs_katch_mcardle",
            recomputed_bmr,
            payload.basal_metabolic_rate_kcal,
            _BMR_TOLERANCE_KCAL,
        )
