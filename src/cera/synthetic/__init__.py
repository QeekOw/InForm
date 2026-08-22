import io
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from string import Template
from typing import Literal

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from cera.inbody import InBodyPayload, SegmentalLean

_TEMPLATE_DIR = Path(__file__).parent / "templates"
# 270 renders a full-page portrait clone (issue #13); 570 keeps its minimal
# landscape template until it is overhauled too (Q4 — 270 first).
_WINDOW_SIZE = {"inbody_270": "1060,1320", "inbody_570": "560,460"}

# ponytail: fixed physiological ranges/proportions, not learned from data.
# Tune against real InBody sheets if the synthetic distribution drifts.
_WEIGHT_RANGE_KG = (50.0, 100.0)
_PBF_RANGE_PCT = (10.0, 35.0)
_SMM_FRACTION_OF_LBM_RANGE = (0.55, 0.65)
_VISCERAL_FAT_RANGE = (1, 20)
_SEGMENT_FRACTIONS_OF_LBM = {"left_arm_kg": 0.08, "right_arm_kg": 0.08, "left_leg_kg": 0.17, "right_leg_kg": 0.17}
_ASYMMETRY_PROBABILITY = 0.3
_ASYMMETRY_DEVIATION_PCT = 8.0  # comfortably past the >5% bilateral-asymmetry threshold

# Body Composition Analysis components as fractions of LBM. These sum to ~1.0,
# so Total Body Water + Protein + Minerals + (weight - LBM) ≈ Weight — the block
# cross-adds like a real InBody sheet (Q3, verified in test_synthetic).
_TBW_FRACTION_OF_LBM = 0.73
_PROTEIN_FRACTION_OF_LBM = 0.198
_MINERALS_FRACTION_OF_LBM = 0.0727

_EXERCISES_KCAL = (  # static distractor: the Calorie Expenditure table, verbatim from a real 270
    ("Golf", 144), ("Gateball", 156), ("Walking", 164), ("Yoga", 164),
    ("Badminton", 185), ("Table Tennis", 185), ("Tennis", 246), ("Bicycling", 246),
    ("Boxing", 246), ("Basketball", 246), ("Mountain Climbing", 267), ("Jumping Rope", 287),
    ("Aerobics", 287), ("Jogging", 287), ("Soccer", 287), ("Swimming", 287),
    ("Japanese Fencing", 410), ("Racketball", 410), ("Squash", 410), ("Taekwondo", 410),
)

_BROWSER_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium-browser",
    "chromium",
    "msedge",
)


def generate_sheet(device: Literal["inbody_270", "inbody_570"], seed: int) -> tuple[bytes, InBodyPayload]:
    """Render one synthetic InBody sheet + its exact ground-truth payload (ADR-0007)."""
    payload = _generate_values(device, seed)
    image = _render(device, payload)
    image = _augment(image, random.Random(seed))

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue(), payload


def _generate_values(device: Literal["inbody_270", "inbody_570"], seed: int) -> InBodyPayload:
    rng = random.Random(seed)

    weight_kg = round(rng.uniform(*_WEIGHT_RANGE_KG), 1)
    percent_body_fat = round(rng.uniform(*_PBF_RANGE_PCT), 1)
    lean_body_mass_kg = round(weight_kg * (1 - percent_body_fat / 100), 1)
    skeletal_muscle_mass_kg = round(lean_body_mass_kg * rng.uniform(*_SMM_FRACTION_OF_LBM_RANGE), 1)
    basal_metabolic_rate_kcal = round(370 + 21.6 * lean_body_mass_kg, 1)
    # Both devices print a Visceral Fat Level (ADR-0004 corrected in issue #13 —
    # confirmed on two real InBody 270 sheets). Schema keeps it optional for
    # real-world absence, but synthetic sheets always render it.
    visceral_fat_level = rng.randint(*_VISCERAL_FAT_RANGE)

    return InBodyPayload(
        weight_kg=weight_kg,
        lean_body_mass_kg=lean_body_mass_kg,
        percent_body_fat=percent_body_fat,
        skeletal_muscle_mass_kg=skeletal_muscle_mass_kg,
        basal_metabolic_rate_kcal=basal_metabolic_rate_kcal,
        segmental_lean=_generate_segmental(lean_body_mass_kg, rng),
        visceral_fat_level=visceral_fat_level,
        source_device=device,
    )


