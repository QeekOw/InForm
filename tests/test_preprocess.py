"""The sheet has to come out of the frame before Donut sees it (#53)."""

import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from inform.preprocess import (
    _MIN_ASPECT_GAIN,
    _aspect_gain,
    _box_from_mask,
    _is_plausible_sheet,
    _paper_mask,
    crop_if_misframed,
    crop_to_sheet,
    sheet_box,
)

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


def _already_framed() -> Image.Image:
    """A synthetic training image: sheet at ~0.706 with a thin surface border."""
    image = Image.new("RGB", (600, 850), _WOOD)
    ImageDraw.Draw(image).rectangle((20, 20, 580, 830), fill=_PAPER)
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


def test_a_misframed_photo_is_cropped():
    photo = _photo()

    assert crop_if_misframed(photo).size != photo.size


def test_an_image_already_framed_like_the_training_set_is_untouched():
    # Cropping these costs ~2 points on synthetic sheets, so the guard has to
    # decline. Identity, not merely a similar size.
    framed = _already_framed()

    assert crop_if_misframed(framed) is framed


def test_a_frame_with_no_sheet_is_never_cropped():
    blank = Image.new("RGB", _FRAME, _WOOD)

    assert crop_if_misframed(blank) is blank


# The inputs #54 lists as never tried. Flat colour, so these exercise the paper
# mask and the guards rather than real photo texture -- they say what the
# detector does on a dark desk, not how well it does it.


def _cut_off_at_the_edge() -> Image.Image:
    """A sheet running past the right edge of the frame."""
    image = Image.new("RGB", _FRAME, _WOOD)
    ImageDraw.Draw(image).rectangle((150, 100, 700, 726), fill=_PAPER)
    return image


def _bright_card_on_a_dark_desk() -> Image.Image:
    """Something small, bright and sheet-shaped that is not the sheet."""
    image = Image.new("RGB", _FRAME, (28, 28, 30))
    ImageDraw.Draw(image).rectangle((230, 420, 330, 560), fill=_PAPER)
    return image


def test_a_sheet_cut_off_by_the_frame_is_not_cropped():
    # The dangerous case: the detector confidently bounds the visible part, the
    # crop improves the aspect (+0.104, over the 0.10 threshold), and Donut gets
    # a sheet with its right third missing -- which it reads confidently and the
    # cross-checks have nothing to object to.
    photo = _cut_off_at_the_edge()

    assert crop_if_misframed(photo) is photo


def test_a_small_bright_object_is_not_mistaken_for_the_sheet():
    # Aspect gain is +0.145 here, the highest of any case measured. Area is what
    # separates it: 2% of the frame against ~60% for a real hold-out sheet.
    photo = _bright_card_on_a_dark_desk()

    assert crop_if_misframed(photo) is photo


def test_a_sheet_on_a_dark_desk_is_still_cropped():
    # The guards may only ever decline, so the case the module exists for has to
    # survive them on a surface other than the wooden table it was tuned on.
    photo = Image.new("RGB", _FRAME, (28, 28, 30))
    ImageDraw.Draw(photo).rectangle(_SHEET, fill=_PAPER)

    assert crop_if_misframed(photo).size != photo.size


def test_a_sheet_on_a_bright_placemat_is_cropped_to_include_the_whole_sheet():
    # The mask takes the placemat for paper too, so the box is too big. That is
    # the harmless direction: the crop still contains every value on the sheet.
    photo = Image.new("RGB", _FRAME, _WOOD)
    draw = ImageDraw.Draw(photo)
    draw.rectangle((40, 100, 534, 820), fill=(230, 228, 225))
    draw.rectangle((120, 200, 450, 700), fill=_PAPER)

    left, top, right, bottom = sheet_box(photo)

    assert crop_if_misframed(photo).size != photo.size
    assert left <= 120 and top <= 200
    assert right >= 450 and bottom >= 700


