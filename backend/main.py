import sys
from pathlib import Path

# The inform package lives in the repository root (src/inform).
# Modules 2 & 3 are pure Pydantic models and deterministic calculations
# with lightweight dependencies, so adding the root src directory to sys.path
# allows direct importing without requiring a full editable package installation.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from inform.exercise import ExercisePlan
from inform.exercise_filter import recommend_exercises
from inform.exercise_pool import DEFAULT_EXERCISE_POOL
from inform.inbody import InBodyPayload
from inform.master import MasterPayload
from inform.nutrition import NutritionTargets
from inform.nutrition_engine import compute_targets
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
    return {
        "service": "inform-api",
        "status": "ok",
        "docs_url": "/docs",
        "health_url": "/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "inform-api"}


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
    same shape a completed correction flow would produce.

    Privacy & ADR-0005: When OPENAI_API_KEY is unset, Module 4 automatically
    falls back to a deterministic, local template-based plan narrative so no
    data leaves the host environment. If OPENAI_API_KEY is configured, cloud
    synthesis is used for POC / development testing with consented or synthetic
    data only. Real patient health data must never be sent to external cloud APIs.
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
