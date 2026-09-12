"""Pre-computed Sample sheet manifest and extractions artifact handler (Issue #32).

Manages the Sample sheet gallery manifest (provenance: synthetic vs real printouts)
and the pre-computed extractions artifact. The artifact records clean reads, unread
fields, flagged cross-checks, and refusals exactly as produced by the model checkpoint.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

from inform.errors import (
    InBodyExtractionError,
    MissingRequiredFieldsError,
    NotAnInBodySheetError,
)
from inform.extract import Engine, default_engine, extract_inbody
from inform.inbody import PartialInBody

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_MANIFEST_PATH = _REPO_ROOT / "data" / "samples" / "manifest.json"
_DEFAULT_EXTRACTIONS_PATH = _REPO_ROOT / "data" / "samples" / "extractions.json"
_DEFAULT_CKPT = "models/donut-both-v3"
_DONUT_CKPT_ENV = "INFORM_DONUT_CKPT"


class SampleSheet(BaseModel):
    """Metadata describing a single Sample sheet in the gallery."""

    id: str
    name: str
    provenance: Literal["synthetic", "real"]
    source_device: Literal["inbody_270", "inbody_570"] | None = None
    image_path: str
    description: str


class SampleManifest(BaseModel):
    """The committed manifest of Sample sheets."""

    samples: list[SampleSheet]


class ExtractionItem(BaseModel):
    """Recorded model extraction or refusal for a single Sample sheet."""

    status: Literal["complete", "refused"]
    data: PartialInBody | None = None
    unread: list[str] = Field(default_factory=list)
    flagged: list[str] = Field(default_factory=list)
    error: str | None = None
    message: str | None = None


class SampleExtractionsArtifact(BaseModel):
    """Regenerable build artifact holding pre-computed sample extractions."""

    checkpoint: str
    generated_at: str
    extractions: dict[str, ExtractionItem]


def default_manifest_path() -> Path:
    return _DEFAULT_MANIFEST_PATH


def default_extractions_path() -> Path:
    return _DEFAULT_EXTRACTIONS_PATH


def current_checkpoint_id() -> str:
    return os.environ.get(_DONUT_CKPT_ENV, _DEFAULT_CKPT)


def load_manifest(path: Path | str | None = None) -> SampleManifest:
    """Load the Sample sheet manifest from disk."""
    p = Path(path) if path is not None else default_manifest_path()
    if not p.is_absolute():
        p = _REPO_ROOT / p
    if not p.exists():
        raise FileNotFoundError(f"Sample manifest not found at {p}")
    return SampleManifest.model_validate_json(p.read_text(encoding="utf-8"))


def load_extractions(path: Path | str | None = None) -> SampleExtractionsArtifact:
    """Load the pre-computed Sample extractions artifact from disk."""
    p = Path(path) if path is not None else default_extractions_path()
    if not p.is_absolute():
        p = _REPO_ROOT / p
    if not p.exists():
        raise FileNotFoundError(f"Sample extractions artifact not found at {p}")
    return SampleExtractionsArtifact.model_validate_json(p.read_text(encoding="utf-8"))


def extract_sheet_for_sample(
    image_path: Path, engine: Engine | None = None
) -> ExtractionItem:
    """Run extraction over a single sheet, capturing data, unread, flagged, or refusal."""
    try:
        extraction = extract_inbody(image_path, engine=engine)
        return ExtractionItem(
            status="complete",
            data=extraction.data,
            unread=extraction.unread,
            flagged=extraction.flagged,
        )
    except MissingRequiredFieldsError as exc:
        return ExtractionItem(
            status="refused",
            error="missing_required_fields",
            unread=list(exc.fields),
            message=str(exc),
        )
    except NotAnInBodySheetError as exc:
        return ExtractionItem(
            status="refused",
            error="not_an_inbody_sheet",
            message=str(exc),
        )
    except InBodyExtractionError as exc:
        return ExtractionItem(
            status="refused",
            error="extraction_error",
            message=str(exc),
        )


def generate_extractions(
    manifest: SampleManifest,
    engine: Engine | None = None,
    checkpoint_id: str | None = None,
    base_dir: Path | None = None,
) -> SampleExtractionsArtifact:
    """Run extraction over every sheet in the manifest and record the results."""
    root = base_dir or _REPO_ROOT
    ckpt = checkpoint_id or current_checkpoint_id()
    if engine is None:
        engine = default_engine()

    extractions: dict[str, ExtractionItem] = {}
    for sample in manifest.samples:
        img_path = Path(sample.image_path)
        if not img_path.is_absolute():
            img_path = root / img_path
        if not img_path.exists():
            raise FileNotFoundError(f"Sample image not found: {img_path}")

        extractions[sample.id] = extract_sheet_for_sample(img_path, engine=engine)

    return SampleExtractionsArtifact(
        checkpoint=ckpt,
        generated_at=datetime.now(timezone.utc).isoformat(),
        extractions=extractions,
    )


def diff_extractions(
    committed: SampleExtractionsArtifact, candidate: SampleExtractionsArtifact
) -> list[str]:
    """Compare two extractions artifacts and return differences (empty if match).

    Checks the checkpoint identity and every extraction item per sample ID.
    Ignores generated_at timestamps so identical model outputs are recognized.
    """
    diffs: list[str] = []

    if committed.checkpoint != candidate.checkpoint:
        diffs.append(
            f"Checkpoint mismatch: committed '{committed.checkpoint}' vs generated '{candidate.checkpoint}'"
        )

    committed_ids = set(committed.extractions.keys())
    candidate_ids = set(candidate.extractions.keys())

    for missing_id in sorted(committed_ids - candidate_ids):
        diffs.append(f"Sample '{missing_id}' missing in newly generated extractions")

    for extra_id in sorted(candidate_ids - committed_ids):
        diffs.append(f"Sample '{extra_id}' missing in committed extractions")

    common_ids = sorted(committed_ids & candidate_ids)
    for sample_id in common_ids:
        c_item = committed.extractions[sample_id].model_dump()
        n_item = candidate.extractions[sample_id].model_dump()
        if c_item != n_item:
            diffs.append(
                f"Sample '{sample_id}' extraction differs:\n  committed: {c_item}\n  generated: {n_item}"
            )

    return diffs
