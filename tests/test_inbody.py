import pytest
from pydantic import ValidationError

from inform.inbody import InBodyPayload, SegmentalLean


def _segmental() -> SegmentalLean:
    return SegmentalLean(
        left_arm_kg=3.2,
        right_arm_kg=3.3,
        left_leg_kg=8.1,
        right_leg_kg=8.2,
        trunk_kg=24.5,
    )


def _payload(**overrides) -> InBodyPayload:
    fields = dict(
        weight_kg=70.0,
        lean_body_mass_kg=58.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=_segmental(),
        source_device="inbody_570",
    )
    fields.update(overrides)
    return InBodyPayload(**fields)


def test_valid_570_payload_with_visceral_fat():
    payload = _payload(visceral_fat_level=7)
    assert payload.visceral_fat_level == 7
    assert payload.source_device == "inbody_570"


def test_valid_270_payload_without_visceral_fat():
    payload = _payload(source_device="inbody_270")
    assert payload.visceral_fat_level is None
    assert payload.source_device == "inbody_270"


def test_missing_required_field_rejected():
    fields = dict(
        weight_kg=70.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=_segmental(),
        source_device="inbody_270",
    )
    with pytest.raises(ValidationError):
        InBodyPayload(**fields)


def test_invalid_source_device_rejected():
    with pytest.raises(ValidationError):
        _payload(source_device="inbody_990")


def test_payload_round_trips_through_json():
    original = _payload(visceral_fat_level=7)
    restored = InBodyPayload.model_validate_json(original.model_dump_json())
    assert restored == original
