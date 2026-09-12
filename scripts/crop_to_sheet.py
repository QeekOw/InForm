"""Crop photographed InBody sheets out of the frames around them.

The engine does this itself now (`inform.preprocess`, wired into
`donut.load_engine`). This script is the diagnostic version: it crops a whole
directory unconditionally and prints the geometry, which is how the effect was
measured in #53 and how to check a new batch of photos before trusting it.

`check_sheet_geometry.py` is the sibling that measures the *rendered* sheet
against A4. That is the right target for a template and says nothing about what
reaches the model at inference, which is what this covers.

    python scripts/crop_to_sheet.py <src-dir> <dst-dir>
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inform.preprocess import crop_to_sheet  # noqa: E402

_SUFFIXES = {".png", ".jpg", ".jpeg"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("src", type=Path, help="Directory of photographed sheets")
    parser.add_argument("dst", type=Path, help="Where to write the crops")
    args = parser.parse_args()

    args.dst.mkdir(parents=True, exist_ok=True)
    print(f"{'file':16s} {'frame':>12s} {'crop':>12s} {'aspect':>7s} {'of frame':>9s}")
    for path in sorted(p for p in args.src.iterdir() if p.suffix.lower() in _SUFFIXES):
        image = Image.open(path).convert("RGB")
        cropped = crop_to_sheet(image)
        cropped.save(args.dst / path.name)
        area = (cropped.width * cropped.height) / (image.width * image.height)
        print(
            f"{path.name:16s} {f'{image.width}x{image.height}':>12s} "
            f"{f'{cropped.width}x{cropped.height}':>12s} "
            f"{cropped.width / cropped.height:>7.3f} {area:>8.1%}"
        )
    print("")
    print("A4 portrait 0.707 | synthetic ~0.706 | Donut canvas 1920x2560 = 0.750")


if __name__ == "__main__":
    main()