def _surfaces_and_lights() -> dict[str, Image.Image]:
    """One frame per untested input in #54, keyed by what it is."""
    scan = Image.new("RGB", (1240, 1754), _PAPER)

    night = Image.new("RGB", _FRAME, (40, 30, 20))
    ImageDraw.Draw(night).rectangle(_SHEET, fill=(118, 96, 64))

    two_sheets = Image.new("RGB", _FRAME, _WOOD)
    draw = ImageDraw.Draw(two_sheets)
    draw.rectangle((30, 140, 270, 726), fill=_PAPER)
    draw.rectangle((310, 140, 550, 726), fill=_PAPER)

    patterned = Image.new("RGB", _FRAME, _WOOD)
    draw = ImageDraw.Draw(patterned)
    for y in range(0, _FRAME[1], 80):
        draw.rectangle((0, y, _FRAME[0], y + 30), fill=(225, 225, 228))
    draw.rectangle(_SHEET, fill=_PAPER)

    glare = _photo()
    ImageDraw.Draw(glare).rectangle((0, 300, _FRAME[0], 420), fill=(252, 252, 252))

    white_desk = Image.new("RGB", _FRAME, (248, 248, 250))
    ImageDraw.Draw(white_desk).rectangle(_SHEET, fill=_PAPER)

    against_clothing = Image.new("RGB", _FRAME, (200, 200, 205))
    ImageDraw.Draw(against_clothing).rectangle(_SHEET, fill=_PAPER)

    return {
        "a scan with no frame around it": scan,
        "a photo taken at night under warm light": night,
        "two sheets in frame": two_sheets,
        "a patterned surface": patterned,
        "heavy glare spilling onto the table": glare,
        "a white desk": white_desk,
        "a sheet held against clothing": against_clothing,
    }


def test_the_untested_surfaces_all_fail_towards_no_crop():
    # None of these is a case the detector handles -- the mask assumption does
    # not hold on any of them. The claim is only that each one degrades to the
    # behaviour that shipped before this module, rather than to half a sheet.
    for description, photo in _surfaces_and_lights().items():
        assert crop_if_misframed(photo) is photo, description


# The real photos are one consenting subject's health records and live outside
# the repo (ADR-0011), so this runs only where they are. They sit in one checkout
# while the code is worked on in another, so the directory can be pointed at:
#     INFORM_REAL_HOLDOUT=/path/to/real_holdout pytest tests/test_preprocess.py
_REAL_HOLDOUT = Path(
    os.environ.get("INFORM_REAL_HOLDOUT")
    or Path(__file__).resolve().parents[1] / "data" / "real_holdout"
)
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@pytest.mark.skipif(
    not _REAL_HOLDOUT.is_dir(),
    reason=f"needs the real hold-out photos at {_REAL_HOLDOUT}",
)
def test_the_guards_decline_nothing_the_real_holdout_already_cropped():
    """The guards may only ever decline, so they have to decline nothing real.

    A declined crop costs a real upload ~10 points of accuracy (ADR-0012), which
    is far more than the silent error the guards buy back. Checking the crop
    decision rather than the scored read is deliberate: if every photo that
    cropped before still crops to the same box, the scored numbers are unchanged
    by construction, and this needs no checkpoint, no torch and no GPU.
    """
    photos = sorted(p for p in _REAL_HOLDOUT.rglob("*") if p.suffix.lower() in _IMAGE_SUFFIXES)
    assert photos, f"no images under {_REAL_HOLDOUT}"

    declined = []
    for path in photos:
        image = Image.open(path).convert("RGB")
        paper = _paper_mask(image)
        box = _box_from_mask(image, paper)
        if _aspect_gain(image, box) >= _MIN_ASPECT_GAIN and not _is_plausible_sheet(
            image, box, paper
        ):
            declined.append(path.name)

    assert not declined, (
        f"{len(declined)} of {len(photos)} hold-out photos cropped before the #54 guards and "
        f"do not now: {', '.join(declined)}. Either a threshold is too tight, or these photos "
        f"really are cut off at the frame edge -- check the crop by eye before loosening it."
    )
