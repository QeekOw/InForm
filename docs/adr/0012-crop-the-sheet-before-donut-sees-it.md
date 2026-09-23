# ADR-0012: Crop the sheet out of the photo before Donut sees it

**Status:** Accepted
**Date:** 2026-09-12
**Module:** 1 (OCR)

## Context

Donut trains on synthetic sheets that `_crop_to_content()` crops tight to the page. They
come out at aspect ~0.706, measured over 600 sheets of `synth_v5_both`. A real upload is a
whole phone frame — 0.563 across all twelve real hold-out photos — with the sheet lying on
a table inside it, surrounded by wood and a hand's shadow.

Donut resizes whatever it is handed onto one fixed 1920x2560 canvas (0.750). So an
uncropped photo gives the model a sheet that is both smaller than anything in training
(~60% of the frame) and squashed along a different axis. That is a train/serve input
mismatch, and it sat upstream of every field-level hypothesis Module 1 has chased.

Measured on `donut-both-v3`, the shipped default, cropping the photo to the sheet first
with no retrain and no change to the checkpoint (#53):

| | uncropped | cropped |
|---|---|---|
| core fields | 33/36 | **36/36** |
| segmental lean | 23/30 | **27/30** |
| critical (LBM + limbs) | 26/36 | **33/36** |
| `segmental_lean.right_arm_kg` | 1/6 | **4/6** |

The control is exact: the same checkpoint re-run on uncropped images reproduces the
recorded baseline in every cell, so the difference is the crop and nothing else.

This also mis-ranked two retrains. Scored uncropped, v5 looked like a regression; scored
cropped, it has the best segmental lean (28/30) and critical (34/36) of any checkpoint, and
`right_arm_kg` of 5/6. The 270 Segmental Fat fix had worked all along (#50).

## Decision

**The Donut engine crops the sheet out of the frame before inference**, in
`inform.preprocess.crop_if_misframed`, called from `donut.load_engine`'s `extract`.

- **In the engine, not the seam.** `extract_inbody(image_path) -> InBodyExtraction` is
  unchanged; it is Track B's contract. The crop is also genuinely Donut-specific: it exists
  to match *Donut's* training distribution, and the VLM oracle has no equivalent constraint.
  Putting it in the engine keeps it in memory too, so no PHI is written to a temp file.
- **Conditional, on measured evidence.** Cropping is not free: on synthetic sheets, already
  framed the way the model trained, the same crop *costs* 1.9 points (173/264 to 168/264
  field observations). So the crop is taken only when it materially improves how well the
  image fits the canvas. Measured aspect gain separates the two populations cleanly:

  ```
  real hold-out photos   +0.125 .. +0.184   (n=12,  every one cropped)
  synthetic sheets       -0.101 .. +0.101   (n=120, median ~0, none cropped)
  ```

  The threshold is 0.10, biased toward cropping: missing a crop on a real upload costs a
  user ~10 points of accuracy, while cropping a synthetic eval image costs ~2.
- **Declining is the safe default.** When the guard says no, or no paper is found, the image
  passes through untouched and behaviour is exactly what it was before. A missed crop costs
  accuracy we never had; a wrong crop would hand the model half a sheet, which it would read
  confidently and the cross-checks would not catch.

## Considered Options

- **Crop unconditionally.** Simpler, and still net positive. Rejected: it pays the 1.9-point
  synthetic cost for nothing, and the synthetic set is how every future retrain is scored, so
  the cost lands on the measurement instrument.
- **Crop in `extract_inbody`.** Rejected: the seam hands the engine a `Path`, so cropping there
  means writing a cropped copy to disk — real health data in a temp file (ADR-0005) — and it
  would impose Donut's framing on the VLM oracle too.
- **Train on uncropped frames instead.** Correct in the long run and does not depend on
  detection working. Rejected as the *first* move: it costs a retrain, helps nothing already
  trained, and cannot be evaluated until the hold-out can resolve it (#24). Not foreclosed.
- **Refuse when detection is uncertain.** Rejected: a refusal is a worse outcome for the person
  than the read they get today, and today's read is not broken, only degraded.

## Consequences

- **Every existing checkpoint gets better on real photos at no cost**, including the one we
  ship. The gain is not a model improvement and should never be reported as one.
- **Engine comparisons must state their preprocessing.** Cropping changes which checkpoint
  wins without touching any checkpoint. `docs/training.md` §4 carries both tables for this
  reason.
- **The detector is tuned on twelve photos of one table.** Paper is masked as bright and
  unsaturated, which is a fair assumption for a printout and an untested one for a dark
  desk, a patterned surface, or a photo taken at night. The guard limits the blast radius
  to "no crop", not "bad crop", but the detector's real-world range is unmeasured.
  *Amended 2026-09-22: the blast-radius claim was too strong. See below.*
- **`numpy` becomes a base dependency.** `inform.preprocess` is on the runtime path and
  percentiles over a pixel mask are not something Pillow does well.
- **The synthetic cost is real and now measured**, so a future decision to crop
  unconditionally has a number attached rather than an intuition.

## Amendment (2026-09-22): the aspect guard alone lets bad crops through

**`crop_if_misframed` now also checks the box, in `_is_plausible_sheet`.** The original
decision rested on the claim that the worst case is "no crop". Probing the detector against
the inputs #54 lists as never tried shows that holds for most of them but not all. The aspect
guard asks whether cropping *helps*, not whether what was found *is a sheet*, and two kinds of
constructed frame clear it while being wrong:

| | aspect gain | area | edge coverage | before |
|---|---|---|---|---|
| twelve real hold-out photos | +0.125 .. +0.184 | 0.58–0.67 | 0.13–0.49 | cropped ✓ |
| **sheet cut off by the frame** | +0.10 .. +0.18 | 0.13–0.44 | **0.58–1.00** | cropped ✗ |
| **bright card on a dark desk** | +0.145 | **0.02** | 0.00 | cropped ✗ |

A cut-off sheet is the silent error this ADR said the guard prevented. Donut gets part of a
sheet, reads it confidently, and the cross-checks have nothing to object to.

Two thresholds, both of which can only ever *decline* a crop:

- `_MAX_EDGE_COVERAGE = 0.55`: how much of the box's side along a frame edge reads as paper,
  on whichever side reads highest. Where a sheet was cut off, paper runs the length of that
  side. A whole sheet leaves surface showing between it and the frame. Cut-off frames read
  0.97–1.00 off every edge and corner, and 0.58–0.98 with a hand's shadow across 20–40% of the
  sheet. The twelve real photos read 0.13–0.49.
- `_MIN_AREA = 0.10`: below this the box is likelier a glint, a card or a label than the
  sheet, and even when it is the sheet it carries too few pixels to survive the upscale onto
  the canvas. Real sheets fill 0.58–0.67 of the frame. The card fills 0.02.

**Two earlier edge checks were tried and rejected, and the real photos caught both.**

1. *Distance from the box to the frame border.* On constructed frames it separated cleanly:
   0.070–0.133 for a well-framed sheet against 0.016 for a cut-off one, so a 0.03 threshold
   looked safe. On the real photos it declined **eight of twelve**. Real sheets fill most of
   the frame and sit 0.021–0.052 from its edges. The constructed frames had drawn the sheet
   smaller and more centred than any real photo.
2. *How much of the whole frame edge is paper*, declining at 0.45. It kept all twelve real
   photos (0.325 at worst) and caught a sheet cut off along one edge (0.51–0.72). It missed
   two cases found in review. A sheet cut off at a corner only lays paper along part of each
   frame edge (0.38–0.44 with 39–48% of the sheet missing on each axis), and a shadow across a
   cut-off sheet breaks the paper along the edge (0.37). Both were cropped. No threshold on
   this signal can catch them without also declining a real photo.

Constructed evidence is only as good as the constructions. Both rejections came from running
the check against something other than the frames it was designed on.

**A fill-ratio (rectangularity) check was measured and rejected.** #54 suggested it, but it
reads 0.97 on both the correct crops and a cut-off sheet, so it does not close the hole. The
only frames it would catch are already declined on aspect, and it is the check most likely to
misfire on real photos, where the shadow band this module exists to survive breaks the mask.

- **The in-band check is a substitute for evidence, not a replacement.** The photos that
  would settle the detector's real range are not obtainable (ADR-0010, 2026-09-20), so the
  cut-off side of these thresholds is set from constructed frames. Flat-colour frames exercise
  the mask and the geometry, not real photo texture. `tests/test_preprocess.py` carries one
  case per input #54 named, and one per cut-off edge and corner, each placed so the crop would
  improve the aspect. The next person to move a threshold finds out what it costs.
- **The no-regression check is a test, and it has run.** Every guard added here can only
  decline more, and a declined crop costs a real upload ~10 points of accuracy.
  `test_every_real_holdout_photo_is_still_cropped_to_the_sheet` runs each photo through
  `crop_if_misframed` and asserts it comes back cropped to the detected sheet. All twelve do.
  It checks the crop rather than the scored read: if every photo still crops to the same box,
  the scored numbers are unchanged by construction, so it needs no checkpoint, no torch and no
  GPU. It skips with a named path where the photos are absent, fails if fewer than twelve are
  found, and `INFORM_REAL_HOLDOUT` points it at whichever checkout holds them.
- **The margins are narrow on both sides.** 0.49 is the worst of twelve photos of one sheet
  on one surface in one session, and a brighter desk reads higher, so a user photographing a
  sheet on a white table may lose the crop. That is the direction this ADR has always chosen
  to fail in. On the other side, a shadow that breaks more than about 45% of the cut-off edge
  would read under 0.55 and be cropped. Both are named numbers to watch.
