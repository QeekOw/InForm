"""Check that generated sheets match the geometry of a real InBody printout.

Donut learned whatever geometry the synthetic set had. When that differs from a
real photographed sheet, the model reads the training distribution well and the
real one badly -- which is what `donut-both-v3` does (48% on its own synthetic
270 set, 3 usable reads out of 12 real photos).

Two things have to line up, and this script measures both:

* **Aspect.** A real InBody sheet is A4 portrait (0.707). The rendered sheet is
  measured before augmentation, because that is what the template controls.
* **Resolution.** The render should be at least as wide as a phone photo
  (~2300 px), so both get *downscaled* onto Donut's fixed 2560x1920 canvas
  rather than the synthetic one being upscaled onto it.

Run it after editing a template; it is the target to iterate against.
"""

import argparse
import io
import random

from PIL import Image

from inform.synthetic import (
    MIN_SHEET_WIDTH_PX,
    SHEET_ASPECT,
    SHEET_ASPECT_TOLERANCE,
    _augment,
    _generate_values,
    _render,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=6, help="Sheets per device")
    parser.add_argument("--seed-start", type=int, default=9001)
    args = parser.parse_args()

    print(f"target: aspect {SHEET_ASPECT:.3f} +/- {SHEET_ASPECT_TOLERANCE}   width >= {MIN_SHEET_WIDTH_PX}px\n")
    failures = 0

    for device in ("inbody_270", "inbody_570"):
        aspects, widths = [], []
        for seed in range(args.seed_start, args.seed_start + args.samples):
            rendered = _render(device, _generate_values(device, seed))
            augmented = _augment(rendered, random.Random(seed))
            aspects.append(rendered.width / rendered.height)
            widths.append(rendered.width)
            print(
                f"  {device}  seed {seed}  render {rendered.width}x{rendered.height}"
                f"  aspect {aspects[-1]:.3f}   final {augmented.width}x{augmented.height}"
            )

        mean_aspect = sum(aspects) / len(aspects)
        min_width = min(widths)
        aspect_ok = abs(mean_aspect - SHEET_ASPECT) <= SHEET_ASPECT_TOLERANCE
        width_ok = min_width >= MIN_SHEET_WIDTH_PX
        failures += (not aspect_ok) + (not width_ok)

        print(
            f"  -> {device}: mean aspect {mean_aspect:.3f} "
            f"[{'OK' if aspect_ok else 'TOO SQUARE -- sheet needs more vertical extent'}]"
            f", min width {min_width}px "
            f"[{'OK' if width_ok else 'TOO LOW -- raise _DEVICE_SCALE_FACTOR'}]\n"
        )

    if failures:
        print(f"{failures} check(s) failed.")
    else:
        print("All checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