def _generate_segmental(lean_body_mass_kg: float, rng: random.Random) -> SegmentalLean:
    skewed_pair = rng.choice(["arm", "leg"]) if rng.random() < _ASYMMETRY_PROBABILITY else None

    def _pair(name: str, fraction: float) -> tuple[float, float]:
        base = lean_body_mass_kg * fraction
        if name != skewed_pair:
            return base, base
        deviation = base * (_ASYMMETRY_DEVIATION_PCT / 100)
        return base + deviation / 2, base - deviation / 2

    left_arm, right_arm = _pair("arm", _SEGMENT_FRACTIONS_OF_LBM["left_arm_kg"])
    left_leg, right_leg = _pair("leg", _SEGMENT_FRACTIONS_OF_LBM["left_leg_kg"])
    left_arm, right_arm, left_leg, right_leg = (round(v, 1) for v in (left_arm, right_arm, left_leg, right_leg))

    # Trunk absorbs the rounding remainder so the five segments always sum
    # exactly to lean_body_mass_kg — "segments sum coherently" (ADR-0007).
    trunk_kg = round(lean_body_mass_kg - (left_arm + right_arm + left_leg + right_leg), 1)

    return SegmentalLean(
        left_arm_kg=left_arm, right_arm_kg=right_arm, left_leg_kg=left_leg, right_leg_kg=right_leg, trunk_kg=trunk_kg
    )


def _bar_pct(value: float, lo: float, hi: float) -> float:
    """Bar fill as a % of the plot width, clamped so the tip stays on-scale.

    ponytail: an indicative width, not InBody's exact %-of-standard normalisation
    — Donut is graded on the numeric label at the bar tip, not the bar length.
    """
    return round(min(max((value - lo) / (hi - lo), 0.05), 0.95) * 100, 1)


def _history_cells(end: float, drift_frac: float, rng: random.Random, decimals: int, n: int = 8) -> str:
    """A row of n dated `<td>` values drifting toward `end` (the current value).

    Positive drift → the metric was higher in the past (weight/PBF trending down);
    negative drift → it was lower (SMM trending up). The last cell equals `end`.
    """
    values = []
    v = float(end)
    for _ in range(n):
        values.append(round(v, decimals))
        v = v * (1 + drift_frac / n) + rng.uniform(-0.1, 0.1)
    values.reverse()
    return "".join(f"<td>{x}</td>" for x in values)


