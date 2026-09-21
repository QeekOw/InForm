# Partial extraction + the remaining fail-closed paths (ADR-0008 amended):
# extract_inbody returns what it read plus `unread`/`flagged`, and never
# fabricates. It still hard-rejects two cases — a non-InBody image, and the
# floor case where nothing readable came back. The OpenAI client is mocked so
# each path is exercised deterministically, independent of real VLM output.
from pathlib import Path

import pytest

from inform.engines.vlm import _RawExtraction
from inform.errors import MissingRequiredFieldsError, NotAnInBodySheetError
from inform.extract import extract_inbody

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
        source_device="inbody_270",
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


def test_a_one_decimal_arm_on_a_two_decimal_sheet_is_flagged(fake_openai, raw_segmental):
    # ADR-0008 (2026-09-13): the legs carry two decimals, so the one-decimal
    # arm is flagged, and only that arm.
    segmental = raw_segmental(
        left_arm_kg=3.2, right_arm_kg=3.31, left_leg_kg=8.86, right_leg_kg=8.83
    )
    fake_openai(_raw(raw_segmental, segmental_lean=segmental))

    result = extract_inbody(FIXTURE)

    assert result.flagged == ["segmental_lean.left_arm_kg"]
    assert result.data.segmental_lean.left_arm_kg == 3.2  # value kept, just flagged


def test_two_decimal_arms_on_a_two_decimal_sheet_are_not_flagged(fake_openai, raw_segmental):
    segmental = raw_segmental(
        left_arm_kg=3.27, right_arm_kg=3.31, left_leg_kg=8.86, right_leg_kg=8.83
    )
    fake_openai(_raw(raw_segmental, segmental_lean=segmental))

    assert extract_inbody(FIXTURE).flagged == []


def test_one_decimal_limbs_throughout_are_not_flagged(fake_openai, raw_segmental):
    # A sheet that prints every limb to one decimal, as every synthetic sheet
    # does today, shows no sign of a missing digit.
    fake_openai(_raw(raw_segmental))

    assert extract_inbody(FIXTURE).flagged == []


def test_an_arm_is_not_flagged_when_no_leg_was_read(fake_openai, raw_segmental):
    # Without a leg there is no evidence of how many decimals the sheet prints.
    segmental = raw_segmental(left_arm_kg=3.2, left_leg_kg=None, right_leg_kg=None)
    fake_openai(_raw(raw_segmental, segmental_lean=segmental))

    assert extract_inbody(FIXTURE).flagged == []


def test_one_two_decimal_leg_is_enough_and_the_arm_flag_follows_the_others(
    fake_openai, raw_segmental
):
    # One leg unread and the other past 10 kg, the short arm on the right, and
    # the same LBM breach as the LBM test above on the same read.
    segmental = raw_segmental(
        left_arm_kg=3.27, right_arm_kg=3.3, left_leg_kg=None, right_leg_kg=10.46
    )
    fake_openai(
        _raw(
            raw_segmental,
            segmental_lean=segmental,
            lean_body_mass_kg=40.0,
            basal_metabolic_rate_kcal=1234.0,
        )
    )

    result = extract_inbody(FIXTURE)

    assert result.flagged == [
        "weight_kg",
        "percent_body_fat",
        "lean_body_mass_kg",
        "segmental_lean.right_arm_kg",
    ]


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
