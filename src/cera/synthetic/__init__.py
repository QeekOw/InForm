import io
import random
import shutil
import subprocess
import tempfile
from pathlib import Path
from string import Template
from typing import Literal

from PIL import Image, ImageEnhance, ImageFilter

from cera.inbody import InBodyPayload, SegmentalLean

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_WINDOW_SIZE = {"inbody_270": "560,420", "inbody_570": "560,460"}

# ponytail: fixed physiological ranges/proportions, not learned from data.
# Tune against real InBody sheets if the synthetic distribution drifts.
_WEIGHT_RANGE_KG = (50.0, 100.0)
_PBF_RANGE_PCT = (10.0, 35.0)
_SMM_FRACTION_OF_LBM_RANGE = (0.55, 0.65)
_VISCERAL_FAT_RANGE = (1, 20)
_SEGMENT_FRACTIONS_OF_LBM = {"left_arm_kg": 0.08, "right_arm_kg": 0.08, "left_leg_kg": 0.17, "right_leg_kg": 0.17}
_ASYMMETRY_PROBABILITY = 0.3
_ASYMMETRY_DEVIATION_PCT = 8.0  # comfortably past the >5% bilateral-asymmetry threshold

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
    visceral_fat_level = rng.randint(*_VISCERAL_FAT_RANGE) if device == "inbody_570" else None

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


def _fill_template(device: Literal["inbody_270", "inbody_570"], payload: InBodyPayload) -> str:
    template = Template((_TEMPLATE_DIR / f"{device}.html").read_text(encoding="utf-8"))
    values = {
        "weight_kg": payload.weight_kg,
        "lean_body_mass_kg": payload.lean_body_mass_kg,
        "percent_body_fat": payload.percent_body_fat,
        "skeletal_muscle_mass_kg": payload.skeletal_muscle_mass_kg,
        "basal_metabolic_rate_kcal": payload.basal_metabolic_rate_kcal,
        "left_arm_kg": payload.segmental_lean.left_arm_kg,
        "right_arm_kg": payload.segmental_lean.right_arm_kg,
        "left_leg_kg": payload.segmental_lean.left_leg_kg,
        "right_leg_kg": payload.segmental_lean.right_leg_kg,
        "trunk_kg": payload.segmental_lean.trunk_kg,
    }
    if device == "inbody_570":
        values["visceral_fat_level"] = payload.visceral_fat_level
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
        return Image.open(png_path).convert("RGB").copy()


def _augment(image: Image.Image, rng: random.Random) -> Image.Image:
    """Mimic phone capture: blur, rotation, perspective warp, lighting, JPEG noise (ADR-0007)."""
    image = image.rotate(rng.uniform(-1.5, 1.5), expand=True, fillcolor="white")
    image = _perspective_warp(image, rng)
    image = image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0, 1.5)))
    image = ImageEnhance.Brightness(image).enhance(rng.uniform(0.85, 1.15))
    image = ImageEnhance.Contrast(image).enhance(rng.uniform(0.9, 1.1))
    image = _jpeg_noise(image, rng)
    return image


def _jpeg_noise(image: Image.Image, rng: random.Random) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=rng.randint(60, 90))
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def _perspective_warp(image: Image.Image, rng: random.Random) -> Image.Image:
    width, height = image.size
    jitter_x = width * 0.025
    jitter_y = height * 0.015
    quad = (
        rng.uniform(0, jitter_x), rng.uniform(0, jitter_y),
        rng.uniform(0, jitter_x), height - rng.uniform(0, jitter_y),
        width - rng.uniform(0, jitter_x), height - rng.uniform(0, jitter_y),
        width - rng.uniform(0, jitter_x), rng.uniform(0, jitter_y),
    )
    return image.transform((width, height), Image.QUAD, quad, resample=Image.BICUBIC, fillcolor="white")
