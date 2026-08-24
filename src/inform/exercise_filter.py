from inform.exercise import Exercise, ExercisePlan
from inform.inbody import InBodyPayload
from inform.user import UserProfile

# Bilateral asymmetry: |larger - smaller| / larger x 100 (an Asymmetry Index,
# cf. Bishop et al.). CONTEXT.md and the paper (§3.1.3.1) fix the trigger at
# a deviation exceeding 5% between a left/right limb pair.
_ASYMMETRY_THRESHOLD_PCT = 5.0

# limb -> (left field, right field, matching Exercise.body_part values)
_LIMB_PAIRS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    "arm": ("left_arm_kg", "right_arm_kg", ("upper arms", "lower arms")),
    "leg": ("left_leg_kg", "right_leg_kg", ("upper legs", "lower legs")),
}

# Not sourced from an ADR — InBody's own published scale treats roughly 10+
# (of a typical 1-20 range) as elevated. Documented default, same spirit as
# nutrition_engine.py's macro-split constants; revisit if InBody's
# interpretation guide is consulted directly.
_HIGH_VISCERAL_FAT_THRESHOLD = 10

_HYPERTROPHY_COMPOUND_COUNT = 4
_FAT_LOSS_BASE_CARDIO_COUNT = 1
_FAT_LOSS_HIGH_VISCERAL_CARDIO_COUNT = 3


def recommend_exercises(
    user: UserProfile, inbody: InBodyPayload, exercise_pool: list[Exercise]
) -> ExercisePlan:
    """Module 3: deterministic constraint-based filtering over exercise_pool.

    exercise_pool is the candidate set to filter/select from (in production,
    the hasaneyldrm/exercises-dataset per the concept paper §3.2.2 — not yet
    vendored in this repo; injected here so the filtering rules are testable
    independent of that data-acquisition concern).
    """
    detected_imbalances: list[str] = []
    selected: list[Exercise] = []
    seen_names: set[str] = set()

    def _add(exercises: list[Exercise]) -> None:
        for ex in exercises:
            if ex.name not in seen_names:
                selected.append(ex)
                seen_names.add(ex.name)

    # 3.1.3.1 Imbalance correction
    for limb, (left_field, right_field, body_parts) in _LIMB_PAIRS.items():
        left = getattr(inbody.segmental_lean, left_field)
        right = getattr(inbody.segmental_lean, right_field)
        deviation_pct = abs(left - right) / max(left, right) * 100
        if deviation_pct > _ASYMMETRY_THRESHOLD_PCT:
            detected_imbalances.append(f"L/R {limb} lean-mass deviation {deviation_pct:.1f}%")
            _add(
                [
                    ex
                    for ex in exercise_pool
                    if ex.movement_type == "corrective_unilateral"
                    and ex.body_part.lower() in body_parts
                ]
            )

    # 3.1.3.2 Goal-driven adaptation
    if user.fitness_goal == "hypertrophy":
        compounds = [ex for ex in exercise_pool if ex.movement_type == "bilateral_compound"]
        _add(compounds[:_HYPERTROPHY_COMPOUND_COUNT])
    elif user.fitness_goal == "fat_loss":
        cardio = [ex for ex in exercise_pool if ex.movement_type == "cardio_hiit"]
        # ADR-0009: an absent visceral_fat_level falls back to fitness_goal
        # alone rather than erroring or imputing a value.
        high_visceral = (
            inbody.visceral_fat_level is not None
            and inbody.visceral_fat_level >= _HIGH_VISCERAL_FAT_THRESHOLD
        )
        count = (
            _FAT_LOSS_HIGH_VISCERAL_CARDIO_COUNT
            if high_visceral
            else _FAT_LOSS_BASE_CARDIO_COUNT
        )
        _add(cardio[:count])

    return ExercisePlan(exercises=selected, detected_imbalances=detected_imbalances)