def _derive_render_values(payload: InBodyPayload) -> dict:
    """Physiologically-coherent distractor values for the realistic 270 clone.

    Pure and deterministic in the payload (seeded from its own JSON), so the same
    ground truth always renders the same surrounding clutter. Everything here is
    ungraded — the graded target fields come straight off `payload` (Q3, ADR-0007).
    """
    rng = random.Random(payload.model_dump_json())
    lbm = payload.lean_body_mass_kg
    weight = payload.weight_kg
    pbf = payload.percent_body_fat
    smm = payload.skeletal_muscle_mass_kg
    seg = payload.segmental_lean

    height_cm = round(rng.uniform(150.0, 190.0), 1)
    height_m = height_cm / 100
    body_fat_mass_kg = round(weight - lbm, 1)
    total_body_water_l = round(_TBW_FRACTION_OF_LBM * lbm, 1)
    protein_kg = round(_PROTEIN_FRACTION_OF_LBM * lbm, 1)
    minerals_kg = round(_MINERALS_FRACTION_OF_LBM * lbm, 2)
    bmi = round(weight / (height_m**2), 1)
    ideal_weight = 22.0 * height_m**2
    appendicular = seg.left_arm_kg + seg.right_arm_kg + seg.left_leg_kg + seg.right_leg_kg

    def _seg(value: float, fraction: float) -> tuple[float, str]:
        expected = lbm * fraction
        pct = round(value / expected * 100, 1) if expected else 100.0
        rate = "Normal" if 95 <= pct <= 105 else ("Under" if pct < 95 else "Over")
        return pct, rate

    la_pct, la_rate = _seg(seg.left_arm_kg, _SEGMENT_FRACTIONS_OF_LBM["left_arm_kg"])
    ra_pct, ra_rate = _seg(seg.right_arm_kg, _SEGMENT_FRACTIONS_OF_LBM["right_arm_kg"])
    ll_pct, ll_rate = _seg(seg.left_leg_kg, _SEGMENT_FRACTIONS_OF_LBM["left_leg_kg"])
    rl_pct, rl_rate = _seg(seg.right_leg_kg, _SEGMENT_FRACTIONS_OF_LBM["right_leg_kg"])
    trunk_pct, trunk_rate = _seg(seg.trunk_kg, 0.5)

    target_weight = round(ideal_weight, 1)
    fat_control = round(min(0.0, ideal_weight - weight), 1)
    waist_hip = round(rng.uniform(0.78, 0.95), 2)

    return {
        "id": f"{rng.choice('ABCDEFGH')}{rng.randint(1000, 9999)}",
        "height_cm": height_cm,
        "age": rng.randint(18, 65),
        "gender": rng.choice(["Male", "Female"]),
        "test_date": f"2026.{rng.randint(1, 12):02d}.{rng.randint(1, 28):02d}. {rng.randint(8, 19):02d}:{rng.randint(0, 59):02d}",
        "total_body_water_l": total_body_water_l,
        "protein_kg": protein_kg,
        "minerals_kg": minerals_kg,
        "body_fat_mass_kg": body_fat_mass_kg,
        "bmi": bmi,
        # bar widths (indicative)
        "weight_bar": _bar_pct(weight, 40, 140),
        "smm_bar": _bar_pct(smm, 20, 60),
        "bfm_bar": _bar_pct(body_fat_mass_kg, 5, 45),
        "bmi_bar": _bar_pct(bmi, 10, 55),
        "pbf_bar": _bar_pct(pbf, 5, 55),
        "waist_hip": waist_hip,
        "waist_hip_bar": _bar_pct(waist_hip, 0.70, 1.00),
        "visceral_bar": _bar_pct(payload.visceral_fat_level, 1, 20),
        "inbody_score": max(55, min(95, round(90 - (pbf - 15) * 1.2))),
        # weight control
        "target_weight": target_weight,
        "weight_control": round(ideal_weight - weight, 1),
        "fat_control": fat_control,
        "muscle_control": round(max(0.0, (ideal_weight - weight) - fat_control), 1),
        # research parameters (FFM = LBM target rendered in _fill_template)
        "obesity_degree": round(weight / ideal_weight * 100),
        "smi": round(appendicular / (height_m**2), 1),
        # recommended daily intake ≈ BMR × a light activity multiplier (distractor only)
        "recommended_calories": round(payload.basal_metabolic_rate_kcal * 1.4),
        # segmental lean percentages / ratings
        "la_pct": la_pct, "ra_pct": ra_pct, "ll_pct": ll_pct, "rl_pct": rl_pct, "trunk_pct": trunk_pct,
        "la_rate": la_rate, "ra_rate": ra_rate, "ll_rate": ll_rate, "rl_rate": rl_rate, "trunk_rate": trunk_rate,
        # segmental fat (estimated distractor)
        "fat_la": round(body_fat_mass_kg * 0.04, 1), "fat_ra": round(body_fat_mass_kg * 0.04, 1),
        "fat_ll": round(body_fat_mass_kg * 0.14, 1), "fat_rl": round(body_fat_mass_kg * 0.14, 1),
        "fat_trunk": round(body_fat_mass_kg * 0.44, 1),
        # history rows
        "weight_history": _history_cells(weight, 0.06, rng, 1),
        "smm_history": _history_cells(smm, -0.05, rng, 1),
        "pbf_history": _history_cells(pbf, 0.10, rng, 1),
        "date_history": "".join(f"<td>{rng.randint(1, 12):02d}.{rng.randint(1, 28):02d}</td>" for _ in range(8)),
        "exercise_rows": "".join(
            f'<div class="c"><span>{name}</span><span>{kcal}</span></div>' for name, kcal in _EXERCISES_KCAL
        ),
    }


def _graded_fields(payload: InBodyPayload) -> dict:
    """The graded target fields, verbatim off the payload (ADR-0007).

    Both device templates render exactly these; the 270 additionally spreads in
    `_derive_render_values`. Kept in one place so a field rename touches one spot.
    """
    seg = payload.segmental_lean
    return {
        "weight_kg": payload.weight_kg,
        "lean_body_mass_kg": payload.lean_body_mass_kg,  # 270 renders this as "Fat Free Mass"
        "percent_body_fat": payload.percent_body_fat,
        "skeletal_muscle_mass_kg": payload.skeletal_muscle_mass_kg,
        "basal_metabolic_rate_kcal": payload.basal_metabolic_rate_kcal,
        "visceral_fat_level": payload.visceral_fat_level,
        "left_arm_kg": seg.left_arm_kg,
        "right_arm_kg": seg.right_arm_kg,
        "left_leg_kg": seg.left_leg_kg,
        "right_leg_kg": seg.right_leg_kg,
        "trunk_kg": seg.trunk_kg,
    }


def _fill_template(device: Literal["inbody_270", "inbody_570"], payload: InBodyPayload) -> str:
    template = Template((_TEMPLATE_DIR / f"{device}.html").read_text(encoding="utf-8"))
    values = _graded_fields(payload)
    if device == "inbody_270":
        # 270 is the full realistic clone (issue #13): target fields sit amid the
        # coherent distractor surround. 570 stays minimal until overhauled (Q4).
        values |= _derive_render_values(payload)
    return template.substitute(values)


def _find_browser() -> str:
    # ponytail: shells out to a locally-installed Chrome/Edge/Chromium
    # instead of adding a browser-automation dependency (playwright,
    # weasyprint). Ceiling: fails on a machine/CI image with no such
    # browser present. Swap in playwright if the training environment
    # needs a guaranteed-portable renderer.
    for candidate in _BROWSER_CANDIDATES:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise RuntimeError(
        "No headless-capable browser (Chrome/Edge/Chromium) found on PATH or in a "
        "standard install location. Synthetic sheet rendering shells out to one "
        "instead of adding a browser-automation dependency."
    )


