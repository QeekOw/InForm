# _generate_values is pure (no browser subprocess) so most invariant checks
# run fast across many seeds. Only a couple of tests exercise the full
# generate_sheet() render path, which shells out to a headless browser.
import io

from PIL import Image

from cera.synthetic import _fill_template, _generate_values, generate_sheet

_SEEDS = range(30)
_TOLERANCE = 0.1


def test_lbm_matches_weight_times_one_minus_pbf():
    for device in ("inbody_270", "inbody_570"):
        for seed in _SEEDS:
            payload = _generate_values(device, seed)
            derived_lbm = payload.weight_kg * (1 - payload.percent_body_fat / 100)
            assert abs(payload.lean_body_mass_kg - derived_lbm) <= _TOLERANCE


def test_smm_is_less_than_lbm():
    for device in ("inbody_270", "inbody_570"):
        for seed in _SEEDS:
            payload = _generate_values(device, seed)
            assert payload.skeletal_muscle_mass_kg < payload.lean_body_mass_kg


def test_bmr_matches_katch_mcardle_recompute():
    for device in ("inbody_270", "inbody_570"):
        for seed in _SEEDS:
            payload = _generate_values(device, seed)
            recomputed = 370 + 21.6 * payload.lean_body_mass_kg
            assert abs(payload.basal_metabolic_rate_kcal - recomputed) <= _TOLERANCE


def test_segments_sum_to_lbm():
    for device in ("inbody_270", "inbody_570"):
        for seed in _SEEDS:
            payload = _generate_values(device, seed)
            segments = payload.segmental_lean
            total = (
                segments.left_arm_kg
                + segments.right_arm_kg
                + segments.left_leg_kg
                + segments.right_leg_kg
                + segments.trunk_kg
            )
            assert abs(total - payload.lean_body_mass_kg) <= _TOLERANCE


def test_270_omits_visceral_fat_570_includes_it():
    for seed in _SEEDS:
        assert _generate_values("inbody_270", seed).visceral_fat_level is None
        assert _generate_values("inbody_570", seed).visceral_fat_level is not None


def test_some_seeds_produce_deliberate_bilateral_asymmetry():
    def _max_pair_deviation_pct(payload) -> float:
        s = payload.segmental_lean
        pairs = ((s.left_arm_kg, s.right_arm_kg), (s.left_leg_kg, s.right_leg_kg))
        return max(abs(left - right) / ((left + right) / 2) * 100 for left, right in pairs)

    deviations = [_max_pair_deviation_pct(_generate_values("inbody_570", seed)) for seed in _SEEDS]
    assert any(deviation > 5.0 for deviation in deviations)


def test_same_seed_is_deterministic():
    first = _generate_values("inbody_570", seed=42)
    second = _generate_values("inbody_570", seed=42)
    assert first == second


def test_generate_sheet_returns_png_matching_device_window():
    image_bytes, payload = generate_sheet("inbody_570", seed=7)
    image = Image.open(io.BytesIO(image_bytes))
    assert image.format == "PNG"
    assert payload.source_device == "inbody_570"


def test_ground_truth_matches_rendered_template_values():
    # generate_sheet's image and payload are built from the same
    # _generate_values() call, and _fill_template renders directly from the
    # payload's own fields — so the rendered text and the ground truth JSON
    # can never diverge (ADR-0007).
    _, payload = generate_sheet("inbody_570", seed=7)
    html = _fill_template("inbody_570", payload)

    assert str(payload.weight_kg) in html
    assert str(payload.lean_body_mass_kg) in html
    assert str(payload.percent_body_fat) in html
    assert str(payload.skeletal_muscle_mass_kg) in html
    assert str(payload.basal_metabolic_rate_kcal) in html
    assert str(payload.visceral_fat_level) in html
    assert str(payload.segmental_lean.trunk_kg) in html

    ground_truth = payload.model_dump_json()
    restored = payload.model_validate_json(ground_truth)
    assert restored == payload


def test_270_template_omits_visceral_fat_row_570_includes_it():
    payload_270 = _generate_values("inbody_270", seed=3)
    payload_570 = _generate_values("inbody_570", seed=3)

    html_270 = _fill_template("inbody_270", payload_270)
    html_570 = _fill_template("inbody_570", payload_570)

    assert "Visceral Fat" not in html_270
    assert "Visceral Fat" in html_570


def test_270_ground_truth_matches_rendered_template_values():
    _, payload = generate_sheet("inbody_270", seed=3)
    html = _fill_template("inbody_270", payload)

    assert "Visceral Fat" not in html
    assert str(payload.weight_kg) in html
    assert str(payload.lean_body_mass_kg) in html
    assert str(payload.segmental_lean.trunk_kg) in html
