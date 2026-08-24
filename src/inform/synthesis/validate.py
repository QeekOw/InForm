"""Module 4 — Backend validation guard against numerical mutation.

Second half of the dual-validation mechanism (concept paper §3.3):
After API-level JSON Schema adherence, this validator confirms that the LLM
did not mutate any deterministic number computed upstream. On mismatch,
the caller drops the LLM response and defaults to deterministic fallback text.
"""

import re

from inform.master import DailyPlan, MasterPayload

_DEFAULT_FLOAT_TOLERANCE = 0.5  # Tolerance for floating point equality check

_NUMERIC_FIELDS = (
    "target_calories_kcal",
    "protein_g",
    "carbs_g",
    "fats_g",
    "fiber_g",
)

# A "<number> kcal/calorie(s)" figure in the narrative is only a mutation if it
# is a *restatement* of a deterministic calorie value (target, BMR, TDEE) that
# got the number wrong. Rounding for display can shift a value by up to ~0.5, so
# allow 1.0 kcal of slack before calling it mutated.
_NARRATIVE_KCAL_TOLERANCE = 1.0
# A stated figure within this fraction of a deterministic value is read as a
# restatement of it (and must match); figures farther from every deterministic
# value are unrelated coaching numbers — "500 kcal deficit", "4 kcal per gram" —
# and are left alone. The strict structured-field echo above still guards the
# actual targets regardless.
_RESTATEMENT_BAND = 0.20
# Match a calorie figure with the unit on EITHER side: "1,800 kcal" and
# "kcal: 1800" / "calories are 1800" both count. Two capture groups, one per order.
_NUM = r"(\d[\d,]*(?:\.\d+)?)"
_KCAL_UNIT = r"(?:kcal|kilocalories|kilocalorie|calories|calorie)"
_KCAL_MENTION = re.compile(
    rf"{_NUM}\s*{_KCAL_UNIT}\b|\b{_KCAL_UNIT}\b\s*(?:is|are|of|[:=])?\s*{_NUM}",
    re.IGNORECASE,
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
    _assert_narrative_calories_consistent(master, plan)
    return plan


def _assert_narrative_calories_consistent(master: MasterPayload, plan: DailyPlan) -> None:
    """Guard the *prose* against a mutated calorie figure.

    The echoed structured fields above are a parallel copy; the numbers a human
    actually reads live in ``narrative_text``. The model is told to restate the
    deterministic figures exactly, so a ``<n> kcal`` figure *close to* one of the
    three deterministic calorie values (target, BMR, TDEE) but not equal to it is
    a mutated restatement — e.g. "aim for 1,800 kcal" when BMR is 1,688 — and we
    raise so the caller drops to the deterministic fallback.

    A kcal figure far from every deterministic value is an unrelated coaching
    number ("a 500 kcal deficit", "4 kcal per gram"), not a restatement, so it is
    left alone — the strict structured-field echo above still guards the targets.

    Coverage is a number adjacent to the unit in either order ("1,800 kcal",
    "kcal: 1800"). Two residuals are deliberately left to the prompt instruction
    and the structured-field echo: (1) a unit and number separated by intervening
    words ("kcal target is 1800") — closing that needs NLP, not a regex; (2) macro
    figures in grams — gram tokens collide with example food quantities.
    """
    legit = (
        master.nutrition.target_calories_kcal,
        master.nutrition.bmr_kcal,
        master.nutrition.tdee_kcal,
    )
    for match in _KCAL_MENTION.finditer(plan.narrative_text):
        # Group 1 = number-before-unit, group 2 = unit-before-number; exactly one fires.
        token = match.group(1) or match.group(2)
        stated = float(token.replace(",", ""))
        nearest = min(legit, key=lambda v: abs(v - stated))
        delta = abs(nearest - stated)
        if delta <= _NARRATIVE_KCAL_TOLERANCE:
            continue  # exact restatement of a deterministic value
        if delta <= _RESTATEMENT_BAND * nearest:
            # Close enough to be a restatement of `nearest`, but the number is
            # wrong: a mutated deterministic figure. Sentinel field name marks a
            # prose figure; "expected" carries the value it should have restated.
            raise NumericalMutationError(
                "narrative_text:kcal", nearest, stated, _NARRATIVE_KCAL_TOLERANCE
            )
        # else: far from every deterministic value — an unrelated coaching figure.


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
