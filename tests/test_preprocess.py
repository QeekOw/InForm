"""The sheet has to come out of the frame before Donut sees it (#53)."""

import os
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from inform.preprocess import (
    _MIN_ASPECT_GAIN,
    _aspect_gain,
    crop_if_misframed,
    crop_to_sheet,
    sheet_box,
)

# A phone frame: 9:16, a wooden table, a near-A4 sheet lying on it.
_FRAME = (574, 1020)
_SHEET = (80, 140, 494, 726)
_WOOD = (150, 96, 52)
_PAPER = (243, 241, 236)
# Dark enough to fall out of the paper mask (value 0.31 against its 0.40 floor),
# which is what a hand's shadow does to a real photo.
_SHADOW = (80, 79, 77)


def _photo(shadow: bool = False) -> Image.Image:
    image = Image.new("RGB", _FRAME, _WOOD)
    draw = ImageDraw.Draw(image)
    draw.rectangle(_SHEET, fill=_PAPER)
    if shadow:
        # A hand's shadow across the lower third, which is in every real photo
        # and is what breaks a largest-contiguous-run cropper.
        draw.rectangle((_SHEET[0], 480, _SHEET[2], 620), fill=_SHADOW)
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
    # cropper that takes the largest contiguous bright run stops at 480 and
    # loses the bottom of the sheet below the shadow.
    _, _, _, bottom = sheet_box(_photo(shadow=True))

    assert bottom > 620


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


def _bright_card_on_a_dark_desk() -> Image.Image:
    """Something small, bright and sheet-shaped that is not the sheet."""
    image = Image.new("RGB", _FRAME, (28, 28, 30))
    ImageDraw.Draw(image).rectangle((230, 420, 330, 560), fill=_PAPER)
    return image


# A sheet running past the frame, off each edge and corner, with and without a
# shadow across it. Each one is placed so the crop would improve the aspect --
# a cut-off the aspect guard already declines says nothing about this guard.
_CUT_OFF = {
    "off the right edge": ((150, 100, 700, 726), None),
    "off the left edge": ((-126, 100, 424, 726), None),
    "off the top": ((80, -58, 494, 528), None),
    "off the bottom": ((80, 492, 494, 1078), None),
    "off the bottom right corner": ((333, 680, 747, 1266), None),
    "off the top left corner": ((-173, -246, 241, 340), None),
    "off the right edge, under a shadow": ((150, 100, 700, 726), (0.4, 0.8)),
    "off a corner, under a shadow": ((325, 668, 739, 1254), (0.55, 0.75)),
}


def _cut_off(sheet, shadow) -> Image.Image:
    image = Image.new("RGB", _FRAME, _WOOD)
    draw = ImageDraw.Draw(image)
    draw.rectangle(sheet, fill=_PAPER)
    if shadow:
        left, top, right, bottom = sheet
        height = bottom - top
        draw.rectangle(
            (left, top + height * shadow[0], right, top + height * shadow[1]),
            fill=_SHADOW,
        )
    return image


@pytest.mark.parametrize("sheet, shadow", _CUT_OFF.values(), ids=_CUT_OFF.keys())
def test_a_sheet_cut_off_by_the_frame_is_not_cropped(sheet, shadow):
    # The dangerous case: the detector confidently bounds the visible part, the
    # crop improves the aspect, and Donut gets part of a sheet -- which it reads
    # confidently and the cross-checks have nothing to object to.
    photo = _cut_off(sheet, shadow)
    assert _aspect_gain(photo, sheet_box(photo)) >= _MIN_ASPECT_GAIN

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
# A path given that way that does not exist fails rather than skips.
_REAL_HOLDOUT_OVERRIDE = os.environ.get("INFORM_REAL_HOLDOUT")
_REAL_HOLDOUT = Path(
    _REAL_HOLDOUT_OVERRIDE
    or Path(__file__).resolve().parents[1] / "data" / "real_holdout"
)
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
# The twelve photos of ADR-0006. Fewer means the corpus is incomplete, and the
# check would pass on whatever is left.
_REAL_HOLDOUT_SIZE = 12


@pytest.mark.skipif(
    not _REAL_HOLDOUT_OVERRIDE and not _REAL_HOLDOUT.is_dir(),
    reason=f"needs the real hold-out photos at {_REAL_HOLDOUT}",
)
def test_every_real_holdout_photo_is_still_cropped_to_the_sheet():
    """The guards may only ever decline, so they have to decline nothing real.

    A declined crop costs a real upload ~10 points of accuracy (ADR-0012), which
    is far more than the silent error the guards buy back. Checking the crop
    rather than the scored read is deliberate: if every photo still crops to the
    same box, the scored numbers are unchanged by construction, and this needs
    no checkpoint, no torch and no GPU.
    """
    photos = sorted(
        p for p in _REAL_HOLDOUT.glob("*") if p.suffix.lower() in _IMAGE_SUFFIXES
    )
    assert len(photos) >= _REAL_HOLDOUT_SIZE, (
        f"{len(photos)} images under {_REAL_HOLDOUT}, expected {_REAL_HOLDOUT_SIZE}"
    )

    declined = []
    for path in photos:
        image = Image.open(path).convert("RGB")
        if crop_if_misframed(image).size != image.crop(sheet_box(image)).size:
            declined.append(path.name)

    assert not declined, (
        f"{len(declined)} of {len(photos)} hold-out photos are not cropped to the "
        f"sheet: {', '.join(declined)}. Either a threshold is too tight, or these "
        f"photos really are cut off at the frame edge -- check the crop by eye "
        f"before loosening it."
    )
