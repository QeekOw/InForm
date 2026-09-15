import pytest
from inform.corrections import (
    CorrectionValue,
    UnreadFieldsError,
    apply_corrections,
    validate_correction,
)
from inform.inbody import PartialInBody, PartialSegmentalLean


def _partial_segmental(**overrides) -> PartialSegmentalLean:
    fields = dict(
        left_arm_kg=3.1,
        right_arm_kg=3.1,
        left_leg_kg=6.9,
        right_leg_kg=6.4,
        trunk_kg=19.5,
    )
    fields.update(overrides)
    return PartialSegmentalLean(**fields)


def _partial_inbody(**overrides) -> PartialInBody:
    fields = dict(
        weight_kg=56.7,
        lean_body_mass_kg=39.0,
        percent_body_fat=31.2,
        skeletal_muscle_mass_kg=24.4,
        basal_metabolic_rate_kcal=1212.4,
        segmental_lean=_partial_segmental(),
        source_device="inbody_270",
        visceral_fat_level=9,
    )
    fields.update(overrides)
    return PartialInBody(**fields)


# AC: An out-of-range or wrong-unit value is rejected before the plan is computed


def test_out_of_range_weight_rejected():
    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("weight_kg", CorrectionValue(value=500.0))

    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("weight_kg", CorrectionValue(value=5.0))


def test_out_of_range_lbm_rejected():
    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("lean_body_mass_kg", CorrectionValue(value=7.0))  # slipped decimal like real_270_clean

    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("lean_body_mass_kg", CorrectionValue(value=300.0))


def test_out_of_range_pbf_rejected():
    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("percent_body_fat", CorrectionValue(value=85.0))

    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("percent_body_fat", CorrectionValue(value=1.0))


def test_out_of_range_bmr_rejected():
    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("basal_metabolic_rate_kcal", CorrectionValue(value=200.0))

    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("basal_metabolic_rate_kcal", CorrectionValue(value=7000.0))


def test_out_of_range_visceral_fat_rejected():
    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("visceral_fat_level", CorrectionValue(value=40))

    with pytest.raises(ValueError, match="must be an integer"):
        validate_correction("visceral_fat_level", CorrectionValue(value=5.5))


def test_out_of_range_segmental_limb_rejected():
    with pytest.raises(ValueError, match="out of plausible range"):
        validate_correction("segmental_lean.left_arm_kg", CorrectionValue(value=25.0))


def test_wrong_unit_weight_rejected():
    with pytest.raises(ValueError, match="Invalid unit 'lbs' for Weight"):
        validate_correction("weight_kg", CorrectionValue(value=70.0, unit="lbs"))


def test_wrong_unit_pbf_rejected():
    with pytest.raises(ValueError, match="Invalid unit 'kg' for Percent Body Fat"):
        validate_correction("percent_body_fat", CorrectionValue(value=20.0, unit="kg"))


def test_wrong_unit_bmr_rejected():
    with pytest.raises(ValueError, match="Invalid unit 'kJ' for Basal Metabolic Rate"):
        validate_correction("basal_metabolic_rate_kcal", CorrectionValue(value=1500.0, unit="kJ"))


def test_correct_units_accepted():
    validate_correction("weight_kg", CorrectionValue(value=70.0, unit="kg"))
    validate_correction("percent_body_fat", CorrectionValue(value=20.0, unit="%"))
    validate_correction("basal_metabolic_rate_kcal", CorrectionValue(value=1600.0, unit="kcal"))
    validate_correction("visceral_fat_level", CorrectionValue(value=8, unit="level"))


# AC: A typed value lets the plan proceed
# AC: Corrected fields are stored alongside measured fields, never merged into them


def test_typed_value_fills_unread_field_and_proceeds():
    measured = _partial_inbody(lean_body_mass_kg=None)
    assert measured.lean_body_mass_kg is None

    payload, corrected = apply_corrections(
        measured,
        {"lean_body_mass_kg": CorrectionValue(value=42.0, unit="kg")},
    )

    assert payload.lean_body_mass_kg == 42.0
    assert corrected == ["lean_body_mass_kg"]
    # Measured object was NOT mutated
    assert measured.lean_body_mass_kg is None


def test_person_corrects_plainly_wrong_field():
    measured = _partial_inbody(lean_body_mass_kg=7.0)  # misread OCR value

    payload, corrected = apply_corrections(
        measured,
        {"lean_body_mass_kg": 45.0},
    )

    assert payload.lean_body_mass_kg == 45.0
    assert corrected == ["lean_body_mass_kg"]
    assert measured.lean_body_mass_kg == 7.0


# AC: Building a plan is impossible while a required field remains unread


def test_building_plan_impossible_while_required_field_unread():
    # lean_body_mass_kg and weight_kg are both unread
    measured = _partial_inbody(lean_body_mass_kg=None, weight_kg=None)

    # Only one of them is corrected
    with pytest.raises(UnreadFieldsError) as exc_info:
        apply_corrections(
            measured,
            {"lean_body_mass_kg": 42.0},
        )

    assert "weight_kg" in exc_info.value.unread_fields


def test_lbm_exceeding_weight_rejected():
    measured = _partial_inbody(weight_kg=60.0)
    with pytest.raises(ValueError, match="Lean Body Mass cannot exceed total Weight"):
        apply_corrections(measured, {"lean_body_mass_kg": 65.0})
