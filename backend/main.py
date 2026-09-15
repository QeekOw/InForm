import sys
from pathlib import Path

# The inform package lives in the repository root (src/inform).
# Modules 2 & 3 are pure Pydantic models and deterministic calculations
# with lightweight dependencies, so adding the root src directory to sys.path
# allows direct importing without requiring a full editable package installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator

from inform.corrections import (
    CrossCheckFlaggedError,
    UnreadFieldsError,
    apply_corrections,
)
from inform.exercise import ExercisePlan
from inform.exercise_filter import recommend_exercises
from inform.exercise_pool import DEFAULT_EXERCISE_POOL
from inform.inbody import InBodyExtraction, InBodyPayload, PartialInBody
from inform.master import MasterPayload
from inform.nutrition import NutritionTargets
from inform.nutrition_engine import compute_targets
from inform.samples import (
    ExtractionItem,
    load_extractions,
    load_manifest,
)
from inform.synthesis.generate import OpenAIClientProtocol, synthesize_plan
from inform.synthesis.validate import generate_fallback_plan
from inform.user import UserProfile

app = FastAPI(title="InForm API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "inform-api",
        "status": "ok",
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "inform-api"}


class SampleGalleryItem(BaseModel):
    id: str
    name: str
    provenance: Literal["synthetic", "real"]
    source_device: Literal["inbody_270", "inbody_570"] | None = None
    image_url: str
    description: str


@app.get("/samples", response_model=list[SampleGalleryItem])
@app.get("/api/samples", response_model=list[SampleGalleryItem])
def list_samples() -> list[SampleGalleryItem]:
    """Return all sample sheets in the gallery manifest with provenance labels."""
    manifest = load_manifest()
    return [
        SampleGalleryItem(
            id=s.id,
            name=s.name,
            provenance=s.provenance,
            source_device=s.source_device,
            image_url=f"/samples/{s.id}/image",
            description=s.description,
        )
        for s in manifest.samples
    ]


@app.get("/samples/{sample_id}", response_model=ExtractionItem)
@app.get("/api/samples/{sample_id}", response_model=ExtractionItem)
def get_sample_extraction(sample_id: str) -> ExtractionItem:
    """Return precomputed extraction for a sample sheet instantly without running OCR."""
    extractions_artifact = load_extractions()
    if sample_id not in extractions_artifact.extractions:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found")
    return extractions_artifact.extractions[sample_id]


@app.get("/samples/{sample_id}/image")
@app.get("/api/samples/{sample_id}/image")
def get_sample_image(sample_id: str):
    """Serve the thumbnail/photo of a sample sheet from the repository."""
    manifest = load_manifest()
    sample = next((s for s in manifest.samples if s.id == sample_id), None)
    if sample is None:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found")

    img_path = Path(sample.image_path)
    if not img_path.is_absolute():
        repo_root = Path(__file__).resolve().parent.parent
        img_path = repo_root / img_path

    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Sample image not found on disk")

    return FileResponse(img_path, media_type="image/png")


class PlanRequest(BaseModel):
    user: UserProfile
    # A Sample sheet whose stored read the server plans from, with optional human corrections
    sample_id: str | None = None
    # An explicit measured read with optional human corrections
    measured: PartialInBody | None = None
    # Corrections typed by a person (recorded alongside measured fields, never merged into them)
    corrections: dict[str, Any] | None = None
    # Flagged fields confirmed unchanged by a person
    confirmations: list[str] | None = None
    confirmed_fields: list[str] | None = None
    # Direct InBody reading (retained for backward compatibility)
    inbody: InBodyPayload | None = None

    @model_validator(mode="after")
    def _validate_source(self) -> "PlanRequest":
        sources = [s is not None for s in (self.sample_id, self.measured, self.inbody)]
        if sum(sources) != 1:
            raise ValueError("Provide exactly one reading source (sample_id, measured, or inbody)")
        return self


def get_llm_client() -> OpenAIClientProtocol | None:
    """Module 4's LLM client; None lets synthesize_plan build the default one.

    A FastAPI dependency so tests can inject a fake client."""
    return None


def _apply_plan_corrections(
    base: PartialInBody,
    corrections: dict[str, Any] | None,
    confirmations: list[str] | None = None,
    source_device: Literal["inbody_270", "inbody_570"] | None = None,
    initial_flagged: list[str] | None = None,
) -> tuple[InBodyPayload, list[str], list[str]]:
    """Deduplicated helper to validate and apply corrections and confirmations, mapping domain exceptions to HTTP responses."""
    try:
        return apply_corrections(
            base,
            corrections or {},
            source_device=source_device,
            confirmations=confirmations,
            initial_flagged=initial_flagged,
        )
    except UnreadFieldsError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Building a plan is impossible while a required field remains unread.",
                "unread": exc.unread_fields,
            },
        )
    except CrossCheckFlaggedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Building a plan is impossible while a flagged field is unresolved.",
                "unread": [],
                "flagged": exc.flagged_fields,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


