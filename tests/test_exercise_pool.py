from inform.exercise_pool import DEFAULT_EXERCISE_POOL


def test_pool_covers_every_corrective_body_part():
    corrective = [ex for ex in DEFAULT_EXERCISE_POOL if ex.movement_type == "corrective_unilateral"]
    body_parts = {ex.body_part for ex in corrective}
    assert body_parts == {"upper arms", "lower arms", "upper legs", "lower legs"}


def test_pool_has_enough_bilateral_compounds_for_hypertrophy_selection():
    compounds = [ex for ex in DEFAULT_EXERCISE_POOL if ex.movement_type == "bilateral_compound"]
    assert len(compounds) >= 4  # exercise_filter._HYPERTROPHY_COMPOUND_COUNT


def test_pool_has_enough_cardio_for_high_visceral_selection():
    cardio = [ex for ex in DEFAULT_EXERCISE_POOL if ex.movement_type == "cardio_hiit"]
    assert len(cardio) >= 3  # exercise_filter._FAT_LOSS_HIGH_VISCERAL_CARDIO_COUNT


def test_pool_names_are_unique():
    names = [ex.name for ex in DEFAULT_EXERCISE_POOL]
    assert len(names) == len(set(names))
