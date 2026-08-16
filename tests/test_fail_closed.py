# Fail-closed behavior (ADR-0008): extract_inbody must refuse rather than
# fabricate. The OpenAI client is mocked so each path is exercised
# deterministically, independent of real VLM output.
from pathlib import Path

import pytest

from cera.engines.vlm import _RawExtraction
from cera.errors import CrossCheckFailedError, MissingRequiredFieldsError, NotAnInBodySheetError
from cera.extract import extract_inbody

FIXTURE = Path(__file__).parent / "fixtures" / "inbody_sample.png"


def _raw(raw_segmental, **overrides) -> _RawExtraction:
    fields = dict(
        is_inbody_sheet=True,
        weight_kg=70.0,
        lean_body_mass_kg=58.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=raw_segmental(),
        source_device="inbody_570",
    )
    fields.update(overrides)
    return _RawExtraction(**fields)


def test_missing_required_field_raises_named_error(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, lean_body_mass_kg=None))

    with pytest.raises(MissingRequiredFieldsError) as excinfo:
        extract_inbody(FIXTURE)

    assert excinfo.value.fields == ["lean_body_mass_kg"]


def test_missing_segmental_field_is_named_with_prefix(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, segmental_lean=raw_segmental(trunk_kg=None)))

    with pytest.raises(MissingRequiredFieldsError) as excinfo:
        extract_inbody(FIXTURE)

    assert excinfo.value.fields == ["segmental_lean.trunk_kg"]


def test_lbm_cross_check_breach_is_flagged(fake_openai, raw_segmental):
    # weight x (1 - PBF/100) = 70 x 0.829 = 58.03; 40.0 is far outside tolerance.
    fake_openai(_raw(raw_segmental, lean_body_mass_kg=40.0, basal_metabolic_rate_kcal=1234.0))

    with pytest.raises(CrossCheckFailedError) as excinfo:
        extract_inbody(FIXTURE)

    assert excinfo.value.check_name == "lbm_vs_weight_pbf"


def test_bmr_cross_check_breach_is_flagged(fake_openai, raw_segmental):
    # Katch-McArdle recompute = 370 + 21.6 x 58.0 = 1622.8; 2000 is far off.
    fake_openai(_raw(raw_segmental, basal_metabolic_rate_kcal=2000.0))

    with pytest.raises(CrossCheckFailedError) as excinfo:
        extract_inbody(FIXTURE)

    assert excinfo.value.check_name == "bmr_vs_katch_mcardle"


def test_non_inbody_image_is_rejected(fake_openai):
    fake_openai(_RawExtraction(is_inbody_sheet=False))

    with pytest.raises(NotAnInBodySheetError):
        extract_inbody(FIXTURE)


def test_270_sheet_without_visceral_fat_succeeds(fake_openai, raw_segmental):
    fake_openai(
        _raw(
            raw_segmental,
            weight_kg=62.0,
            lean_body_mass_kg=48.0,
            percent_body_fat=22.5,
            skeletal_muscle_mass_kg=26.0,
            basal_metabolic_rate_kcal=1406.8,
            source_device="inbody_270",
        )
    )

    result = extract_inbody(FIXTURE)

    assert result.visceral_fat_level is None
    assert result.source_device == "inbody_270"
