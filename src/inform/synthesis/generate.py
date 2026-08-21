"""Module 4 — Natural Language Generation interface (LLM Synthesis).

Injects the consolidated Master JSON into a zero-shot LLM (OpenAI Structured Outputs)
that acts strictly as a linguistic synthesizer, producing an empathetic daily plan
without altering any deterministic number.
"""

from typing import Protocol

from inform.master import DailyPlan, MasterPayload
from inform.synthesis.validate import (
    NumericalMutationError,
    generate_fallback_plan,
    validate_no_mutation,
)

_SYSTEM_PROMPT = """You are an empathetic, supportive, and knowledgeable AI personal fitness and nutrition coach.
Your role is to write a personalized, motivating daily fitness and nutrition guide for the user based strictly on their assessment data.

Guidelines:
1. Address the user's specific fitness goal (hypertrophy or fat loss) encouragingly.
2. If muscle asymmetries or imbalances were detected, explain in plain English which limbs need attention and how the prescribed unilateral exercises will help correct the balance.
3. Outline the prescribed workout routine clearly and offer brief, helpful form cues.
4. Highlight their daily nutrition targets and provide practical, balanced meal suggestions that fit their exact macronutrient requirements.
5. CRITICAL INVARIANT: The caloric and macronutrient targets (target_calories_kcal, protein_g, carbs_g, fats_g, fiber_g) are clinically pre-computed and DETERMINISTIC. You MUST restate these numbers EXACTLY as provided in the input. DO NOT modify, round, or alter them under any circumstance.
"""


class OpenAIClientProtocol(Protocol):
    """Protocol matching the OpenAI SDK chat completion interface for dependency injection."""

    beta: object


def _build_user_prompt(master: MasterPayload) -> str:
    return (
        f"Please synthesize a comprehensive daily fitness and nutrition plan for this user based on their assessment data:\n\n"
        f"{master.model_dump_json(indent=2)}"
    )


def synthesize_plan(
    master: MasterPayload,
    client: OpenAIClientProtocol | None = None,
    model: str = "gpt-4o-mini",
) -> DailyPlan:
    """Synthesize the human-readable daily plan from deterministic outputs.

    Uses OpenAI Structured Outputs to enforce JSON Schema adherence, then
    hands the result to ``validate_no_mutation`` before returning.
    If the LLM call fails or mutates any number, it safely falls back
    to ``generate_fallback_plan``.
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
            response_format=DailyPlan,
        )
        plan = completion.choices[0].message.parsed
        if plan is None:
            return generate_fallback_plan(master)
        return validate_no_mutation(master, plan)
    except (NumericalMutationError, Exception):
        # Drop-on-mutation / fail-closed fallback
        return generate_fallback_plan(master)
