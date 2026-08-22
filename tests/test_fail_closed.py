# Partial extraction + the remaining fail-closed paths (ADR-0008 amended):
# extract_inbody returns what it read plus `unread`/`flagged`, and never
# fabricates. It still hard-rejects two cases — a non-InBody image, and the
# floor case where nothing readable came back. The OpenAI client is mocked so
# each path is exercised deterministically, independent of real VLM output.
from pathlib import Path

import pytest

from cera.engines.vlm import _RawExtraction
from cera.errors import MissingRequiredFieldsError, NotAnInBodySheetError
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


def test_missing_required_field_is_unread_not_raised(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, lean_body_mass_kg=None))

    result = extract_inbody(FIXTURE)

    assert result.unread == ["lean_body_mass_kg"]
    assert not result.is_complete()
    assert result.data.weight_kg == 70.0  # the rest is still returned


def test_missing_segmental_field_is_unread_with_prefix(fake_openai, raw_segmental):
    fake_openai(_raw(raw_segmental, segmental_lean=raw_segmental(trunk_kg=None)))

    result = extract_inbody(FIXTURE)

    assert result.unread == ["segmental_lean.trunk_kg"]


def test_lbm_cross_check_breach_is_flagged_not_raised(fake_openai, raw_segmental):
    # weight x (1 - PBF/100) = 70 x 0.829 = 58.03; 40.0 is far outside tolerance.
    # BMR 1234 == 370 + 21.6 x 40, so only the LBM check fires.
    fake_openai(_raw(raw_segmental, lean_body_mass_kg=40.0, basal_metabolic_rate_kcal=1234.0))

    result = extract_inbody(FIXTURE)

    assert result.flagged == ["weight_kg", "percent_body_fat", "lean_body_mass_kg"]
    assert result.data.lean_body_mass_kg == 40.0  # value kept, just flagged
    assert not result.is_complete()


def test_bmr_cross_check_breach_is_flagged_not_raised(fake_openai, raw_segmental):
    # Katch-McArdle recompute = 370 + 21.6 x 58.0 = 1622.8; 2000 is far off.
    fake_openai(_raw(raw_segmental, basal_metabolic_rate_kcal=2000.0))

    result = extract_inbody(FIXTURE)

    assert result.flagged == ["basal_metabolic_rate_kcal", "lean_body_mass_kg"]


def test_non_inbody_image_is_rejected(fake_openai):
    fake_openai(_RawExtraction(is_inbody_sheet=False))

    with pytest.raises(NotAnInBodySheetError):
        extract_inbody(FIXTURE)


def test_floor_case_nothing_readable_is_rejected(fake_openai, raw_segmental):
    # A sheet where no required field could be read fails closed (re-upload),
    # rather than returning an all-empty result.
    fake_openai(
        _RawExtraction(
            is_inbody_sheet=True,
            weight_kg=None,
            lean_body_mass_kg=None,
            percent_body_fat=None,
            skeletal_muscle_mass_kg=None,
            basal_metabolic_rate_kcal=None,
            segmental_lean=None,
            source_device=None,
        )
    )

    with pytest.raises(MissingRequiredFieldsError):
        extract_inbody(FIXTURE)


def test_270_sheet_without_visceral_fat_is_complete(fake_openai, raw_segmental):
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

    assert result.is_complete()
    assert result.data.visceral_fat_level is None
    assert result.data.source_device == "inbody_270"
