"""Shared body-composition formulas — single source of truth.

Kept in a leaf module so Module 1 (extraction cross-check), Module 2 (nutrition
engine), and the synthetic-sheet generator can all share the exact same formula
without any backward dependency between pipeline stages.
"""

# Katch-McArdle: BMR = 370 + 21.6 x LBM_kg (CONTEXT.md; ADR-0001 [reserved]).
KATCH_MCARDLE_BASE_KCAL = 370.0
KATCH_MCARDLE_LBM_COEFFICIENT = 21.6


def katch_mcardle_bmr(lean_body_mass_kg: float) -> float:
    """Basal metabolic rate from lean body mass, via Katch-McArdle."""
    return KATCH_MCARDLE_BASE_KCAL + KATCH_MCARDLE_LBM_COEFFICIENT * lean_body_mass_kg
