import sys
from pathlib import Path

# The inform package lives in the sibling Track A repo layout (src/inform),
# not installed into this service's environment — Modules 2 & 3 are pure
# pydantic with no heavy deps (see CLAUDE.md agent-handoff notes), so this
# sys.path addition is enough rather than packaging/installing inform here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from inform.exercise import ExercisePlan
from inform.exercise_filter import recommend_exercises
from inform.exercise_pool import DEFAULT_EXERCISE_POOL
from inform.inbody import InBodyPayload
from inform.master import MasterPayload
from inform.nutrition import NutritionTargets
from inform.nutrition_engine import compute_targets
from inform.samples import (
    ExtractionItem,
    load_extractions,
    load_manifest,
)
from inform.synthesis.generate import synthesize_plan
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
    return {"service": "inform-api", "status": "ok"}


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
    inbody: InBodyPayload


class PlanResponse(BaseModel):
    # The deterministic numbers (Modules 2 & 3) alongside the narrative
    # (Module 4), not folded into it — "deterministic numbers, generative
    # prose only" means the UI should show the audited figures directly
    # rather than trust them only as restated inside the generated text.
    nutrition: NutritionTargets
    exercises: ExercisePlan
    narrative_text: str


@app.post("/plan")
def plan(request: PlanRequest) -> PlanResponse:
    """Modules 2 -> 3 -> 4, given an already-complete InBody reading.

    No OCR (Module 1) here — the caller supplies the reading values directly,
    same shape a completed correction flow would produce. Module 4 falls back
    to a deterministic plan automatically when no OPENAI_API_KEY is set.
    """
    nutrition = compute_targets(request.user, request.inbody)
    exercises = recommend_exercises(request.user, request.inbody, DEFAULT_EXERCISE_POOL)
    master = MasterPayload(
        user=request.user,
        inbody=request.inbody,
        nutrition=nutrition,
        exercises=exercises,
    )
    daily_plan = synthesize_plan(master, client=None)
    return PlanResponse(
        nutrition=nutrition,
        exercises=exercises,
        narrative_text=daily_plan.narrative_text,
    )
