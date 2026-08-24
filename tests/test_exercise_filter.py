from inform.exercise import Exercise
from inform.exercise_filter import recommend_exercises

from tests.test_master import _inbody
from tests.test_user import _user


def _pool() -> list[Exercise]:
    return [
        Exercise(
            name="Single-arm dumbbell row",
            target="lats",
            body_part="upper arms",
            equipment="dumbbell",
            secondary_muscles=["biceps"],
            movement_type="corrective_unilateral",
        ),
        Exercise(
            name="Bulgarian split squat",
            target="quadriceps",
            body_part="upper legs",
            equipment="body weight",
            secondary_muscles=["glutes"],
            movement_type="corrective_unilateral",
        ),
        Exercise(
            name="Barbell back squat",
            target="quadriceps",
            body_part="upper legs",
            equipment="barbell",
            secondary_muscles=["glutes", "hamstrings"],
            movement_type="bilateral_compound",
        ),
        Exercise(
            name="Bench press",
            target="pectorals",
            body_part="chest",
            equipment="barbell",
            secondary_muscles=["triceps"],
            movement_type="bilateral_compound",
        ),
        Exercise(
            name="Deadlift",
            target="glutes",
            body_part="upper legs",
            equipment="barbell",
            secondary_muscles=["hamstrings", "lower back"],
            movement_type="bilateral_compound",
        ),
        Exercise(
            name="Overhead press",
            target="deltoids",
            body_part="shoulders",
            equipment="barbell",
            secondary_muscles=["triceps"],
            movement_type="bilateral_compound",
        ),
        Exercise(
            name="Rowing sprint intervals",
            target="cardiovascular system",
            body_part="cardio",
            equipment="rowing machine",
            secondary_muscles=[],
            movement_type="cardio_hiit",
        ),
        Exercise(
            name="Burpees",
            target="cardiovascular system",
            body_part="cardio",
            equipment="body weight",
            secondary_muscles=[],
            movement_type="cardio_hiit",
        ),
        Exercise(
            name="Battle ropes",
            target="cardiovascular system",
            body_part="cardio",
            equipment="rope",
            secondary_muscles=[],
            movement_type="cardio_hiit",
        ),
        Exercise(
            name="Mountain climbers",
            target="cardiovascular system",
            body_part="cardio",
            equipment="body weight",
            secondary_muscles=[],
            movement_type="cardio_hiit",
        ),
    ]


def test_no_asymmetry_hypertrophy_selects_bilateral_compounds():
    inbody = _inbody()  # default fixture: arm 3.03%, leg 1.22% — both under threshold
    user = _user(fitness_goal="hypertrophy")

    plan = recommend_exercises(user, inbody, _pool())

    assert plan.detected_imbalances == []
    assert [ex.name for ex in plan.exercises] == [
        "Barbell back squat",
        "Bench press",
        "Deadlift",
        "Overhead press",
    ]


def test_leg_asymmetry_over_threshold_adds_corrective_exercise():
    inbody = _inbody(
        segmental_lean=_inbody().segmental_lean.model_copy(
            update={"left_leg_kg": 8.0, "right_leg_kg": 9.0}
        )
    )
    user = _user(fitness_goal="hypertrophy")

    plan = recommend_exercises(user, inbody, _pool())

    assert plan.detected_imbalances == ["L/R leg SMM deviation 11.1%"]
    names = [ex.name for ex in plan.exercises]
    assert names[0] == "Bulgarian split squat"
    assert "Single-arm dumbbell row" not in names


def test_both_limb_asymmetries_detected_in_order():
    inbody = _inbody(
        segmental_lean=_inbody().segmental_lean.model_copy(
            update={
                "left_arm_kg": 3.0,
                "right_arm_kg": 4.0,
                "left_leg_kg": 8.0,
                "right_leg_kg": 9.0,
            }
        )
    )
    user = _user(fitness_goal="hypertrophy")

    plan = recommend_exercises(user, inbody, _pool())

    assert plan.detected_imbalances == [
        "L/R arm SMM deviation 25.0%",
        "L/R leg SMM deviation 11.1%",
    ]
    names = [ex.name for ex in plan.exercises]
    assert names[:2] == ["Single-arm dumbbell row", "Bulgarian split squat"]


def test_fat_loss_with_absent_visceral_fat_uses_base_cardio_count():
    inbody = _inbody(source_device="inbody_270")  # visceral_fat_level is None
    user = _user(fitness_goal="fat_loss")

    plan = recommend_exercises(user, inbody, _pool())

    assert [ex.name for ex in plan.exercises] == ["Rowing sprint intervals"]


def test_fat_loss_with_low_visceral_fat_uses_base_cardio_count():
    inbody = _inbody(visceral_fat_level=3)
    user = _user(fitness_goal="fat_loss")

    plan = recommend_exercises(user, inbody, _pool())

    assert [ex.name for ex in plan.exercises] == ["Rowing sprint intervals"]


def test_fat_loss_with_high_visceral_fat_increases_cardio_count():
    inbody = _inbody(visceral_fat_level=15)
    user = _user(fitness_goal="fat_loss")

    plan = recommend_exercises(user, inbody, _pool())

    assert [ex.name for ex in plan.exercises] == [
        "Rowing sprint intervals",
        "Burpees",
        "Battle ropes",
    ]
