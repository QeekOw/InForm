"""Crop a photographed InBody sheet out of the frame around it.

`check_sheet_geometry.py` compares the *rendered* sheet against A4, which is the
right target for a template. It says nothing about what reaches the model at
inference, and that turned out to be the gap: synthetic training images are
cropped tight to the sheet (`_crop_to_content`, aspect ~0.706), while a real
photo is a whole 9:16 phone frame (0.563) with the sheet lying on a table inside
it. Donut resizes both onto one fixed 1920x2560 canvas, so the real sheet
arrives smaller and squashed harder than anything the model trained on.

Cropping the frame down to the sheet, with no retrain and no change to any
checkpoint, moves `donut-both-v3` from 33/36 core fields to 36/36 and
`segmental_lean.right_arm_kg` from 1/6 to 4/6 on the real hold-out (#53).

Paper is the bright, unsaturated region; a table is not. Percentiles rather than
a contiguous run, because the shadow falling across the lower third of a photo
splits the paper mask into pieces and the largest piece is not the sheet.

    python scripts/crop_to_sheet.py <src-dir> <dst-dir>
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

# A pixel is paper if it is bright and close to grey. Wood, skin and cloth are
# all more saturated than this; glare and shadow on paper stay inside it.
MAX_SATURATION = 0.25
MIN_VALUE = 0.40
# Ignore the outer 1% of paper pixels, which is glare bleeding onto the table.
LO, HI = 1.0, 99.0
DOWNSCALE = 8


def sheet_box(image: Image.Image) -> tuple[int, int, int, int]:
    """The bounding box of the sheet within a photographed frame."""
    small = image.resize((max(1, image.width // DOWNSCALE), max(1, image.height // DOWNSCALE)))
    hsv = np.asarray(small.convert("HSV"), dtype=np.float32) / 255.0
    paper = (hsv[..., 1] < MAX_SATURATION) & (hsv[..., 2] > MIN_VALUE)

    ys, xs = np.nonzero(paper)
    if len(xs) == 0:
        return 0, 0, image.width, image.height
    scale_x = image.width / paper.shape[1]
    scale_y = image.height / paper.shape[0]
    return (
        int(np.percentile(xs, LO) * scale_x),
        int(np.percentile(ys, LO) * scale_y),
        int(np.percentile(xs, HI) * scale_x),
        int(np.percentile(ys, HI) * scale_y),
    )


def crop_to_sheet(image: Image.Image) -> Image.Image:
    return image.crop(sheet_box(image))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("src", type=Path, help="Directory of photographed sheets")
    parser.add_argument("dst", type=Path, help="Where to write the crops")
    args = parser.parse_args()

    args.dst.mkdir(parents=True, exist_ok=True)
    print(f"{'file':16s} {'frame':>12s} {'crop':>12s} {'aspect':>7s} {'of frame':>9s}")
    for path in sorted(p for p in args.src.iterdir() if p.suffix.lower() in {".png", ".jpg"}):
        image = Image.open(path).convert("RGB")
        cropped = crop_to_sheet(image)
        cropped.save(args.dst / path.name)
        area = (cropped.width * cropped.height) / (image.width * image.height)
        print(
            f"{path.name:16s} {f'{image.width}x{image.height}':>12s} "
            f"{f'{cropped.width}x{cropped.height}':>12s} "
            f"{cropped.width / cropped.height:>7.3f} {area:>8.1%}"
        )
    print("\nA4 portrait 0.707 | synthetic ~0.706 | Donut canvas 1920x2560 = 0.750")


if __name__ == "__main__":
    main()
