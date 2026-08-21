"""Module 4 — Backend validation guard against numerical mutation.

Second half of the dual-validation mechanism (concept paper §3.3):
After API-level JSON Schema adherence, this validator confirms that the LLM
did not mutate any deterministic number computed upstream. On mismatch,
the caller drops the LLM response and defaults to deterministic fallback text.
"""

from inform.master import DailyPlan, MasterPayload

_DEFAULT_FLOAT_TOLERANCE = 0.5  # Tolerance for floating point equality check

_NUMERIC_FIELDS = (
    "target_calories_kcal",
    "protein_g",
    "carbs_g",
    "fats_g",
    "fiber_g",
)


class NumericalMutationError(ValueError):
    """Raised when the LLM modifies a deterministic nutrition number."""

    def __init__(self, field_name: str, expected: float, actual: float, tolerance: float) -> None:
        self.field_name = field_name
        self.expected = expected
        self.actual = actual
        self.tolerance = tolerance
        super().__init__(
            f"LLM mutated deterministic field '{field_name}': expected {expected}, "
            f"got {actual} (tolerance {tolerance}). Drop-on-mutation triggered."
        )


def validate_no_mutation(
    master: MasterPayload,
    plan: DailyPlan,
    tolerance: float = _DEFAULT_FLOAT_TOLERANCE,
) -> DailyPlan:
    """Confirm the LLM preserved every deterministic nutrition figure.

    Compares ``plan``'s calorie/macro fields against ``master.nutrition``.
    Raises ``NumericalMutationError`` on any mismatch beyond ``tolerance``.
    """
    for field in _NUMERIC_FIELDS:
        expected = getattr(master.nutrition, field)
        actual = getattr(plan, field)
        if abs(expected - actual) > tolerance:
            raise NumericalMutationError(field, expected, actual, tolerance)
    return plan


def generate_fallback_plan(master: MasterPayload) -> DailyPlan:
    """Generate a deterministic, non-generative fallback DailyPlan.

    Used when LLM synthesis fails or triggers a NumericalMutationError.
    Constructs a clean, structured summary directly from deterministic fields.
    """
    goal_label = "Muscle Hypertrophy" if master.user.fitness_goal == "hypertrophy" else "Fat Loss"

    lines = [
        f"# Daily Fitness & Nutrition Plan ({goal_label})",
        "",
        "## Nutritional Targets",
        f"- **Daily Energy Target:** {master.nutrition.target_calories_kcal:.0f} kcal (BMR: {master.nutrition.bmr_kcal:.0f} kcal, TDEE: {master.nutrition.tdee_kcal:.0f} kcal)",
        f"- **Protein:** {master.nutrition.protein_g:.1f}g",
        f"- **Carbohydrates:** {master.nutrition.carbs_g:.1f}g",
        f"- **Fats:** {master.nutrition.fats_g:.1f}g",
        f"- **Fiber:** {master.nutrition.fiber_g:.1f}g",
        "",
        "## Recommended Workout Program",
    ]

    if master.exercises.detected_imbalances:
        lines.append("### Detected Imbalances & Focus Areas")
        for imbalance in master.exercises.detected_imbalances:
            lines.append(f"- ⚠️ {imbalance}")
        lines.append("")

    if master.exercises.exercises:
        lines.append("### Exercise Routine")
        for i, ex in enumerate(master.exercises.exercises, 1):
            move_type_tag = f"[{ex.movement_type.replace('_', ' ').title()}]"
            secondary = (
                f" (Secondary: {', '.join(ex.secondary_muscles)})" if ex.secondary_muscles else ""
            )
            lines.append(
                f"{i}. **{ex.name}** {move_type_tag} — Target: {ex.target} ({ex.equipment}){secondary}"
            )
    else:
        lines.append("No specific exercises prescribed for today.")

    narrative = "\n".join(lines)

    return DailyPlan(
        narrative_text=narrative,
        target_calories_kcal=master.nutrition.target_calories_kcal,
        protein_g=master.nutrition.protein_g,
        carbs_g=master.nutrition.carbs_g,
        fats_g=master.nutrition.fats_g,
        fiber_g=master.nutrition.fiber_g,
    )
