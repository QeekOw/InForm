import json
from pathlib import Path

import pytest

from inform.errors import MissingRequiredFieldsError, NotAnInBodySheetError
from inform.holdout import load_holdout, load_labels, replay_engine, score
from inform.inbody import InBodyExtraction, PartialInBody, PartialSegmentalLean

# A hand-labelled sheet: what a person can read off a printout, which is a
# subset of the schema. Everything absent here is *unknown*, not zero.
_LABEL = PartialInBody(
    weight_kg=85.5,
    lean_body_mass_kg=63.1,
    percent_body_fat=26.2,
    skeletal_muscle_mass_kg=35.9,
    basal_metabolic_rate_kcal=1732,
    visceral_fat_level=9,
    segmental_lean=PartialSegmentalLean(
        left_arm_kg=3.63, right_arm_kg=3.68, left_leg_kg=9.59, right_leg_kg=9.59, trunk_kg=28.2
    ),
)
_IMAGE = Path("sheet_05.png")


def _reading(data: PartialInBody, unread=None, flagged=None):
    return lambda image_path: InBodyExtraction(
        data=data, unread=unread or [], flagged=flagged or []
    )


def _refusing(exc):
    def _raise(image_path):
        raise exc

    return _raise


def _write_labels(tmp_path: Path, labels: dict) -> Path:
    path = tmp_path / "labels.json"
    path.write_text(json.dumps(labels), encoding="utf-8")
    return path


def test_load_labels_reads_sheet_stems_and_ignores_notes(tmp_path):
    path = _write_labels(
        tmp_path,
        {
            "_note": "hand-read off the printouts, do not commit",
            "_unlabelled": ["sheet_01"],
            "sheet_05": {"weight_kg": 85.5, "percent_body_fat": 26.2},
        },
    )

    labels = load_labels(path)

    assert list(labels) == ["sheet_05"]
    assert labels["sheet_05"].weight_kg == 85.5
    # An unmentioned field stays unknown rather than defaulting to a value.
    assert labels["sheet_05"].skeletal_muscle_mass_kg is None


def test_load_holdout_pairs_every_image_labelled_or_not(tmp_path):
    (tmp_path / "sheet_01.png").write_bytes(b"")
    (tmp_path / "sheet_05.png").write_bytes(b"")
    path = _write_labels(tmp_path, {"sheet_05": {"weight_kg": 85.5}})

    holdout = load_holdout(tmp_path, path)

    assert [image.name for image, _ in holdout] == ["sheet_01.png", "sheet_05.png"]
    assert holdout[0][1] is None
    assert holdout[1][1] is not None


def test_load_holdout_rejects_a_directory_with_no_images(tmp_path):
    path = _write_labels(tmp_path, {})

    with pytest.raises(ValueError, match="No hold-out images"):
        load_holdout(tmp_path, path)


def test_a_perfect_read_scores_every_labelled_field():
    report = score(_reading(_LABEL), [(_IMAGE, _LABEL)])

    assert report.core.matched == 6 and report.core.labelled == 6
    assert report.segmental.matched == 5 and report.segmental.labelled == 5
    assert report.core.accuracy == 1.0
    assert report.outcome_split["usable"] == 1


def test_an_unlabelled_field_leaves_the_denominator():
    # Only weight was hand-read. The other fields are unknown, so a correct
    # weight is 1/1 and not 1/6 -- scoring unknowns as misses would make every
    # checkpoint look broken.
    sparse = PartialInBody(weight_kg=85.5)

    report = score(_reading(_LABEL), [(_IMAGE, sparse)])

    assert report.core.matched == 1 and report.core.labelled == 1
    assert report.segmental.labelled == 0
    assert report.per_field["percent_body_fat"].labelled == 0


def test_a_field_the_model_left_unread_scores_wrong_against_a_label():
    blank_arm = _LABEL.model_copy(deep=True)
    blank_arm.segmental_lean.right_arm_kg = None

    report = score(_reading(blank_arm, unread=["segmental_lean.right_arm_kg"]), [(_IMAGE, _LABEL)])

    assert report.per_field["segmental_lean.right_arm_kg"].matched == 0
    assert report.per_field["segmental_lean.right_arm_kg"].labelled == 1
    assert report.segmental.matched == 4 and report.segmental.labelled == 5
    assert report.outcome_split["unread"] == 1


def test_the_panel_crossing_shows_up_as_a_wrong_segmental_field():
    # sheet_05's failure: the right-arm lean value read as the neighbouring
    # panel's left-arm *fat* value (docs/ocr-eval-results.md). It scores as a
    # miss on that field alone, with the rest of the sheet still credited.
    crossed = _LABEL.model_copy(deep=True)
    crossed.segmental_lean.right_arm_kg = 0.94  # a fat-panel value, not lean

    report = score(_reading(crossed), [(_IMAGE, _LABEL)])

    assert report.per_field["segmental_lean.right_arm_kg"].matched == 0
    assert report.segmental.matched == 4
    assert report.core.matched == 6


