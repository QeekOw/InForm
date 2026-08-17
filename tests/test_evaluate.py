from pathlib import Path

from cera.errors import NotAnInBodySheetError
from cera.evaluate import evaluate
from cera.inbody import InBodyPayload, SegmentalLean

_TRUTH = InBodyPayload(
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
_IMAGE = Path("sheet.png")


def _engine_returning(payload: InBodyPayload):
    return lambda image_path: payload


def test_perfect_prediction_scores_100_percent():
    report = evaluate(_engine_returning(_TRUTH), [(_IMAGE, _TRUTH)])

    assert report.whole_sheet_accuracy == 1.0
    assert all(rate == 1.0 for rate in report.per_field_accuracy.values())
    assert all(rate == 1.0 for rate in report.critical_field_accuracy.values())


def test_one_wrong_field_zeroes_whole_sheet_and_only_that_field():
    wrong = _TRUTH.model_copy(update={"weight_kg": 999.0})

    report = evaluate(_engine_returning(wrong), [(_IMAGE, _TRUTH)])

    assert report.whole_sheet_accuracy == 0.0
    assert report.per_field_accuracy["weight_kg"] == 0.0
    assert report.per_field_accuracy["lean_body_mass_kg"] == 1.0
    assert report.per_field_accuracy["source_device"] == 1.0


def test_wrong_critical_field_shows_in_critical_cut():
    wrong = _TRUTH.model_copy(update={"lean_body_mass_kg": 1.0})

    report = evaluate(_engine_returning(wrong), [(_IMAGE, _TRUTH)])

    assert report.critical_field_accuracy["lean_body_mass_kg"] == 0.0
    assert all(
        rate == 1.0 for field, rate in report.critical_field_accuracy.items() if field != "lean_body_mass_kg"
    )


def test_tolerance_boundary_within_0_1_counts_as_correct():
    within = _TRUTH.model_copy(update={"weight_kg": 70.1})

    report = evaluate(_engine_returning(within), [(_IMAGE, _TRUTH)])

    assert report.per_field_accuracy["weight_kg"] == 1.0


def test_tolerance_boundary_beyond_0_1_counts_as_incorrect():
    beyond = _TRUTH.model_copy(update={"weight_kg": 70.11})

    report = evaluate(_engine_returning(beyond), [(_IMAGE, _TRUTH)])

    assert report.per_field_accuracy["weight_kg"] == 0.0


def test_matching_none_visceral_fat_counts_as_correct():
    truth_270 = _TRUTH.model_copy(update={"source_device": "inbody_270", "visceral_fat_level": None})

    report = evaluate(_engine_returning(truth_270), [(_IMAGE, truth_270)])

    assert report.per_field_accuracy["visceral_fat_level"] == 1.0


def test_wrong_optional_field_does_not_zero_whole_sheet_accuracy():
    # visceral_fat_level is optional (ADR-0004); whole_sheet_accuracy only
    # gates on required fields (ADR-0006), so a misread here shouldn't zero it.
    wrong = _TRUTH.model_copy(update={"visceral_fat_level": 1})

    report = evaluate(_engine_returning(wrong), [(_IMAGE, _TRUTH)])

    assert report.per_field_accuracy["visceral_fat_level"] == 0.0
    assert report.whole_sheet_accuracy == 1.0


def test_fail_closed_refusal_scores_as_whole_sheet_miss():
    def refusing_engine(image_path):
        raise NotAnInBodySheetError()

    report = evaluate(refusing_engine, [(_IMAGE, _TRUTH)])

    assert report.whole_sheet_accuracy == 0.0
    assert all(rate == 0.0 for rate in report.per_field_accuracy.values())


def test_averages_per_field_rate_across_multiple_sheets():
    wrong = _TRUTH.model_copy(update={"weight_kg": 999.0})

    report = evaluate(lambda image_path: _TRUTH if image_path == _IMAGE else wrong, [(_IMAGE, _TRUTH), (Path("other.png"), _TRUTH)])

    assert report.per_field_accuracy["weight_kg"] == 0.5
    assert report.whole_sheet_accuracy == 0.5
