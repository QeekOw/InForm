# ADR-0011: Crop the sheet out of the photo before Donut sees it

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
- **`numpy` becomes a base dependency.** `inform.preprocess` is on the runtime path and
  percentiles over a pixel mask are not something Pillow does well.
- **The synthetic cost is real and now measured**, so a future decision to crop
  unconditionally has a number attached rather than an intuition.