def test_a_refusal_scores_every_labelled_field_wrong():
    # Otherwise a checkpoint that refuses everything would score perfectly by
    # reading nothing.
    report = score(_refusing(NotAnInBodySheetError()), [(_IMAGE, _LABEL)])

    assert report.core.matched == 0 and report.core.labelled == 6
    assert report.segmental.matched == 0 and report.segmental.labelled == 5
    assert report.outcome_split["refused"] == 1


def test_outcome_split_counts_unlabelled_sheets_too():
    # The split is the one real-photo number that needs no ground truth, so it
    # covers all 12 sheets while per-field covers only the labelled ones.
    holdout = [
        (Path("sheet_01.png"), None),
        (Path("sheet_02.png"), None),
        (_IMAGE, _LABEL),
    ]

    def extractor(image_path):
        if image_path.name == "sheet_01.png":
            raise MissingRequiredFieldsError(["weight_kg"])
        if image_path.name == "sheet_02.png":
            return InBodyExtraction(data=_LABEL, unread=[], flagged=["weight_kg"])
        return InBodyExtraction(data=_LABEL, unread=[], flagged=[])

    report = score(extractor, holdout)

    assert report.n_sheets == 3
    assert report.n_labelled == 1
    assert report.outcome_split == {"usable": 1, "flagged": 1, "unread": 0, "refused": 1}
    assert report.core.labelled == 6  # only the labelled sheet contributes


def test_flagged_and_unread_are_counted_once_each():
    # A sheet that is both flagged and incomplete counts as flagged: a
    # cross-check breach is the stronger signal and the two must not double-count.
    report = score(
        _reading(_LABEL, unread=["weight_kg"], flagged=["weight_kg"]), [(_IMAGE, _LABEL)]
    )

    assert report.outcome_split == {"usable": 0, "flagged": 1, "unread": 0, "refused": 0}


def test_replay_engine_reads_a_recorded_run_by_name_or_stem(tmp_path):
    # Scoring a recorded run needs neither the checkpoint nor a GPU, which is
    # what keeps a published baseline checkable later.
    reads = tmp_path / "reads.json"
    reads.write_text(json.dumps({"sheet_05.png": {"weight_kg": 85.5}}), encoding="utf-8")

    engine = replay_engine(reads)

    assert engine(Path("a/sheet_05.png")).weight_kg == 85.5
    with pytest.raises(KeyError, match="sheet_99.png"):
        engine(Path("sheet_99.png"))


def test_the_real_holdout_scores_limbs_by_the_relative_bound_too():
    # sheet_06's printed left arm is 3.59 kg and donut-both-v3 read 3.5: 0.09 kg
    # out, inside the absolute tolerance, 2.5% out. The dropped second decimal
    # on an arm is what clears exercise_filter's 5% asymmetry trigger, so the
    # real hold-out has to see it as a miss, exactly as the synthetic set does.
    dropped_decimal = _LABEL.model_copy(deep=True)
    dropped_decimal.segmental_lean.left_arm_kg = 3.5
    label = _LABEL.model_copy(deep=True)
    label.segmental_lean.left_arm_kg = 3.59

    report = score(_reading(dropped_decimal), [(_IMAGE, label)])

    assert report.per_field["segmental_lean.left_arm_kg"].matched == 0
    assert report.per_field["segmental_lean.left_arm_kg"].labelled == 1
    assert report.segmental.matched == 4 and report.segmental.labelled == 5
    assert report.core.matched == 6  # scalars untouched by the limb rule


def test_an_unlabelled_field_reports_no_accuracy_rather_than_zero():
    # 0/0 is unknown, not 0% correct. Returning 0.0 would let any caller that
    # averages per-field accuracy drag the mean down with fields nobody read --
    # the exact error the partial-truth denominator exists to prevent.
    report = score(_reading(_LABEL), [(_IMAGE, _LABEL)])

    assert report.per_field["source_device"].labelled == 0
    assert report.per_field["source_device"].accuracy is None
    assert report.per_field["weight_kg"].accuracy == 1.0


def test_the_critical_field_cut_is_lbm_plus_the_limbs():
    # ADR-0006 requires separate reporting for the fields the pipeline hinges
    # on: lean_body_mass_kg and the segmental lean values. On this hold-out that
    # is the number that matters, because LBM is the weakest field.
    wrong_lbm = _LABEL.model_copy(deep=True)
    wrong_lbm.lean_body_mass_kg = 30.0  # the observed donut-both-v3 misread

    report = score(_reading(wrong_lbm), [(_IMAGE, _LABEL)])

    assert report.critical.labelled == 6  # LBM + five limbs
    assert report.critical.matched == 5  # limbs right, LBM wrong
    assert report.core.matched == 5  # LBM also sits in the scalar cut
