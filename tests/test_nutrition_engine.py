import pytest

from inform.nutrition_engine import compute_targets

from tests.test_master import _inbody
from tests.test_user import _user


def test_bmr_uses_katch_mcardle_not_device_printed_value():
    # Deliberately mismatched printed BMR to prove it is never read.
    inbody = _inbody(lean_body_mass_kg=58.0, basal_metabolic_rate_kcal=999.9)
    user = _user(activity_multiplier=1.55, fitness_goal="fat_loss")

    targets = compute_targets(user, inbody)

    assert targets.bmr_kcal == pytest.approx(1622.8)
    assert targets.tdee_kcal == pytest.approx(2515.34)


def test_fat_loss_applies_deficit_and_higher_protein():
    inbody = _inbody(lean_body_mass_kg=58.0)
    user = _user(activity_multiplier=1.55, fitness_goal="fat_loss")

    targets = compute_targets(user, inbody)

    assert targets.target_calories_kcal == pytest.approx(2015.34)
    assert targets.protein_g == pytest.approx(139.2)
    assert targets.fats_g == pytest.approx(55.9817, rel=1e-4)
    assert targets.carbs_g == pytest.approx(238.6763, rel=1e-4)
    assert targets.fiber_g == pytest.approx(28.2148, rel=1e-4)


def test_hypertrophy_applies_surplus_and_lower_protein():
    inbody = _inbody(lean_body_mass_kg=58.0)
    user = _user(activity_multiplier=1.55, fitness_goal="hypertrophy")

    targets = compute_targets(user, inbody)

    assert targets.target_calories_kcal == pytest.approx(2815.34)
    assert targets.protein_g == pytest.approx(127.6)
    assert targets.fats_g == pytest.approx(78.2039, rel=1e-4)
    assert targets.carbs_g == pytest.approx(400.2763, rel=1e-4)
    assert targets.fiber_g == pytest.approx(39.4148, rel=1e-4)


def test_carbs_never_go_negative():
    # Very low LBM + sedentary + aggressive deficit: protein and fat alone
    # exceed target_calories_kcal (BMR=586, TDEE=586, target=86 kcal;
    # protein_kcal alone is 96).
    inbody = _inbody(lean_body_mass_kg=10.0)
    user = _user(activity_multiplier=1.0, fitness_goal="fat_loss")

    targets = compute_targets(user, inbody)

    assert targets.carbs_g == 0.0
