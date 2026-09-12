import json
from pathlib import Path

import pytest

from inform.errors import MissingRequiredFieldsError, NotAnInBodySheetError
from inform.holdout import (
    _source_labels,
    format_comparison,
    load_holdout,
    load_labels,
    replay_engine,
    score,
)
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
    assert report.outcome_split["unverified"] == 1


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
    assert report.outcome_split == {"unverified": 1, "flagged": 1, "unread": 0, "refused": 1}
    assert report.core.labelled == 6  # only the labelled sheet contributes


def test_flagged_and_unread_are_counted_once_each():
    # A sheet that is both flagged and incomplete counts as flagged: a
    # cross-check breach is the stronger signal and the two must not double-count.
    report = score(
        _reading(_LABEL, unread=["weight_kg"], flagged=["weight_kg"]), [(_IMAGE, _LABEL)]
    )

    assert report.outcome_split == {"unverified": 0, "flagged": 1, "unread": 0, "refused": 0}


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


# --- silent error (CONTEXT.md: the headline measure) -------------------------
# A wrong value inside an `unverified` read: wrong, and carrying no signal that
# anything is wrong. Every other failure announces itself, so these tests pin
# what does *not* count as silent as tightly as what does.


def test_a_wrong_value_in_an_unverified_read_is_a_silent_error():
    wrong = _LABEL.model_copy(deep=True)
    wrong.weight_kg = 60.0

    report = score(_reading(wrong), [(_IMAGE, _LABEL)])

    assert report.outcome_split["unverified"] == 1
    assert report.silent.sheets == 1
    assert report.silent.sheets_with_error == 1
    assert report.silent.field_errors == 1
    assert report.silent.sheet_rate == 1.0


def test_a_correct_unverified_read_carries_no_silent_error():
    report = score(_reading(_LABEL), [(_IMAGE, _LABEL)])

    assert report.silent.sheets == 1
    assert report.silent.sheets_with_error == 0
    assert report.silent.field_errors == 0
    assert report.silent.sheet_rate == 0.0


def test_a_wrong_value_that_was_flagged_is_not_silent():
    # The whole point of the metric: an error that announced itself is not the
    # one that reaches a person unnoticed. A flagged sheet leaves the
    # denominator rather than scoring clean.
    wrong = _LABEL.model_copy(deep=True)
    wrong.weight_kg = 60.0

    report = score(_reading(wrong, flagged=["weight_kg"]), [(_IMAGE, _LABEL)])

    assert report.outcome_split["flagged"] == 1
    assert report.silent.sheets == 0
    assert report.silent.field_errors == 0
    assert report.silent.sheet_rate is None


def test_a_wrong_value_in_an_incomplete_read_is_not_silent():
    # `unread` asks the person for the missing fields, so the read is already
    # in front of them. Same reasoning as flagged.
    wrong = _LABEL.model_copy(deep=True)
    wrong.weight_kg = 60.0

    report = score(_reading(wrong, unread=["visceral_fat_level"]), [(_IMAGE, _LABEL)])

    assert report.outcome_split["unread"] == 1
    assert report.silent.sheets == 0


def test_an_unverified_read_on_an_unlabelled_sheet_is_unmeasurable_not_clean():
    # Nothing to check it against. Counting it clean would flatter the engine
    # with exactly the sheets nobody has labelled yet (#24), so it leaves the
    # denominator and is reported as the size of the blind spot instead.
    report = score(_reading(_LABEL), [(_IMAGE, None)])

    assert report.silent.sheets == 0
    assert report.silent.unmeasurable == 1
    assert report.silent.sheet_rate is None


def test_a_refusal_is_neither_silent_nor_unmeasurable():
    # A refusal announces itself and produced no read to check, so it is
    # outside the metric altogether rather than a gap in it.
    report = score(_refusing(NotAnInBodySheetError()), [(_IMAGE, _LABEL)])

    assert report.silent.sheets == 0
    assert report.silent.unmeasurable == 0


def test_silent_error_counts_sheets_and_fields_separately():
    # Per-sheet is the headline -- a sheet is what reaches a person -- and
    # per-field is the diagnostic underneath it.
    wrong = _LABEL.model_copy(deep=True)
    wrong.weight_kg = 60.0
    wrong.percent_body_fat = 5.0

    report = score(_reading(wrong), [(_IMAGE, _LABEL), (Path("sheet_07.png"), _LABEL)])

    assert report.silent.sheets == 2
    assert report.silent.sheets_with_error == 2
    assert report.silent.field_errors == 4
    assert report.silent.fields == 22  # 11 labelled fields on each of the two


# --- comparing checkpoints ---------------------------------------------------
# A retrain produces one checkpoint per epoch and every one has to be scored
# (ADR-0006). The tables in docs/ocr-eval-results.md were transcribed by hand,
# and that has already put a stale baseline into a training notebook, so the
# table is generated from the reports instead.


