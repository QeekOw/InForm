import sys
from pathlib import Path

# The inform package lives in the repository root (src/inform).
# Modules 2 & 3 are pure Pydantic models and deterministic calculations
# with lightweight dependencies, so adding the root src directory to sys.path
# allows direct importing without requiring a full editable package installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, model_validator

from inform.exercise import ExercisePlan
from inform.exercise_filter import recommend_exercises
from inform.exercise_pool import DEFAULT_EXERCISE_POOL
from inform.inbody import InBodyExtraction, InBodyPayload
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
        raise HTTPException(status_code=404, detail=f"Sample image not found on disk")

    return FileResponse(img_path, media_type="image/png")


class PlanRequest(BaseModel):
    user: UserProfile
    # Exactly one: a Sample sheet whose stored read the server plans from, or
    # a reading the caller supplies (the edit screen, until the correction flow).
    sample_id: str | None = None
    inbody: InBodyPayload | None = None

    @model_validator(mode="after")
    def _one_reading_source(self) -> "PlanRequest":
        if (self.sample_id is None) == (self.inbody is None):
            raise ValueError("Provide exactly one of sample_id or inbody")
        return self


def get_llm_client() -> OpenAIClientProtocol | None:
    """Module 4's LLM client; None lets synthesize_plan build the default one.

    A FastAPI dependency so tests can inject a fake client."""
    return None


def _inbody_for_plan(request: PlanRequest) -> InBodyPayload:
    if request.inbody is not None:
        return request.inbody
    extraction = load_extractions().extractions.get(request.sample_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail=f"Sample '{request.sample_id}' not found")
    # A refused read carries no data; as_payload refuses an unread or flagged one.
    inbody = (
        InBodyExtraction(
            data=extraction.data, unread=extraction.unread, flagged=extraction.flagged
        ).as_payload()
        if extraction.data is not None
        else None
    )
    if inbody is None:
        # Fail-closed (ADR-0008): an unread, flagged or refused read never
        # becomes a plan without a person acting on it.
        raise HTTPException(
            status_code=409,
            detail={
                "message": "This read needs a person to fill in or confirm fields before a plan can be built.",
                "unread": extraction.unread,
                "flagged": extraction.flagged,
            },
        )
    return inbody


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
    inbody = _inbody_for_plan(request)
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
    )
