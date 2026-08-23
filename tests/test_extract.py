# These tests mock the OpenAI client, so the fixture image's content is
# never read by the model — they verify seam wiring (schema binding, image
# encoding), not real VLM extraction accuracy. Accuracy against known
# per-device ground truth belongs to the eval harness (issue #6), which
# will run against the synthetic-generator's labeled sheets (issue #5).
from pathlib import Path

from inform.engines.vlm import _RawExtraction
from inform.extract import extract_inbody
from inform.inbody import InBodyPayload, SegmentalLean

FIXTURE = Path(__file__).parent / "fixtures" / "inbody_sample.png"


def test_extracts_570_sheet_with_visceral_fat(fake_openai, raw_segmental):
    fake_openai(
        _RawExtraction(
            is_inbody_sheet=True,
            weight_kg=70.0,
            lean_body_mass_kg=58.0,
            percent_body_fat=17.1,
            skeletal_muscle_mass_kg=33.0,
            basal_metabolic_rate_kcal=1622.8,
            segmental_lean=raw_segmental(),
            visceral_fat_level=7,
            source_device="inbody_570",
        )
    )

    result = extract_inbody(FIXTURE)

    assert result.is_complete()
    assert not result.unread and not result.flagged
    assert result.as_payload() == InBodyPayload(
        weight_kg=70.0,
        lean_body_mass_kg=58.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=SegmentalLean(
            left_arm_kg=3.2, right_arm_kg=3.3, left_leg_kg=8.1, right_leg_kg=8.2, trunk_kg=24.5
        ),
        visceral_fat_level=7,
        source_device="inbody_570",
    )


def test_extracts_270_sheet_without_visceral_fat(fake_openai, raw_segmental):
    fake_openai(
        _RawExtraction(
            is_inbody_sheet=True,
            weight_kg=62.0,
            lean_body_mass_kg=48.0,
            percent_body_fat=22.5,
            skeletal_muscle_mass_kg=26.0,
            basal_metabolic_rate_kcal=1406.8,
            segmental_lean=raw_segmental(),
            source_device="inbody_270",
        )
    )

    result = extract_inbody(FIXTURE)

    assert result.data.visceral_fat_level is None
    assert result.data.source_device == "inbody_270"
    assert result.is_complete()


def test_binds_structured_output_schema_and_encodes_image(fake_openai, raw_segmental):
    client = fake_openai(
        _RawExtraction(
            is_inbody_sheet=True,
            weight_kg=70.0,
            lean_body_mass_kg=58.0,
            percent_body_fat=17.1,
            skeletal_muscle_mass_kg=33.0,
            basal_metabolic_rate_kcal=1622.8,
            segmental_lean=raw_segmental(),
            source_device="inbody_570",
        )
    )

    extract_inbody(FIXTURE)

    call_kwargs = client.beta.chat.completions.parse.call_args.kwargs
    assert call_kwargs["response_format"] is _RawExtraction
    image_content = call_kwargs["messages"][1]["content"][0]
    assert image_content["image_url"]["url"].startswith("data:image/png;base64,")