def test_the_comparison_puts_one_column_per_engine_under_its_own_label():
    reports = {
        "v3": score(_reading(_LABEL), [(_IMAGE, _LABEL)]),
        "e1": score(_reading(_LABEL), [(_IMAGE, _LABEL)]),
    }

    table = format_comparison(reports)

    header = table.splitlines()[0]
    assert "v3" in header and "e1" in header
    assert header.index("v3") < header.index("e1")  # insertion order, not sorted


def test_the_comparison_leads_with_the_silent_error_rate():
    reports = {"v3": score(_reading(_LABEL), [(_IMAGE, _LABEL)])}

    lines = format_comparison(reports).splitlines()
    first_metric = next(i for i, l in enumerate(lines) if "silent" in l.lower())
    first_core = next(i for i, l in enumerate(lines) if "core fields" in l)

    assert first_metric < first_core


def test_a_zero_denominator_shows_as_unmeasured_not_as_a_clean_sheet():
    # The v4 epoch-1 and epoch-4 case: every read flagged, so nothing is
    # `unverified`, so there is no silent-error rate. Printing 0% there would
    # rank the worst checkpoints best. It has to read as "no basis", and the
    # outcome split has to be in the same table to make that legible.
    flagged_everything = score(
        _reading(_LABEL, flagged=["weight_kg"]), [(_IMAGE, _LABEL)]
    )

    table = format_comparison({"e1": flagged_everything})

    silent_line = next(l for l in table.splitlines() if "wrong" in l and ">=1" in l)
    assert "0.0%" not in silent_line
    assert "--" in silent_line
    assert "flagged" in table  # the split that explains the dash


def test_each_engines_numbers_land_under_its_own_column():
    # The table is read across a row to compare checkpoints, so a column that
    # is off by one is worse than no table. Two engines that differ on a field
    # the other gets right, checked by column position.
    wrong = _LABEL.model_copy(deep=True)
    wrong.weight_kg = 60.0
    reports = {
        "good": score(_reading(_LABEL), [(_IMAGE, _LABEL)]),
        "bad": score(_reading(wrong), [(_IMAGE, _LABEL)]),
    }

    lines = format_comparison(reports).splitlines()
    header = lines[0]
    weight = next(l for l in lines if l.strip().startswith("weight_kg"))

    # Each cell is right-justified in its column, so the cell's last character
    # sits at its label's right edge.
    assert weight[: header.index("good") + len("good")].endswith("1/1")
    assert weight[: header.index("bad") + len("bad")].endswith("0/1")


def test_the_comparison_carries_the_per_field_cut_too():
    reports = {"v3": score(_reading(_LABEL), [(_IMAGE, _LABEL)])}

    table = format_comparison(reports)

    assert "percent_body_fat" in table
    assert "segmental_lean.right_arm_kg" in table


def test_checkpoints_sharing_a_basename_get_distinct_labels():
    # Every run names its checkpoints by step, so comparing the same epoch
    # across two runs is the normal retrain question -- and both are called
    # `checkpoint-3750`. Keying a report by the basename drops one silently.
    paths = [
        Path("D:/cera/kaggle_out_v4/donut-both-v4/checkpoint-3750"),
        Path("D:/cera/kaggle_out_v5/donut-both-v5/checkpoint-3750"),
    ]

    labels = _source_labels(paths, [path.name for path in paths])

    assert len(set(labels)) == 2
    assert "donut-both-v4" in labels[0]
    assert "donut-both-v5" in labels[1]


def test_labels_stay_short_when_the_basenames_already_differ():
    paths = [Path("out/donut-both-v3"), Path("out/donut-both-v5")]

    assert _source_labels(paths, [path.name for path in paths]) == [
        "donut-both-v3",
        "donut-both-v5",
    ]


def test_labels_deepen_only_as_far_as_they_must_to_separate():
    # Two runs three directories apart still only need the one that differs.
    paths = [
        Path("a/run-one/donut/checkpoint-100"),
        Path("a/run-two/donut/checkpoint-100"),
    ]

    labels = _source_labels(paths, [path.name for path in paths])

    assert len(set(labels)) == 2
    assert all(label.endswith("checkpoint-100") for label in labels)


def test_a_recorded_read_cannot_collide_with_a_checkpoint_of_the_same_name():
    # Reads are named by stem and checkpoints by directory, so the two can
    # produce the same label. Labelling them in separate passes would let one
    # silently replace the other in the report table.
    paths = [Path("baseline/donut-both-v3.json"), Path("out/donut-both-v3")]

    labels = _source_labels(paths, [paths[0].stem, paths[1].name])

    assert len(set(labels)) == 2
