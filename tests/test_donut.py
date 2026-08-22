# The Donut engine's model inference needs a GPU + real checkpoint (covered by
# the training smoke test + the Colab run); these tests exercise the parsing
# logic that turns a decoded sequence into a PartialInBody, which is the only
# non-trivial branch and runs without torch. Partial extraction (ADR-0008
# amended): a garbled/incomplete generation yields an empty/partial read (all or
# some fields None), never a fabricated value — the seam decides floor-reject.
import json

from cera.engines.donut import TASK_TOKEN, _to_partial
from cera.inbody import InBodyPayload, PartialInBody

_GOOD = InBodyPayload(
    weight_kg=70.0,
    lean_body_mass_kg=58.0,
    percent_body_fat=17.1,
    skeletal_muscle_mass_kg=33.0,
    basal_metabolic_rate_kcal=1622.8,
    segmental_lean=dict(
        left_arm_kg=3.2, right_arm_kg=3.3, left_leg_kg=8.1, right_leg_kg=8.2, trunk_kg=24.5
    ),
    source_device="inbody_570",
)
_GOOD_PARTIAL = PartialInBody.model_validate(_GOOD.model_dump())


def test_parses_clean_generation():
    assert _to_partial(_GOOD.model_dump_json()) == _GOOD_PARTIAL


def test_tolerates_residual_task_token():
    # skip_special_tokens normally removes it, but be robust if it lingers.
    assert _to_partial(TASK_TOKEN + _GOOD.model_dump_json()) == _GOOD_PARTIAL


def test_garbled_json_is_empty_read_not_fabricated():
    partial = _to_partial("{weight_kg: 70, ...truncated")
    assert partial == PartialInBody()  # all None — nothing fabricated


def test_missing_field_is_left_unread():
    data = _GOOD.model_dump()
    del data["lean_body_mass_kg"]

    partial = _to_partial(json.dumps(data))

    assert partial.lean_body_mass_kg is None  # unread
    assert partial.weight_kg == 70.0  # the rest is still read
    assert partial.segmental_lean.trunk_kg == 24.5
