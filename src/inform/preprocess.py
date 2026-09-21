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


def sheet_box(image: Image.Image) -> tuple[int, int, int, int]:
    """The bounding box of the sheet within a photographed frame.

    Percentiles of the paper mask rather than its largest contiguous run: the
    shadow that falls across the lower third of a hand-held photo splits the
    mask in two, and the larger piece is not the whole sheet.

    Returns the full frame when no paper is found, so a caller that crops
    unconditionally still gets a valid image back.
    """
    thumbnail = image.resize(
        (max(1, image.width // _DOWNSCALE), max(1, image.height // _DOWNSCALE))
    )
    hsv = np.asarray(thumbnail.convert("HSV"), dtype=np.float32) / 255.0
    paper = (hsv[..., 1] < _MAX_SATURATION) & (hsv[..., 2] > _MIN_VALUE)

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


def crop_if_misframed(image: Image.Image) -> Image.Image:
    """Crop to the sheet when the frame is the wrong shape for the canvas.

    Returns the image unchanged when cropping would not materially help, which
    is the case for anything already framed like the training set.
    """
    box = sheet_box(image)
    if _aspect_gain(image, box) < _MIN_ASPECT_GAIN:
        return image
    return image.crop(box)
