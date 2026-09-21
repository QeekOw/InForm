"""Module 4 — final plan integrity validation and deterministic rendering.

Second half of the dual-validation mechanism (concept paper §3.3):
After structured draft parsing, this validator confirms that final assembly
preserved every deterministic value and the exact backend-rendered plan section.
"""

from inform.master import DailyPlan, MasterPayload

_NUMERIC_FIELDS = (
    "target_calories_kcal",
    "protein_g",
    "carbs_g",
    "fats_g",
    "fiber_g",
)

class NumericalMutationError(ValueError):
    """Raised when the LLM modifies a deterministic nutrition number."""

    def __init__(self, field_name: str, expected: float, actual: float) -> None:
        self.field_name = field_name
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"LLM mutated deterministic field '{field_name}': expected {expected}, "
            f"got {actual}. Drop-on-mutation triggered."
        )


class PlanIntegrityError(ValueError):
    """Raised when the final narrative omits or alters its deterministic section."""


def validate_no_mutation(
    master: MasterPayload,
    plan: DailyPlan,
) -> DailyPlan:
    """Confirm the LLM preserved every deterministic nutrition figure.

    Compares ``plan``'s calorie/macro fields against ``master.nutrition``.
    Raises ``NumericalMutationError`` on any mismatch.
    """
    for field in _NUMERIC_FIELDS:
        expected = getattr(master.nutrition, field)
        actual = getattr(plan, field)
        if expected != actual:
            raise NumericalMutationError(field, expected, actual)
    if not plan.narrative_text.endswith(_render_deterministic_plan(master)):
        raise PlanIntegrityError("Daily plan is missing its exact deterministic section.")
    return plan


def _render_deterministic_plan(master: MasterPayload) -> str:
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

    if master.exercises.unconfirmed_imbalance_pairs:
        pairs = " and ".join(master.exercises.unconfirmed_imbalance_pairs)
        lines.append(
            f"Balance was not assessed for the {pairs} because those readings were not confirmed."
        )
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

    return "\n".join(lines)


def generate_fallback_plan(master: MasterPayload) -> DailyPlan:
    """Generate a deterministic, non-generative fallback DailyPlan."""

    return DailyPlan(
        narrative_text=_render_deterministic_plan(master),
        narrative_source="fallback",
        target_calories_kcal=master.nutrition.target_calories_kcal,
        protein_g=master.nutrition.protein_g,
        carbs_g=master.nutrition.carbs_g,
        fats_g=master.nutrition.fats_g,
        fiber_g=master.nutrition.fiber_g,
    )
