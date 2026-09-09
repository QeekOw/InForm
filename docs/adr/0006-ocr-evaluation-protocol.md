# ADR-0006: OCR evaluation protocol — exact per-field + whole-sheet accuracy

**Status:** Accepted
**Date:** 2026-08-16
**Module:** 1 (OCR)
**Paper ref:** §3.3 ("high fidelity" — no metric or protocol defined)

## Context

The paper claims Donut extracts "with high fidelity" but defines **no accuracy target and no
evaluation protocol**. For a system whose thesis is deterministic, anti-hallucination medical
precision, an unmeasured precision claim is the largest gap. A protocol is needed to define
"done" for *both* engines (VLM and Donut).

A single wrong digit in a field like `lean_body_mass_kg` corrupts the entire downstream
pipeline, so text-similarity metrics (BLEU, edit distance) that give partial credit for
near-misses are inappropriate.

## Decision

**Metrics** (numeric, exact within tolerance — default ±0.1 unit per field; segmental limbs
also carry a 1% relative bound, see the 2026-09-09 amendment):

- **Per-field exact-match rate** — identifies which fields fail most.
- **Whole-sheet accuracy** — % of sheets with *every* required field correct. This is the
  headline number, because one bad field breaks the plan.
- **Critical-field cut** — separate reporting for the fields the pipeline hinges on:
  `lean_body_mass_kg` and the segmental lean values.

**Ground truth — dual:**

- **Synthetic set** — values are known by construction (ADR-0007); thousands of samples at
  zero labeling cost.
- **Small real-photo hold-out** — ~20–30 hand-labeled real InBody photos as the honest test
  of the synthetic→real domain gap. Report the synthetic-vs-real accuracy gap explicitly.

**Live signal:** the ADR-0003 (weight×PBF vs LBM) and Katch–McArdle-recompute cross-checks
flag likely misreads even on unlabeled real sheets.

**Provisional target:** whole-sheet ≥ 95% on synthetic; real-photo accuracy is *reported
honestly*, not targeted.

## Consequences

- Clear pass/fail definition for shipping either engine.
- The synthetic ground-truth generator (ADR-0007) must emit exact values alongside each image.
- Becomes the `tests/` fixture strategy for Module 1.
- Requires collecting a small set of real, consented InBody photos for the hold-out.

## Amendment (2026-09-09): segmental limbs need a relative bound too

The original decision set one tolerance for every field, exact within +/-0.1 unit. That is
right for the scalars and wrong for the limbs, because the segmental values on a single
sheet span an order of magnitude: +/-0.1 kg is 0.1% of an 85 kg weight and 2.9% of a
3.5 kg arm.

2.9% is not a small error at that magnitude. Module 3 treats a bilateral asymmetry above
5% as a finding worth acting on (CONTEXT.md), and computes it from values around 3.5 kg.
Two arm reads that each pass a 2.9% check can therefore differ by enough to invent an
asymmetry that is not on the printout. This is not hypothetical. On sheet_02 of the real
hold-out, printed arms of 3.53 and 3.50 kg, 0.85% apart, were read as 3.5 and 3.7, which
computes to 5.41% and clears the trigger. That read passed the accuracy protocol and still
produced a plan telling the subject to correct an imbalance they do not have.

**A segmental limb field now counts as correct only within both bounds: +/-0.1 unit
absolute AND 1% relative.** Whichever is tighter at that magnitude binds, so the relative
bound governs an arm (+/-0.035 kg) and the absolute one governs a trunk (+/-0.1 kg is 0.35%
of 28 kg). Scalar fields are unchanged.

The 1% figure comes from the threshold it protects: at 1% per limb the induced error in a
computed asymmetry stays near 2 points, inside the 5-point trigger with margin. It was
chosen against that threshold, not fitted to a score.

**Considered and rejected:**

- *Exact equality on limbs.* The printout carries two decimals, so a correct read should
  reproduce them, and this is defensible. Rejected because it makes every accuracy figure
  hostage to a rounding difference and carries no argument about how much error is
  tolerable.
- *A relative bound alone.* Looser than the status quo on the trunk (1% of 28.2 kg is
  +/-0.28), which would weaken scoring on a field that currently reads correctly.

**What the real hold-out can and cannot report.** The hand-labelled set carries the
critical-field cut (`lean_body_mass_kg` plus the five limbs) and per-field accuracy, but
**not whole-sheet accuracy**, this ADR's stated headline number. Whole-sheet is defined as
"every required field correct", and `source_device` is unlabelled on every sheet in the
set: nobody read the device off the page, and inventing the label would both fabricate
ground truth and move the per-field denominator. A whole-sheet figure computed over only
the labelled fields would carry the same name as the synthetic one with a different
denominator, and would invite exactly the comparison this ADR exists to keep honest. The
outcome split (usable / flagged / unread / refused) covers all sheets and needs no labels,
so it carries the whole-set signal instead.

**Consequences.** Implemented as `inform.evaluate.segmental_matches` and used by both
ground-truth sources, `evaluate()` for the synthetic set and `inform.holdout.score()` for
the real hand-labelled hold-out, so "correct" still means one thing across the
synthetic-to-real gap this ADR exists to measure. **Pre-amendment segmental figures are not
directly comparable**: `donut-both-v3` scores 23/30 on the real hold-out's segmental lean
under the amended rule, against 25/30 under +/-0.1 alone.
