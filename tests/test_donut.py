# The Donut engine's model inference needs a GPU + real checkpoint (covered by
# the training smoke test + the Colab run); these tests exercise the parsing /
# fail-closed logic that turns a decoded sequence into a payload, which is the
# only non-trivial branch and runs without torch.
import pytest

from cera.engines.donut import TASK_TOKEN, _to_payload
from cera.errors import MissingRequiredFieldsError
from cera.inbody import InBodyPayload

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


def test_parses_clean_generation():
    assert _to_payload(_GOOD.model_dump_json()) == _GOOD


def test_tolerates_residual_task_token():
    # skip_special_tokens normally removes it, but be robust if it lingers.
    assert _to_payload(TASK_TOKEN + _GOOD.model_dump_json()) == _GOOD


def test_garbled_json_fails_closed_not_fabricated():
    with pytest.raises(MissingRequiredFieldsError):
        _to_payload("{weight_kg: 70, ...truncated")


def test_missing_field_is_named():
    partial = _GOOD.model_dump()
    del partial["lean_body_mass_kg"]
    import json

    with pytest.raises(MissingRequiredFieldsError) as excinfo:
        _to_payload(json.dumps(partial))
    assert "lean_body_mass_kg" in excinfo.value.fields
