# The Donut engine's model inference needs a GPU + real checkpoint (covered by
# the training smoke test + the Colab run); these tests exercise the parsing
# logic that turns a decoded sequence into a PartialInBody, which is the only
# non-trivial branch and runs without torch. Partial extraction (ADR-0008
# amended): a garbled/incomplete generation yields an empty/partial read (all or
# some fields None), never a fabricated value — the seam decides floor-reject.
import json

from inform.engines.donut import TASK_TOKEN, _to_partial
from inform.inbody import InBodyPayload, PartialInBody

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
    # The engine decodes with special tokens kept (#58), so it is always there.
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


def test_bad_typed_field_is_dropped_but_others_kept():
    # Valid JSON, one non-coercible value: keep the good keys, drop only the bad
    # one (spec: keep whatever parses). Nothing fabricated.
    data = _GOOD.model_dump()
    data["weight_kg"] = "n/a"

    partial = _to_partial(json.dumps(data))

    assert partial.weight_kg is None  # the bad field is dropped -> unread
    assert partial.lean_body_mass_kg == 58.0  # the rest survives
    assert partial.segmental_lean.trunk_kg == 24.5
def test_lone_one_written_as_unk_reads_as_one():
    # The tokenizer has no token for a lone "1"; its id is <unk>'s, so the model
    # writes 57.1 as 57.<unk>. Deleting <unk> left "57.", invalid JSON that cost
    # every field after it. In the training targets <unk> only ever stands for
    # "1", so reading it back is the model's own value, not a guess.
    partial = _to_partial(
        '{"weight_kg":66.2,"lean_body_mass_kg":57.<unk>,"percent_body_fat":13.8}'
    )

    assert partial.lean_body_mass_kg == 57.1
    assert partial.percent_body_fat == 13.8


def test_generation_ending_at_unk_is_left_unread():
    # Without the rest of the JSON object, the decoded digit is incomplete and
    # must not be accepted as a completed measurement.
    partial = _to_partial('{"weight_kg":5<unk>')

    assert partial.weight_kg is None


def test_end_token_kept_by_decode_does_not_cost_the_last_field():
    # The engine decodes with special tokens kept so <unk> survives to be read as
    # "1" (#58). The end-of-sequence token comes through with it.
    partial = _to_partial(TASK_TOKEN + '{"weight_kg":66.2,"percent_body_fat":13.8}</s>')

    assert partial.weight_kg == 66.2
    assert partial.percent_body_fat == 13.8


def test_other_special_tokens_the_decode_keeps_are_not_part_of_the_read():
    # Skipping special tokens used to drop these as well. Kept, a leading <s>
    # refused the whole sheet and trailing padding cost the last field.
    partial = _to_partial(
        "<s>" + TASK_TOKEN + '{"weight_kg":66.2,"percent_body_fat":13.8}</s><pad><mask>'
    )

    assert partial.weight_kg == 66.2
    assert partial.percent_body_fat == 13.8
