"""The sheet has to come out of the frame before the engine sees it (#53)."""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from crop_to_sheet import crop_to_sheet, sheet_box  # noqa: E402

# A phone frame: 9:16, a wooden table, a near-A4 sheet lying on it.
_FRAME = (574, 1020)
_SHEET = (80, 140, 494, 726)
_WOOD = (150, 96, 52)
_PAPER = (243, 241, 236)


def _photo(shadow: bool = False) -> Image.Image:
    image = Image.new("RGB", _FRAME, _WOOD)
    draw = ImageDraw.Draw(image)
    draw.rectangle(_SHEET, fill=_PAPER)
    if shadow:
        # A hand's shadow across the lower third, which is in every real photo
        # and is what breaks a largest-contiguous-run cropper.
        draw.rectangle((_SHEET[0], 560, _SHEET[2], _SHEET[3]), fill=(120, 119, 116))
    return image


def test_the_crop_finds_the_sheet_in_the_frame():
    left, top, right, bottom = sheet_box(_photo())

    assert abs(left - _SHEET[0]) < 24
    assert abs(top - _SHEET[1]) < 24
    assert abs(right - _SHEET[2]) < 24
    assert abs(bottom - _SHEET[3]) < 24


def test_a_shadow_across_the_sheet_does_not_truncate_the_crop():
    # The shadowed band is no longer bright enough to read as paper, so a
    # cropper that takes the largest contiguous bright run stops at 560 and
    # loses the bottom quarter of the sheet.
    _, _, _, bottom = sheet_box(_photo(shadow=True))

    assert bottom > 560


def test_cropping_moves_the_aspect_toward_the_training_distribution():
    photo = _photo()
    frame_aspect = photo.width / photo.height
    cropped = crop_to_sheet(photo)

    assert abs(cropped.width / cropped.height - 0.707) < abs(frame_aspect - 0.707)


def test_a_frame_with_no_sheet_in_it_is_left_alone():
    # Fail open on the geometry, not on a guess: a blank crop would hand the
    # engine a slice of table and it would read nothing rather than say so.
    blank = Image.new("RGB", _FRAME, _WOOD)

    assert sheet_box(blank) == (0, 0, *_FRAME)
