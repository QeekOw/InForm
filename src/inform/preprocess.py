"""Give Donut the picture it was trained on: a sheet, not a photo of a table.

Synthetic training images are cropped tight to the sheet (`_crop_to_content`)
and come out at aspect ~0.706. A real upload is a whole phone frame -- measured
at 0.563 across the real hold-out -- with the sheet lying on a table inside it.
Donut resizes whatever it is handed onto one fixed 1920x2560 canvas, so an
uncropped sheet arrives both smaller and squashed harder than anything in
training.

Cropping the frame down to the sheet, with no retrain, moves `donut-both-v3`
from 33/36 core fields to 36/36 on the real hold-out and
`segmental_lean.right_arm_kg` from 1/6 to 4/6 (#53).

**Cropping is not free, so it is conditional.** On synthetic sheets, which are
already framed the way the model trained, the same crop costs 1.9 points
(173/264 to 168/264 field observations, `donut-both-v3`). `crop_if_misframed`
therefore crops only when doing so materially improves how well the image fits
the canvas, which is exactly the case the real photos are in and the synthetic
ones are not. Measured aspect gain (see `_aspect_gain`):

    real hold-out photos   +0.125 .. +0.184   (n=12, every one cropped)
    synthetic sheets       -0.101 .. +0.101   (n=120, median ~0, none cropped)

When it declines, the image passes through untouched and behaviour is exactly
what it was before this module existed. That is the safe direction: a missed
crop costs accuracy we never had, while a wrong crop would hand the model half
a sheet and it would read the half confidently.

**That last case is reachable, so the box is checked for shape too** (#54). The
aspect guard asks whether cropping helps, not whether what was found is a
sheet: a sheet cut off at the frame edge clears it, and so does a bright card
on a dark desk. `_is_plausible_sheet` declines both. It is an in-band check
rather than a wider photo set because the hold-out is the maximum obtainable
corpus (ADR-0010, 2026-09-20).
"""

import numpy as np
from PIL import Image

# A pixel is paper if it is bright and close to grey. Wood, skin and cloth are
# more saturated than this; glare and shadow on paper stay inside it.
_MAX_SATURATION = 0.25
_MIN_VALUE = 0.40
# Ignore the outer 1% of paper pixels, which is glare bleeding onto the table.
_LO, _HI = 1.0, 99.0
# Detection runs on a thumbnail: the sheet's edge is a centimetre of pixels and
# this is 64x less work.
_DOWNSCALE = 8

# Donut's canvas (1920x2560). The thing every input is resized onto, so it is
# what "correctly framed" is measured against.
_CANVAS_ASPECT = 1920 / 2560

# How much closer to the canvas the crop must bring the aspect before it is
# worth taking. Set from the measured gap between the two populations above;
# biased low, because missing a crop on a real upload costs a user ~10 points
# of accuracy while cropping a synthetic eval image costs ~2.
_MIN_ASPECT_GAIN = 0.10

# The aspect guard asks whether cropping helps, not whether what was found is a
# sheet. Two constructed cases clear it while being wrong (#54), so the box is
# also checked for shape before it is trusted.
#
# A sheet running off the edge of the frame is the dangerous one: the detector
# bounds the visible part, the crop improves the aspect, and Donut gets part of
# a sheet, reads it confidently, and the cross-checks have nothing to object to.
# It is caught by how much of the box's side along a frame edge is paper. Where
# the sheet was cut off, paper runs the length of that side; a whole sheet
# leaves the surface showing between it and the frame.
#
# Measured on the box's side rather than the whole frame edge, because a corner
# cut-off only lays paper along part of the frame edge (0.38 at worst), which
# no threshold can separate from the real photos (0.325 at worst):
#
#     cut off, any edge or corner     0.97 .. 1.00
#     cut off, shadow across it       0.58 .. 0.98
#     twelve real hold-out photos     0.13 .. 0.49
#
# The gap is narrow on both sides, and both sides are constructed or n=12 on
# one surface. A brighter desk reads higher on the real side.
_MAX_EDGE_COVERAGE = 0.55

