from inform.inbody import InBodyPayload, SegmentalLean
from inform.master import MasterPayload

from tests.test_exercise import _plan
from tests.test_nutrition import _targets
from tests.test_user import _user


def _inbody(**overrides) -> InBodyPayload:
    fields = dict(
        weight_kg=70.0,
        lean_body_mass_kg=58.0,
        percent_body_fat=17.1,
        skeletal_muscle_mass_kg=33.0,
        basal_metabolic_rate_kcal=1622.8,
        segmental_lean=SegmentalLean(
            left_arm_kg=3.2,
            right_arm_kg=3.3,
            left_leg_kg=8.1,
            right_leg_kg=8.2,
            trunk_kg=24.5,
        ),
        source_device="inbody_570",
    )
    fields.update(overrides)
    return InBodyPayload(**fields)


def _master(**overrides) -> MasterPayload:
    fields = dict(
        user=_user(),
        inbody=_inbody(),
        nutrition=_targets(),
        exercises=_plan(),
    )
    fields.update(overrides)
    return MasterPayload(**fields)


def test_valid_master_payload():
    master = _master()
    assert master.user.fitness_goal == "fat_loss"
    assert master.nutrition.target_calories_kcal == 2015.3
    assert master.exercises.exercises[0].name == "Single-leg press"


def test_master_payload_carries_visceral_fat_absence():
    master = _master(inbody=_inbody(source_device="inbody_270"))
    assert master.inbody.visceral_fat_level is None


def test_master_payload_round_trips_through_json():
    original = _master()
    restored = MasterPayload.model_validate_json(original.model_dump_json())
    assert restored == original
