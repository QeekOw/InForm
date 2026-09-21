"""Module 4 — bounded coaching-note generation and deterministic plan assembly."""

import re
from typing import Protocol

from inform.master import CoachingDraft, DailyPlan, MasterPayload
from inform.synthesis.validate import (
    generate_fallback_plan,
    validate_no_mutation,
)

_SYSTEM_PROMPT = """Write one short, encouraging coaching note.
It may discuss motivation, consistency, and the person's confirmed fitness goal.
Do not include numbers, quantities, nutrition units, exercise names or prescriptions,
imbalance findings, or medical or diagnostic claims. The backend renders every
actionable fact separately from deterministic data.
"""

_UNSAFE_COACHING_CONTENT = re.compile(
    r"\d|%|\b(?:"
    r"kcal|kilocalories?|calories?|grams?|g|mg|milligrams?|mcg|micrograms?|"
    r"kg|kilograms?|lbs?|pounds?|oz|ounces?|ml|milliliters?|liters?|percent|"
    r"protein|carbohydrates?|carbs?|fiber|macros?|macronutrients?|nutrition|diet|meals?|"
    r"food|snacks?|fasting|workouts?|exercises?|training|sets?|reps?|repetitions?|"
    r"aim|avoid|skip|eat|consume|drink|limit|reduce|increase|decrease|perform|target|"
    r"complete|replace|substitute|prescribe|recommend|should|must|try|ensure|"
    r"do|run|walk|lift|stretch|rest|sleep|fast|choose|diagnos\w*|injur\w*|"
    r"pain|disease|symptoms?|treat\w*|cure|imbalance|asymmetr\w*|weaker|stronger"
    r")\b",
    re.IGNORECASE,
)


class OpenAIClientProtocol(Protocol):
    """Protocol matching the OpenAI SDK chat completion interface for dependency injection."""

    beta: object


def _build_user_prompt(master: MasterPayload) -> str:
    return f"Write a coaching note for someone pursuing {master.user.fitness_goal}."


def _normalized_words(value: str) -> str:
    return " " + re.sub(r"\W+", " ", value.casefold()).strip() + " "


def _validated_coaching_text(draft: CoachingDraft, master: MasterPayload) -> str:
    text = draft.coaching_text.strip()
    normalized = _normalized_words(text)
    plan_terms = [
        value
        for exercise in master.exercises.exercises
        for value in (
            exercise.name,
            exercise.target,
            exercise.body_part,
            exercise.equipment,
            *exercise.secondary_muscles,
        )
    ]
    plan_terms.extend(master.exercises.detected_imbalances)
    plan_terms.extend(master.exercises.unconfirmed_imbalance_pairs)
    if (
        not text
        or _UNSAFE_COACHING_CONTENT.search(text)
        or any(_normalized_words(term) in normalized for term in plan_terms if term)
    ):
        raise ValueError("Coaching notes must be qualitative and non-actionable.")
    return text


def synthesize_plan(
    master: MasterPayload,
    client: OpenAIClientProtocol | None = None,
    model: str = "gpt-4o-mini",
) -> DailyPlan:
    """Synthesize the human-readable daily plan from deterministic outputs.

    Uses OpenAI Structured Outputs for a qualitative coaching draft, appends
    backend-rendered facts, and runs ``validate_no_mutation`` before returning.
    Invalid output or an API failure falls back to ``generate_fallback_plan``.
    """
    if client is None:
        try:
            from openai import OpenAI

            client = OpenAI()
        except Exception:
            return generate_fallback_plan(master)

    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(master)},
            ],
            response_format=CoachingDraft,
        )
        draft = completion.choices[0].message.parsed
        if draft is None:
            return generate_fallback_plan(master)
        coaching_text = _validated_coaching_text(draft, master)
        base_plan = generate_fallback_plan(master)
        plan = base_plan.model_copy(
            update={
                "narrative_text": f"# Coaching Note\n\n{coaching_text}\n\n"
                + base_plan.narrative_text,
                "narrative_source": "generated",
            }
        )
        return validate_no_mutation(master, plan)
    except Exception:
        # Invalid generated content, integrity failure, or API failure: fail closed.
        return generate_fallback_plan(master)