# Below this share of the frame the box is likelier a glint, a card or a label
# than the sheet, and even when it is the sheet it carries too few pixels to
# survive the upscale onto the canvas. Real hold-out sheets fill 0.58-0.67 of
# the frame and the constructed false positives fill 0.02, so this sits well
# clear of both: declining here costs a read that would have been unreadable
# anyway, while taking the crop is a confident read of the wrong thing.
_MIN_AREA = 0.10


def _paper_mask(image: Image.Image) -> np.ndarray:
    """Which pixels of a thumbnail of `image` read as paper."""
    thumbnail = image.resize(
        (max(1, image.width // _DOWNSCALE), max(1, image.height // _DOWNSCALE))
    )
    hsv = np.asarray(thumbnail.convert("HSV"), dtype=np.float32) / 255.0
    return (hsv[..., 1] < _MAX_SATURATION) & (hsv[..., 2] > _MIN_VALUE)


def _box_from_mask(image: Image.Image, paper: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.nonzero(paper)
    if len(xs) == 0:
        return 0, 0, image.width, image.height
    scale_x = image.width / paper.shape[1]
    scale_y = image.height / paper.shape[0]
    return (
        int(np.percentile(xs, _LO) * scale_x),
        int(np.percentile(ys, _LO) * scale_y),
        int(np.percentile(xs, _HI) * scale_x),
        int(np.percentile(ys, _HI) * scale_y),
    )


def sheet_box(image: Image.Image) -> tuple[int, int, int, int]:
    """The bounding box of the sheet within a photographed frame.

    Percentiles of the paper mask rather than its largest contiguous run: the
    shadow that falls across the lower third of a hand-held photo splits the
    mask in two, and the larger piece is not the whole sheet.

    Returns the full frame when no paper is found, so a caller that crops
    unconditionally still gets a valid image back.
    """
    return _box_from_mask(image, _paper_mask(image))


def crop_to_sheet(image: Image.Image) -> Image.Image:
    """Crop to the sheet unconditionally. For diagnostics; engines want the guard."""
    return image.crop(sheet_box(image))


def _aspect_gain(image: Image.Image, box: tuple[int, int, int, int]) -> float:
    """How much closer to the canvas aspect cropping to `box` would bring us."""
    left, top, right, bottom = box
    if right <= left or bottom <= top:
        return 0.0
    before = abs(image.width / image.height - _CANVAS_ASPECT)
    after = abs((right - left) / (bottom - top) - _CANVAS_ASPECT)
    return before - after


def _is_plausible_sheet(
    image: Image.Image, box: tuple[int, int, int, int], paper: np.ndarray
) -> bool:
    """Whether `box` bounds a whole sheet rather than a lucky rectangle.

    Cheap and in-band, because the photos that would settle the detector's real
    range do not exist: the hold-out is the maximum obtainable corpus (ADR-0010,
    2026-09-20). So the check is on the mask the detector already built, and it
    can only ever decline -- which is the direction this module is already built
    to fail in.
    """
    left, top, right, bottom = box
    if (right - left) * (bottom - top) / (image.width * image.height) < _MIN_AREA:
        return False
    # The box's extent in thumbnail pixels, where the mask lives.
    rows, cols = paper.shape
    x0, x1 = left * cols // image.width, right * cols // image.width
    y0, y1 = top * rows // image.height, bottom * rows // image.height
    coverage = max(
        paper[0, x0:x1].mean(),
        paper[-1, x0:x1].mean(),
        paper[y0:y1, 0].mean(),
        paper[y0:y1, -1].mean(),
    )
    return coverage < _MAX_EDGE_COVERAGE


def crop_if_misframed(image: Image.Image) -> Image.Image:
    """Crop to the sheet when the frame is the wrong shape for the canvas.

    Returns the image unchanged when cropping would not materially help, which
    is the case for anything already framed like the training set, or when the
    box found does not look like a whole sheet (#54).
    """
    paper = _paper_mask(image)
    box = _box_from_mask(image, paper)
    if not _is_plausible_sheet(image, box, paper):
        return image
    if _aspect_gain(image, box) < _MIN_ASPECT_GAIN:
        return image
    return image.crop(box)
