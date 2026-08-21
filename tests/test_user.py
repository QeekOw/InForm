import pytest
from pydantic import ValidationError

from cera.user import UserProfile


def _user(**overrides) -> UserProfile:
    fields = dict(
        age=30,
        biological_sex="female",
        activity_multiplier=1.55,
        fitness_goal="fat_loss",
    )
    fields.update(overrides)
    return UserProfile(**fields)


def test_valid_user_profile():
    user = _user()
    assert user.fitness_goal == "fat_loss"
    assert user.activity_multiplier == 1.55


def test_invalid_fitness_goal_rejected():
    with pytest.raises(ValidationError):
        _user(fitness_goal="cutting")


def test_invalid_biological_sex_rejected():
    with pytest.raises(ValidationError):
        _user(biological_sex="other")


def test_user_profile_round_trips_through_json():
    original = _user()
    restored = UserProfile.model_validate_json(original.model_dump_json())
    assert restored == original