def _inbody_for_plan(request: PlanRequest) -> tuple[InBodyPayload, PartialInBody, list[str], list[str]]:
    """Resolve reading source into (effective_payload, base_measured, corrected_field_keys, confirmed_field_keys)."""
    confirmations = list(dict.fromkeys((request.confirmations or []) + (request.confirmed_fields or [])))

    if request.sample_id is not None:
        extraction = load_extractions().extractions.get(request.sample_id)
        if extraction is None:
            raise HTTPException(status_code=404, detail=f"Sample '{request.sample_id}' not found")

        # ADR-0008 Amendment §3: The zero-read floor case (data is None) or non-sheet is a hard refusal.
        # Partial extraction only applies once some real data is read.
        if extraction.data is None or extraction.status == "refused":
            message = (
                extraction.message
                or (
                    "This image does not appear to be an InBody result sheet. Please upload a clear photo of your InBody 270 or 570 sheet."
                    if extraction.error == "not_an_inbody_sheet"
                    else "This sheet was refused (not an InBody sheet or nothing readable came back)."
                )
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "message": message,
                    "unread": extraction.unread,
                    "flagged": extraction.flagged,
                    "error": extraction.error,
                },
            )

        base_measured = extraction.data
        if request.corrections or confirmations:
            payload, corrected, confirmed = _apply_plan_corrections(
                base_measured,
                request.corrections,
                confirmations=confirmations,
                source_device=base_measured.source_device,
                initial_flagged=extraction.flagged,
            )
            return payload, base_measured, corrected, confirmed

        # A complete read with no flags
        inbody = (
            InBodyExtraction(
                data=extraction.data, unread=extraction.unread, flagged=extraction.flagged
            ).as_payload()
        )
        if inbody is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Building a plan is impossible while a flagged field is unresolved.",
                    "unread": extraction.unread,
                    "flagged": extraction.flagged,
                },
            )
        return inbody, base_measured, [], []

    if request.measured is not None:
        base_measured = request.measured
        payload, corrected, confirmed = _apply_plan_corrections(
            base_measured,
            request.corrections,
            confirmations=confirmations,
            source_device=base_measured.source_device,
        )
        return payload, base_measured, corrected, confirmed

    if request.inbody is not None:
        base_measured = PartialInBody(**request.inbody.model_dump())
        payload, corrected, confirmed = _apply_plan_corrections(
            base_measured,
            request.corrections,
            confirmations=confirmations,
            source_device=request.inbody.source_device,
        )
        return payload, base_measured, corrected, confirmed

    raise HTTPException(status_code=422, detail="No reading source provided")


class PlanResponse(BaseModel):
    # The deterministic numbers (Modules 2 & 3) alongside the narrative
    # (Module 4), not folded into it — "deterministic numbers, generative
    # prose only" means the UI should show the audited figures directly
    # rather than trust them only as restated inside the generated text.
    nutrition: NutritionTargets
    exercises: ExercisePlan
    narrative_text: str
    # "fallback" when Module 4 dropped the LLM's text (unavailable, or it
    # mutated a number) and returned the plain deterministic plan instead.
    narrative_source: Literal["generated", "fallback"]
    # Recorded alongside measured fields, never merged into them
    measured: PartialInBody | None = None
    corrected_fields: list[str] = Field(default_factory=list)
    confirmed_fields: list[str] = Field(default_factory=list)


@app.post("/plan")
def plan(
    request: PlanRequest,
    llm_client: OpenAIClientProtocol | None = Depends(get_llm_client),
) -> PlanResponse:
    """Modules 2 -> 3 -> 4, given a Sample sheet's stored read or a complete reading.

    No OCR (Module 1) here. Module 4 falls back to a deterministic plan when
    the LLM is unavailable or mutates a number.

    Privacy & ADR-0005: When OPENAI_API_KEY is unset, Module 4 automatically
    falls back to a deterministic, local template-based plan narrative so no
    data leaves the host environment. If OPENAI_API_KEY is configured, cloud
    synthesis is used for POC / development testing with consented or synthetic
    data only. Real patient health data must never be sent to external cloud APIs.
    """
    inbody, base_measured, corrected_fields, confirmed_fields = _inbody_for_plan(request)
    nutrition = compute_targets(request.user, inbody)
    exercises = recommend_exercises(request.user, inbody, DEFAULT_EXERCISE_POOL)
    master = MasterPayload(
        user=request.user,
        inbody=inbody,
        nutrition=nutrition,
        exercises=exercises,
    )
    daily_plan = synthesize_plan(master, client=llm_client)
    return PlanResponse(
        nutrition=nutrition,
        exercises=exercises,
        narrative_text=daily_plan.narrative_text,
        narrative_source="fallback" if daily_plan == generate_fallback_plan(master) else "generated",
        measured=base_measured,
        corrected_fields=corrected_fields,
        confirmed_fields=confirmed_fields,
    )
