# _generate_values is pure (no browser subprocess) so most invariant checks
# run fast across many seeds. Only a couple of tests exercise the full
# generate_sheet() render path, which shells out to a headless browser.
import io

from PIL import Image

from cera.synthetic import _derive_render_values, _fill_template, _generate_values, generate_sheet

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


def test_both_devices_report_visceral_fat():
    # ADR-0004 corrected (issue #13): the real InBody 270 *does* print a
    # Visceral Fat Level (confirmed on two real 270 sheets), so both devices
    # now populate it. The schema keeps it optional for real-world absence.
    for seed in _SEEDS:
        assert _generate_values("inbody_270", seed).visceral_fat_level is not None
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


def test_270_template_includes_visceral_fat_and_fat_free_mass():
    # New realistic 270 (issue #13): full clone renders a Visceral Fat Level
    # block, and LBM appears at its real position — the "Fat Free Mass" row in
    # Research Parameters — not an invented "Lean Body Mass" row (Q2 / ADR-0003).
    payload_270 = _generate_values("inbody_270", seed=3)
    html_270 = _fill_template("inbody_270", payload_270)

    assert "Visceral Fat" in html_270
    assert "Fat Free Mass" in html_270


def test_570_template_uses_lean_body_mass_not_fat_free_mass():
    # The adult 570 sheet labels LBM as "Lean Body Mass" (270 uses "Fat Free
    # Mass"); both map to the same $lean_body_mass_kg placeholder.
    html_570 = _fill_template("inbody_570", _generate_values("inbody_570", seed=3))
    assert "Lean Body Mass" in html_570
    assert "Fat Free Mass" not in html_570
    assert "Visceral Fat" in html_570


def test_570_body_water_split_is_coherent():
    # The 570 Body Composition block cross-adds like a real sheet:
    # ICW + ECW = TBW; TBW + Dry Lean = LBM; LBM + Body Fat = Weight.
    for seed in _SEEDS:
        payload = _generate_values("inbody_570", seed)
        d = _derive_render_values(payload)
        assert abs(d["intracellular_water_l"] + d["extracellular_water_l"] - d["total_body_water_l"]) <= _TOLERANCE
        assert abs(d["total_body_water_l"] + d["dry_lean_mass_kg"] - payload.lean_body_mass_kg) <= 0.15
        assert abs(payload.lean_body_mass_kg + d["body_fat_mass_kg"] - payload.weight_kg) <= _TOLERANCE


def test_270_ground_truth_matches_rendered_template_values():
    _, payload = generate_sheet("inbody_270", seed=3)
    html = _fill_template("inbody_270", payload)

    assert "Visceral Fat" in html
    # Every graded target value must appear verbatim so rendered text can never
    # diverge from the ground-truth JSON (ADR-0007).
    assert str(payload.weight_kg) in html
    assert str(payload.lean_body_mass_kg) in html  # rendered as Fat Free Mass
    assert str(payload.percent_body_fat) in html
    assert str(payload.skeletal_muscle_mass_kg) in html
    assert str(payload.basal_metabolic_rate_kcal) in html
    assert str(payload.visceral_fat_level) in html
    assert str(payload.segmental_lean.trunk_kg) in html


def test_derived_distractors_are_coherent_and_deterministic():
    # Q3: distractor values derive coherently from the ground truth so a
    # rendered sheet cross-adds like a real one and is human-verifiable.
    for seed in _SEEDS:
        payload = _generate_values("inbody_270", seed)
        d = _derive_render_values(payload)

        # Body Fat Mass = weight - LBM (fat is what LBM excludes).
        assert abs(d["body_fat_mass_kg"] - (payload.weight_kg - payload.lean_body_mass_kg)) <= _TOLERANCE
        # The Body Composition Analysis block sums to Weight, as on a real sheet:
        # Total Body Water + Protein + Minerals + Body Fat Mass ≈ Weight.
        block_sum = d["total_body_water_l"] + d["protein_kg"] + d["minerals_kg"] + d["body_fat_mass_kg"]
        assert abs(block_sum - payload.weight_kg) <= 1.0
        # BMI is physiologically plausible.
        assert 12.0 <= d["bmi"] <= 45.0
        # Deterministic given the same payload.
        assert _derive_render_values(payload) == d