def _render(device: Literal["inbody_270", "inbody_570"], payload: InBodyPayload) -> Image.Image:
    html = _fill_template(device, payload)
    with tempfile.TemporaryDirectory() as tmp_dir:
        html_path = Path(tmp_dir) / "sheet.html"
        png_path = Path(tmp_dir) / "sheet.png"
        html_path.write_text(html, encoding="utf-8")
        subprocess.run(
            [
                _find_browser(),
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--screenshot={png_path}",
                f"--window-size={_WINDOW_SIZE[device]}",
                "--hide-scrollbars",
                html_path.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
        image = Image.open(png_path).convert("RGB").copy()
    return _crop_to_content(image) if device == "inbody_270" else image


def _crop_to_content(image: Image.Image) -> Image.Image:
    """Trim the white window margin down to the rendered sheet."""
    background = Image.new("RGB", image.size, (255, 255, 255))
    bbox = ImageChops.difference(image, background).getbbox()
    return image.crop(bbox) if bbox else image


def _augment(image: Image.Image, rng: random.Random) -> Image.Image:
    """Mimic phone capture (ADR-0007, strengthened in issue #13).

    ~30% of sheets stay "easy" (mild, clean, colour) so the held-out synthetic
    number stays interpretable; the rest get the full real-photo treatment —
    grayscale B&W prints, a desk background, glare, stronger geometry (Q6).
    """
    easy = rng.random() < 0.30

    if rng.random() < (0.15 if easy else 0.6):
        image = ImageOps.grayscale(image).convert("RGB")

    if not easy:
        image = _place_on_surface(image, rng)

    rotation = rng.uniform(-1.5, 1.5) if easy else rng.uniform(-6.0, 6.0)
    image = image.rotate(rotation, expand=True, fillcolor=(90, 90, 92), resample=Image.BICUBIC)
    image = _perspective_warp(image, rng, jitter=0.02 if easy else 0.06)

    if not easy:
        image = _glare(image, rng)

    image = image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0, 0.8 if easy else 1.8)))
    image = ImageEnhance.Brightness(image).enhance(rng.uniform(0.9, 1.1) if easy else rng.uniform(0.8, 1.2))
    image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.95, 1.05) if easy else rng.uniform(0.85, 1.15))
    return _jpeg_noise(image, rng, quality_range=(80, 95) if easy else (55, 85))


def _place_on_surface(image: Image.Image, rng: random.Random) -> Image.Image:
    """Paste the sheet onto a larger, darker 'desk' canvas with a random margin."""
    width, height = image.size
    margin_x = int(width * rng.uniform(0.04, 0.12))
    margin_y = int(height * rng.uniform(0.04, 0.12))
    shade = rng.randint(60, 120)
    desk = Image.new("RGB", (width + 2 * margin_x, height + 2 * margin_y), (shade, shade, shade + 2))
    desk.paste(image, (margin_x + rng.randint(-margin_x // 2, margin_x // 2), margin_y + rng.randint(-margin_y // 2, margin_y // 2)))
    return desk


def _glare(image: Image.Image, rng: random.Random) -> Image.Image:
    """Composite a soft white blob over the sheet to mimic overhead-light glare."""
    width, height = image.size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    cx, cy = rng.uniform(0, width), rng.uniform(0, height * 0.7)
    rw, rh = width * rng.uniform(0.2, 0.5), height * rng.uniform(0.12, 0.35)
    draw.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=rng.randint(50, 130))
    mask = mask.filter(ImageFilter.GaussianBlur(width * 0.05))
    white = Image.new("RGB", (width, height), (255, 255, 255))
    return Image.composite(white, image, mask)


def _jpeg_noise(image: Image.Image, rng: random.Random, quality_range: tuple[int, int] = (60, 90)) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=rng.randint(*quality_range))
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def _perspective_warp(image: Image.Image, rng: random.Random, jitter: float = 0.025) -> Image.Image:
    width, height = image.size
    jitter_x = width * jitter
    jitter_y = height * (jitter * 0.6)
    quad = (
        rng.uniform(0, jitter_x), rng.uniform(0, jitter_y),
        rng.uniform(0, jitter_x), height - rng.uniform(0, jitter_y),
        width - rng.uniform(0, jitter_x), height - rng.uniform(0, jitter_y),
        width - rng.uniform(0, jitter_x), rng.uniform(0, jitter_y),
    )
    return image.transform((width, height), Image.QUAD, quad, resample=Image.BICUBIC, fillcolor=(90, 90, 92))
