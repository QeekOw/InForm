from pathlib import Path

from inform.errors import IncompleteExtractionError
from inform.exercise import Exercise
from inform.exercise_filter import recommend_exercises
from inform.extract import Engine, extract_inbody
from inform.inbody import InBodyPayload
from inform.master import DailyPlan, MasterPayload
from inform.nutrition_engine import compute_targets
from inform.synthesis.generate import OpenAIClientProtocol, synthesize_plan
from inform.user import UserProfile


def build_master_payload(
    inbody: InBodyPayload,
    user: UserProfile,
    exercise_pool: list[Exercise],
    confirmed_fields: set[str] | None = None,
) -> MasterPayload:
    """Run Modules 2 & 3 to assemble the intermediate MasterPayload from an InBodyPayload."""
    nutrition = compute_targets(user, inbody)
    exercises = recommend_exercises(user, inbody, exercise_pool, confirmed_fields)

    return MasterPayload(user=user, inbody=inbody, nutrition=nutrition, exercises=exercises)


def build_plan(
    inbody: InBodyPayload,
    user: UserProfile,
    exercise_pool: list[Exercise],
    llm_client: OpenAIClientProtocol | None = None,
    model: str = "gpt-4o-mini",
    confirmed_fields: set[str] | None = None,
) -> DailyPlan:
    """Run Modules 2 to 4 to build a DailyPlan from an already-complete InBody payload.

    Takes a validated InBodyPayload (plus UserProfile and exercise pool) and computes
    nutrition targets (Module 2), exercise recommendations (Module 3), and synthesizes
    the final empathetic DailyPlan with dual-validation (Module 4).
    """
    master = build_master_payload(inbody, user, exercise_pool, confirmed_fields)
    return synthesize_plan(master, client=llm_client, model=model)


def assemble_master_payload(
    image_path: Path,
    user: UserProfile,
    exercise_pool: list[Exercise],
    engine: Engine | None = None,
    confirmed_fields: set[str] | None = None,
) -> MasterPayload:
    """Run Modules 1 -> 2 & 3 to assemble the intermediate MasterPayload.

    `engine` selects the Module 1 OCR engine; None resolves to the default
    self-hosted Donut engine (ADR-0010). Pass one explicitly (e.g. the VLM
    oracle) to override.
    """
    extraction = extract_inbody(image_path, engine=engine)
    inbody = extraction.as_payload()
    if inbody is None:
        raise IncompleteExtractionError(extraction.unread, extraction.flagged)

    return build_master_payload(inbody, user, exercise_pool, confirmed_fields)


def run_pipeline(
    image_path: Path,
    user: UserProfile,
    exercise_pool: list[Exercise],
    llm_client: OpenAIClientProtocol | None = None,
    model: str = "gpt-4o-mini",
    engine: Engine | None = None,
    confirmed_fields: set[str] | None = None,
) -> DailyPlan:
    """Orchestrator: Module 1 -> Modules 2 and 3 (independent) -> MasterPayload -> Module 4 -> DailyPlan.

    exercise_pool is passed through to Module 3 (see exercise_filter.py).
    Module 4 adds optional coaching to a deterministic DailyPlan and validates final assembly.
    `engine` selects the Module 1 OCR engine; None uses the default Donut engine (ADR-0010).
    """
    master = assemble_master_payload(
        image_path, user, exercise_pool, engine=engine, confirmed_fields=confirmed_fields
    )
    return synthesize_plan(master, client=llm_client, model=model)
