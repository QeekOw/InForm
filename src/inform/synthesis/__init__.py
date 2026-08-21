"""Module 4 — LLM synthesis and dual-validation."""

from inform.synthesis.generate import synthesize_plan
from inform.synthesis.validate import (
    NumericalMutationError,
    generate_fallback_plan,
    validate_no_mutation,
)

__all__ = [
    "synthesize_plan",
    "validate_no_mutation",
    "generate_fallback_plan",
    "NumericalMutationError",
]
