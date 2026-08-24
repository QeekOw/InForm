from pathlib import Path

from inform.errors import IncompleteExtractionError
from inform.exercise import Exercise
from inform.exercise_filter import recommend_exercises
from inform.extract import extract_inbody
from inform.master import MasterPayload
from inform.nutrition_engine import compute_targets
from inform.user import UserProfile


def run_pipeline(
    image_path: Path, user: UserProfile, exercise_pool: list[Exercise]
) -> MasterPayload:
    """Orchestrator: Module 1 -> Modules 2 and 3 (independent) -> MasterPayload.

    exercise_pool is passed through to Module 3 (see exercise_filter.py) — the
    real hasaneyldrm/exercises-dataset isn't vendored in this repo yet.

    Module 4 (LLM synthesis, issue #15) is not wired in here: MasterPayload is
    this pipeline's terminal output until that module exists.
    """
    extraction = extract_inbody(image_path)
    inbody = extraction.as_payload()
    if inbody is None:
        raise IncompleteExtractionError(extraction.unread, extraction.flagged)

    nutrition = compute_targets(user, inbody)
    exercises = recommend_exercises(user, inbody, exercise_pool)

    return MasterPayload(user=user, inbody=inbody, nutrition=nutrition, exercises=exercises)
