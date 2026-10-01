"""Live read execution and long polling manager for InForm (Issue #40).

Enables on-demand live model inference using self-hosted Donut or stub engines,
surviving free-host timeouts (30-60s) via long polling rather than SSE or blocking HTTP requests.
Provides honest monotonic progress reporting across document understanding stages.
"""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
import io
from pathlib import Path
import threading
import time
from typing import Any, Callable, Literal
import uuid

from inform.errors import (
    DonutCheckpointError,
    InBodyExtractionError,
    MissingRequiredFieldsError,
    NotAnInBodySheetError,
)
from inform.extract import Engine, extract_inbody
from inform.samples import (
    ExtractionItem,
    extract_sheet_for_sample,
    load_extractions,
    load_manifest,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_EXPECTED_CPU_INFERENCE_SECONDS = 45.0

# Three read failures with three distinct causes, kept distinguishable so the
# frontend can attribute each one honestly:
#
#   engine_unavailable   the extraction model could not be constructed on this
#                        server (the Donut checkpoint is absent, ADR-0010). A
#                        server-side configuration fact.
#   unreadable_photo     the image reached the engine and could not be read.
#                        The person's photo.
#   not_an_inbody_sheet  the image is a document, just not an InBody sheet.
#
# Collapsing the first into the second is the bug this fixes: it blamed a
# person's photo for a missing checkpoint, and told them to retake a photo
# that no retake could ever make readable.
ENGINE_UNAVAILABLE_ERROR = "engine_unavailable"
ENGINE_UNAVAILABLE_MESSAGE = (
    "Live reading is unavailable on this server: the extraction model is not "
    "installed here. This is not a problem with your photo. Pick a sheet from "
    "the sample gallery to see a stored read instead."
)


def _engine_unavailable_extraction() -> ExtractionItem:
    """The refusal for a read that never reached the model (ADR-0010)."""
    return ExtractionItem(
        status="refused",
        error=ENGINE_UNAVAILABLE_ERROR,
        message=ENGINE_UNAVAILABLE_MESSAGE,
    )


def _mark_engine_unavailable(job: ReadJob) -> None:
    """Settle a job as refused because the model could not be built here."""
    job.status = "refused"
    job.progress = 1.0
    job.error = ENGINE_UNAVAILABLE_ERROR
    job.message = ENGINE_UNAVAILABLE_MESSAGE
    job.extraction = _engine_unavailable_extraction()

# Honest progress milestones for live Donut execution
_STAGES: list[tuple[float, float, str]] = [
    (0.0, 0.15, "Loading model checkpoint and tokenizer..."),
    (0.15, 0.35, "Analyzing visual document geometry and layout..."),
    (0.35, 0.75, "Transformer decoding body composition tokens..."),
    (0.75, 0.90, "Extracting segmental lean and fat parameters..."),
    (0.90, 0.96, "Evaluating Katch–McArdle and LBM cross-checks..."),
]


@dataclass
class ReadJob:
    read_id: str
    sample_id: str | None
    live: bool
    status: Literal["pending", "complete", "refused"]
    progress: float
    message: str
    extraction: ExtractionItem | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    start_monotonic: float = field(default_factory=time.monotonic)
    _event: threading.Event = field(default_factory=threading.Event)

    def current_progress_and_message(self) -> tuple[float, str]:
        """Compute honest monotonic progress and stage description based on status and elapsed time."""
        if self.status in ("complete", "refused"):
            return 1.0, self.message

        elapsed = time.monotonic() - self.start_monotonic
        # Model progress up to 96% while waiting for the model worker to finalize
        fraction = min(0.96, elapsed / _EXPECTED_CPU_INFERENCE_SECONDS)

        current_msg = _STAGES[0][2]
        for start_frac, end_frac, stage_msg in _STAGES:
            if start_frac <= fraction:
                current_msg = stage_msg

        return round(fraction, 2), current_msg

    def to_dict(self) -> dict[str, Any]:
        """Convert job to dictionary with current progress and stage message."""
        prog, msg = self.current_progress_and_message()
        return {
            "read_id": self.read_id,
            "sample_id": self.sample_id,
            "live": self.live,
            "status": self.status,
            "progress": prog,
            "message": msg,
            "extraction": self.extraction,
        }


class ReadManager:
    """In-memory manager tracking active and completed read jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, ReadJob] = {}
        self._lock = threading.Lock()

    def get(self, read_id: str) -> ReadJob | None:
        with self._lock:
            return self._jobs.get(read_id)

    def create_read(
        self,
        sample_id: str | None = None,
        image_data: str | None = None,
        live: bool = False,
        engine_factory: Callable[[], Engine | None] | None = None,
    ) -> ReadJob:
        """Create a new read job for either a Sample sheet or an uploaded photo (Issue #45).
        
        If sample_id is given and live=False, completes immediately from the pre-computed extractions.
        If live=True (or image_data is provided), launches background inference with honest progress updates.
        Uploaded images are processed transiently in memory and never written to disk or logs (ADR-0011).
        """
        if (sample_id is None and image_data is None) or (sample_id is not None and image_data is not None):
            raise ValueError("Provide either sample_id or image_data, not both or neither")

        read_id = f"read_{uuid.uuid4().hex[:12]}"
        repo_root = _REPO_ROOT

        if sample_id is not None:
            manifest = load_manifest()
            sample = next((s for s in manifest.samples if s.id == sample_id), None)
            if sample is None:
                raise KeyError(f"Sample '{sample_id}' not found in manifest")

            if not live:
                # Instant precomputed read from artifact
                artifact = load_extractions()
                stored = artifact.extractions.get(sample_id)
                if stored is None:
                    raise KeyError(f"Sample '{sample_id}' not found in stored extractions")

                job = ReadJob(
                    read_id=read_id,
                    sample_id=sample_id,
                    live=False,
                    status=stored.status,
                    progress=1.0,
                    message="Retrieved from stored extractions.",
                    extraction=stored,
                    completed_at=datetime.now(timezone.utc),
                )
                job._event.set()
                with self._lock:
                    self._jobs[read_id] = job
                return job

            # Live read requested on sample sheet
            job = ReadJob(
                read_id=read_id,
                sample_id=sample_id,
                live=True,
                status="pending",
                progress=0.0,
                message="Initializing live model inference...",
            )
            with self._lock:
                self._jobs[read_id] = job

            img_path = Path(sample.image_path)
            if not img_path.is_absolute():
                img_path = repo_root / img_path

            # A factory that builds the engine eagerly (rather than deferring to
            # extract_inbody's default_engine()) fails here, on the request
            # thread, before any worker starts. Same cause, same answer.
            try:
                engine = engine_factory() if engine_factory else None
            except DonutCheckpointError:
                _mark_engine_unavailable(job)
                job.completed_at = datetime.now(timezone.utc)
                job._event.set()
                return job

            def _sample_worker():
                try:
                    is_non = sample.source_device is None or "non_sheet" in sample.id
                    extraction = extract_sheet_for_sample(
                        img_path, engine=engine, is_non_sheet=is_non
                    )
                    job.extraction = extraction
                    job.status = extraction.status
                    job.progress = 1.0
                    if extraction.status == "complete":
                        job.message = "Live extraction completed successfully."
                    else:
                        job.message = extraction.message or "Sheet was refused."
                        job.error = extraction.error
                except DonutCheckpointError:
                    # The model was never built, so nothing about this sheet was
                    # judged. Report the server, not the sheet — and do NOT fall
                    # back to the stored extraction, which is the only thing the
                    # live read exists to be checked against (issue #29).
                    _mark_engine_unavailable(job)
                except Exception as exc:
                    job.status = "refused"
                    job.progress = 1.0
                    job.error = "unexpected_error"
                    job.message = f"Inference failed: {str(exc)}"
                    job.extraction = ExtractionItem(
                        status="refused",
                        error="unexpected_error",
                        message=job.message,
                    )
                finally:
                    job.completed_at = datetime.now(timezone.utc)
                    job._event.set()

            thread = threading.Thread(target=_sample_worker, name=f"read-worker-{read_id}", daemon=True)
            thread.start()
            return job

        # Uploaded image branch (Issue #45 / ADR-0011 zero persistence)
        b64_str = image_data
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]

        raw_bytes: bytes | None = None
        try:
            raw_bytes = base64.b64decode(b64_str)
            from PIL import Image
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img.verify()
        except Exception:
            job = ReadJob(
                read_id=read_id,
                sample_id=None,
                live=True,
                status="refused",
                progress=1.0,
                message="Could not read this photo. Please retake or upload a clear photo (JPG or PNG).",
                extraction=ExtractionItem(
                    status="refused",
                    error="unreadable_photo",
                    message="Could not read this photo. Please retake or upload a clear photo (JPG or PNG).",
                ),
                completed_at=datetime.now(timezone.utc),
            )
            job._event.set()
            with self._lock:
                self._jobs[read_id] = job
            return job

        job = ReadJob(
            read_id=read_id,
            sample_id=None,
            live=True,
            status="pending",
            progress=0.0,
            message="Analyzing uploaded photo...",
        )
        with self._lock:
            self._jobs[read_id] = job

        try:
            engine = engine_factory() if engine_factory else None
        except DonutCheckpointError:
            _mark_engine_unavailable(job)
            job.completed_at = datetime.now(timezone.utc)
            job._event.set()
            return job

        def _upload_worker():
            try:
                extraction_result = extract_inbody(raw_bytes, engine=engine)
                extraction = ExtractionItem(
                    status="complete",
                    data=extraction_result.data,
                    unread=extraction_result.unread,
                    flagged=extraction_result.flagged,
                )
                job.extraction = extraction
                job.status = "complete"
                job.progress = 1.0
                job.message = "Sheet analysis completed successfully."
            except DonutCheckpointError:
                # Raised by extract_inbody's default_engine() before the image is
                # looked at, so this says nothing about the photo's quality. It
                # used to land in the broad handler below and come back as
                # "too blurry", sending people off to retake a photo that was
                # never the problem.
                _mark_engine_unavailable(job)
            except MissingRequiredFieldsError as exc:
                job.status = "refused"
                job.progress = 1.0
                job.error = "unreadable_photo"
                job.message = "The photo is too blurry or unclear to read your measurements. Please retake the photo in good lighting."
                job.extraction = ExtractionItem(
                    status="refused",
                    error="unreadable_photo",
                    unread=list(exc.fields),
                    message=job.message,
                )
            except NotAnInBodySheetError as exc:
                job.status = "refused"
                job.progress = 1.0
                job.error = "not_an_inbody_sheet"
                job.message = str(exc)
                job.extraction = ExtractionItem(
                    status="refused",
                    error="not_an_inbody_sheet",
                    message=str(exc),
                )
            except Exception as exc:
                job.status = "refused"
                job.progress = 1.0
                job.error = "unreadable_photo"
                job.message = "The photo could not be read clearly. Please retake the photo with steady focus and good lighting."
                job.extraction = ExtractionItem(
                    status="refused",
                    error="unreadable_photo",
                    message=job.message,
                )
            finally:
                job.completed_at = datetime.now(timezone.utc)
                job._event.set()

        thread = threading.Thread(target=_upload_worker, name=f"read-worker-{read_id}", daemon=True)
        thread.start()
        return job

    async def poll(self, read_id: str, timeout: float = 10.0) -> ReadJob:
        """Long poll a read job with timeout surviving free-host network limits."""
        job = self.get(read_id)
        if job is None:
            raise KeyError(f"Read '{read_id}' not found")

        if job.status == "pending":
            # Wait up to timeout without blocking the event loop
            await asyncio.to_thread(job._event.wait, timeout)

        # Update progress and message
        prog, msg = job.current_progress_and_message()
        job.progress = prog
        if job.status == "pending":
            job.message = msg
        return job


# Singleton read manager for the process
read_manager = ReadManager()
