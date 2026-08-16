# These tests mock the OpenAI client, so the fixture image's content is
# never read by the model — they verify seam wiring (schema binding, image
# encoding), not real VLM extraction accuracy. Accuracy against known
# per-device ground truth belongs to the eval harness (issue #6), which
# will run against the synthetic-generator's labeled sheets (issue #5).
from pathlib import Path
from unittest.mock import MagicMock

from cera.extract import extract_inbody
from cera.inbody import InBodyPayload, SegmentalLean

FIXTURE = Path(__file__).parent / "fixtures" / "inbody_sample.png"


def _segmental() -> SegmentalLean:
    return SegmentalLean(
        left_arm_kg=3.2,
        right_arm_kg=3.3,
        left_leg_kg=8.1,
        right_leg_kg=8.2,
        trunk_kg=24.5,
    )


def _fake_openai(monkeypatch, payload: InBodyPayload) -> MagicMock:
    completion = MagicMock()
    completion.choices = [MagicMock(message=MagicMock(parsed=payload))]
    client = MagicMock()
    client.beta.chat.completions.parse.return_value = completion
    monkeypatch.setattr("cera.engines.vlm.OpenAI", lambda **_: client)
    return client


def test_extracts_570_sheet_with_visceral_fat(monkeypatch):
    expected = InBodyPayload(
        weight_kg=70.0,
        lean_body_mass_kg=58.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=_segmental(),
        visceral_fat_level=7,
        source_device="inbody_570",
    )
    _fake_openai(monkeypatch, expected)

    result = extract_inbody(FIXTURE)

    assert result == expected


def test_extracts_270_sheet_without_visceral_fat(monkeypatch):
    expected = InBodyPayload(
        weight_kg=62.0,
        lean_body_mass_kg=48.0,
        percent_body_fat=22.5,
        skeletal_muscle_mass_kg=26.0,
        basal_metabolic_rate_kcal=1406.8,
        segmental_lean=_segmental(),
        source_device="inbody_270",
    )
    _fake_openai(monkeypatch, expected)

    result = extract_inbody(FIXTURE)

    assert result.visceral_fat_level is None
    assert result.source_device == "inbody_270"


def test_binds_structured_output_schema_and_encodes_image(monkeypatch):
    expected = InBodyPayload(
        weight_kg=70.0,
        lean_body_mass_kg=58.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=_segmental(),
        source_device="inbody_570",
    )
    client = _fake_openai(monkeypatch, expected)

    extract_inbody(FIXTURE)

    call_kwargs = client.beta.chat.completions.parse.call_args.kwargs
    assert call_kwargs["response_format"] is InBodyPayload
    image_content = call_kwargs["messages"][1]["content"][0]
    assert image_content["image_url"]["url"].startswith("data:image/png;base64,")
