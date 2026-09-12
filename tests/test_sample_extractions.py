"""Tests for pre-computed Sample sheet manifest and extractions artifact (Issue #32)."""

import json
import os
from pathlib import Path
import pytest
from PIL import Image

from inform.errors import (
    InBodyExtractionError,
    MissingRequiredFieldsError,
    NotAnInBodySheetError,
)
from inform.inbody import PartialInBody, PartialSegmentalLean
from inform.samples import (
    ExtractionItem,
    SampleExtractionsArtifact,
    SampleManifest,
    SampleSheet,
    default_extractions_path,
    default_manifest_path,
    diff_extractions,
    extract_sheet_for_sample,
    generate_extractions,
    load_extractions,
    load_manifest,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_manifest_schema_and_provenance():
    """A committed manifest lists every Sample sheet with its provenance."""
    manifest = load_manifest()
    assert len(manifest.samples) >= 3, "Gallery must have multiple sample sheets"

    provenances = {s.provenance for s in manifest.samples}
    assert "synthetic" in provenances, "Must contain synthetic sample sheets"
    assert "real" in provenances, "Must contain real printout sample sheets"

    for sample in manifest.samples:
        assert sample.id, "Sample ID must not be empty"
        assert sample.name, f"Sample {sample.id} name must not be empty"
        assert sample.provenance in ("synthetic", "real")
        if sample.source_device is not None:
            assert sample.source_device in ("inbody_270", "inbody_570")

        img_path = _REPO_ROOT / sample.image_path
        assert img_path.exists(), f"Sample image file does not exist: {img_path}"
        assert sample.description, f"Sample {sample.id} description must not be empty"


def test_real_sheets_carry_no_member_id_or_gym_name():
    """Real sheets in the manifest carry no member ID or gym name (ADR-0011)."""
    manifest = load_manifest()
    real_samples = [s for s in manifest.samples if s.provenance == "real"]
    assert real_samples, "At least one real sheet must be present in manifest"

    # Known pixel coordinates for the Member ID and Gym Name bounding boxes on 270 sheets
    # ID box: [200, 780, 590, 930]
    # Gym box: [1450, 640, 2050, 820]
    for sample in real_samples:
        img_path = _REPO_ROOT / sample.image_path
        with Image.open(img_path) as img:
            rgb = img.convert("RGB")

            # Check ID area is completely solid white (redacted)
            id_crop = rgb.crop((200, 780, 590, 930))
            id_colors = id_crop.getcolors(maxcolors=10)
            assert id_colors is not None and len(id_colors) == 1, (
                f"Real sheet {sample.id} has non-uniform pixels in member ID area"
            )
            count, color = id_colors[0]
            assert color == (255, 255, 255), f"Member ID area not redacted in {sample.id}"

            # Check Gym Name area is completely solid white (redacted)
            gym_crop = rgb.crop((1450, 640, 2050, 820))
            gym_colors = gym_crop.getcolors(maxcolors=10)
            assert gym_colors is not None and len(gym_colors) == 1, (
                f"Real sheet {sample.id} has non-uniform pixels in gym name area"
            )
            count, color = gym_colors[0]
            assert color == (255, 255, 255), f"Gym name area not redacted in {sample.id}"


def test_committed_extractions_structure_and_coverage():
    """The committed output records checkpoint, clean reads, flagged fields, and refusals."""
    manifest = load_manifest()
    artifact = load_extractions()

    assert artifact.checkpoint, "Artifact must record which checkpoint produced it"
    assert artifact.generated_at, "Artifact must record generation timestamp"

    # Every sample in the manifest must be in the artifact
    for sample in manifest.samples:
        assert sample.id in artifact.extractions, (
            f"Sample '{sample.id}' missing from committed extractions"
        )

    # Verify presence of clean read, flagged read, and refusal
    statuses = [item.status for item in artifact.extractions.values()]
    assert "complete" in statuses, "Must have complete reads"
    assert "refused" in statuses, "A sheet the model refuses is recorded as a refusal rather than omitted"

    flagged_counts = [len(item.flagged) for item in artifact.extractions.values()]
    assert any(c > 0 for c in flagged_counts), "Must contain at least one flagged read"
    assert any(c == 0 for c in flagged_counts), "Must contain clean reads"

    # Check the refusal record
    refused_items = [item for item in artifact.extractions.values() if item.status == "refused"]
    for ref in refused_items:
        assert ref.data is None
        assert ref.error is not None, "Refusal must specify an error code"
        assert ref.message is not None, "Refusal must provide an explanation message"


def test_stub_extraction_records_refusals_and_flags():
    """Verify that extract_sheet_for_sample records refusals and flagged reads without omitting."""
    # Test floor case refusal
    def stub_floor(path):
        raise MissingRequiredFieldsError(["weight_kg", "lean_body_mass_kg"])

    item_floor = extract_sheet_for_sample(Path("dummy.png"), engine=stub_floor)
    assert item_floor.status == "refused"
    assert item_floor.error == "missing_required_fields"
    assert "weight_kg" in item_floor.unread
    assert item_floor.data is None

    # Test not an InBody sheet refusal
    def stub_not_inbody(path):
        raise NotAnInBodySheetError()

    item_non = extract_sheet_for_sample(Path("dummy.png"), engine=stub_not_inbody)
    assert item_non.status == "refused"
    assert item_non.error == "not_an_inbody_sheet"

    # Test generic extraction error refusal
    def stub_error(path):
        raise InBodyExtractionError("Corrupted payload")

    item_err = extract_sheet_for_sample(Path("dummy.png"), engine=stub_error)
    assert item_err.status == "refused"
    assert item_err.error == "extraction_error"

    # Test flagged cross-check read
    def stub_flagged(path):
        return PartialInBody(
            weight_kg=80.0,
            lean_body_mass_kg=30.0,  # Cross-check breach: 80 * (1 - 0.20) = 64 != 30
            percent_body_fat=20.0,
            skeletal_muscle_mass_kg=32.0,
            basal_metabolic_rate_kcal=1600.0,
            segmental_lean=PartialSegmentalLean(
                left_arm_kg=3.0, right_arm_kg=3.0, left_leg_kg=8.0, right_leg_kg=8.0, trunk_kg=22.0
            ),
            source_device="inbody_270",
        )

    item_flagged = extract_sheet_for_sample(Path("dummy.png"), engine=stub_flagged)
    assert item_flagged.status == "complete"
    assert item_flagged.data.weight_kg == 80.0
    assert "lean_body_mass_kg" in item_flagged.flagged


def test_diff_extractions_detects_changes():
    """diff_extractions accurately flags discrepancies between committed and candidate artifacts."""
    base = SampleExtractionsArtifact(
        checkpoint="models/donut-both-v3",
        generated_at="2026-09-13T00:00:00Z",
        extractions={
            "s1": ExtractionItem(
                status="complete",
                data=PartialInBody(weight_kg=70.0),
                unread=[],
                flagged=[],
            ),
            "s2": ExtractionItem(
                status="refused",
                error="not_an_inbody_sheet",
                message="Not a sheet",
            ),
        },
    )

    # Identical content (even with different timestamp) produces no diff
    candidate_same = SampleExtractionsArtifact(
        checkpoint="models/donut-both-v3",
        generated_at="2026-09-13T01:00:00Z",
        extractions=base.extractions.copy(),
    )
    assert diff_extractions(base, candidate_same) == []

    # Checkpoint mismatch
    candidate_ckpt = candidate_same.model_copy(update={"checkpoint": "other-ckpt"})
    assert any("Checkpoint mismatch" in d for d in diff_extractions(base, candidate_ckpt))

    # Missing sample
    candidate_missing = candidate_same.model_copy(
        update={"extractions": {"s1": base.extractions["s1"]}}
    )
    assert any("missing in newly generated" in d for d in diff_extractions(base, candidate_missing))

    # Mutated value
    mutated_item = base.extractions["s1"].model_copy(deep=True)
    mutated_item.data.weight_kg = 75.0
    candidate_mutated = candidate_same.model_copy(
        update={"extractions": {"s1": mutated_item, "s2": base.extractions["s2"]}}
    )
    assert any("extraction differs" in d for d in diff_extractions(base, candidate_mutated))

    # Mutated status (from refused to complete)
    mutated_status = base.extractions["s2"].model_copy(
        update={"status": "complete", "data": PartialInBody(weight_kg=60.0), "error": None}
    )
    candidate_status = candidate_same.model_copy(
        update={"extractions": {"s1": base.extractions["s1"], "s2": mutated_status}}
    )
    assert any("extraction differs" in d for d in diff_extractions(base, candidate_status))


def test_committed_extractions_match_live_checkpoint():
    """A check fails when the committed extractions differ from what the script produces."""
    ckpt_path = Path("models/donut-both-v3")
    if not ckpt_path.exists() and "INFORM_DONUT_CKPT" not in os.environ:
        pytest.skip("Checkpoint models/donut-both-v3 not found locally; skipping live inference check")

    committed = load_extractions()
    manifest = load_manifest()
    fresh = generate_extractions(manifest)

    diffs = diff_extractions(committed, fresh)
    assert diffs == [], f"Committed extractions differ from live checkpoint output:\n" + "\n".join(diffs)
