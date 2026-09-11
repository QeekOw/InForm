# ADR-0007: Synthetic InBody sheet generation — HTML/CSS templates with a consistent physiological model

**Status:** Accepted
**Date:** 2026-08-16
**Module:** 1 (OCR) — training + evaluation data
**Paper ref:** §3.2.1, §3.3 (~5,000 sheets, 2,500× 270 + 2,500× 570, augmented)

## Context

Fine-tuning Donut (ADR-0002) requires a labeled image→JSON dataset that does not exist; real
InBody sheets are scarce and privacy-sensitive. The paper specifies a Python script that
generates ~5,000 augmented synthetic sheets but leaves the rendering method and — critically —
the *value generation* unspecified.

Two subtleties the paper misses:
1. **Layout fidelity** drives the synthetic→real domain gap (ADR-0006). Low-variety templates
   overfit.
2. **Value consistency** — if fields are randomized independently, the data contains
   physically impossible sheets (SMM > LBM, BMR inconsistent with LBM), which would make the
   ADR-0003/0006 cross-checks meaningless because the training data itself violates them.

## Decision

- **Rendering: HTML/CSS templates**, one per device (270, 570), rendered to PNG. Pixel-accurate,
  easy layout jitter (fonts/spacing) for generalization, and the ground-truth JSON is emitted
  from the same values that fill the template.
- **Values from a consistent physiological model**, not independent randomization:
  draw `weight`, `PBF` in realistic ranges → derive `LBM = weight × (1 − PBF/100)` →
  `SMM ≈` realistic fraction of LBM → `BMR = 370 + 21.6 × LBM` → segmental limbs sum coherently,
  with a **controlled, deliberately seeded amount of L/R asymmetry** (so Module 3's >5% rule
  has positive cases).
- **270 sheets omit Visceral Fat Level** (ADR-0004); 570 sheets include it.
- **Augmentation pass** mimicking phone capture: Gaussian blur, rotation, perspective warp,
  lighting gradients, JPEG noise (per §3.2.1/§3.3).
- Emit exact ground-truth JSON per image for ADR-0006 evaluation.

## Consequences

- Training data respects the same physical invariants the runtime cross-checks enforce.
- Sheets with seeded asymmetry **double as test fixtures for Module 3** (one dataset, two
  modules served).
- Requires accurate 270/570 layout recreation from public sample sheets.
- Augmentation strength is a tunable that trades synthetic accuracy for real-world robustness
  (measured via ADR-0006's real hold-out).

## Amendment (issue #13, 2026-08-22) — realistic full-clone 270

The first 270 template was a *minimal* sheet (the ~12 target fields as a clean list). It scored
56% on held-out synthetic but **0% on a real InBody 270 photo** (a safe fail-closed refusal, no
fabrication). Root cause: visual domain gap — a real 270 is a dense two-column sheet, so the
minimal look is out-of-distribution. The 270 template is therefore overhauled (570 deferred):

- **Full structural clone** of a real 270: header/logo/ID row, Body Composition Analysis,
  Muscle-Fat + Obesity bar charts, Segmental Lean **and** Fat figures, InBody Score, Weight
  Control, Obesity Evaluation, Waist-Hip, Visceral Fat, Research Parameters, Calorie Expenditure
  and Impedance tables, and a Body Composition History strip — the ~12 target fields kept in
  their **real** positions amid this clutter.
- **LBM renders as "Fat Free Mass"** in Research Parameters — its real position on a 270 — not
  an invented "Lean Body Mass" row (ADR-0003; the FFM↔LBM equivalence is documented in CONTEXT.md).
- **Distractor fields derive coherently** from the ground truth (`Body Fat Mass = weight − LBM`,
  `TBW ≈ 0.73·LBM`, `Protein ≈ 0.198·LBM`, `Minerals ≈ 0.0727·LBM`, `BMI` from a generated
  ungraded height, history = target ± drift), so the sheet cross-adds like a real one and stays
  human-verifiable. Peripheral tables (Calorie Expenditure, Impedance) are static clutter.
- **270 now renders a Visceral Fat Level** (supersedes the "270 omits VF" bullet above — see the
  ADR-0004 correction). `visceral_fat_level` is populated for both devices; the schema keeps it
  optional for real-world absence.
- **Augmentation strengthened toward the real photo (Q6):** grayscale/B&W prints, a darker desk
  background, glare, and stronger rotation/perspective, with ~30% of sheets kept "easy" so the
  held-out synthetic number stays interpretable.

Ground-truth invariants (LBM = weight·(1−PBF/100), Katch-McArdle BMR, segments sum, seeded
asymmetry) are unchanged — only the visual surround and the coherent distractors are new. The
`InBodyPayload` contract is untouched.

## Amendment (2026-09-11) — the 270 fat-figure fix also changed the 570

Found while preparing the v5 regeneration, by byte-comparing freshly rendered 570s against
`synth_v4_both` on disk. **They do not match.** The fix commit says a sheet stays
"byte-identical for a given (device, seed)"; that is true of the payloads, which were what it
verified, and false of the 570 images.

`_derive_render_values` is shared by both templates. Before the fix, `fat_la` and `fat_ra` were
both `body_fat_mass_kg * 0.04` — identical for left and right on every sheet — and the fix
skews them inversely against the seeded lean asymmetry so the arm carrying more lean carries
proportionally less fat. The 570 template renders `$fat_la` and `$fat_ra` in its Segmental Fat
bar rows, so its printed values moved too. Measured over 600 payloads, **23% of 570 sheets
now render differently**; the rest are sheets with no seeded asymmetry, where left and right
still coincide. The change is confined to those five values. Bars are unaffected (they use
fixed fractions), and `$fat_*_pct` / `$fat_*_rate` are read by the 270 template only.

**This is an improvement to the 570, not a regression.** "Left always equals right" is a
training-only cue of the same family as the missing third line on the 270: no real sheet prints
identical left and right segmental fat. It was not intended, recorded or measured, which is the
part worth writing down.

Two consequences.

**The 570 half of `synth_v4_both` is not reproducible from this commit onward**, so it cannot be
copied forward into a new set to save render time. A regeneration is 5,000 sheets, not 2,500.
The manifest fingerprint in `inform.training.dataset` is what surfaced this, on its first real
use.

**A v5 retrain is not single-variable per device, and is single-variable per hypothesis.** Both
halves of the change come from one commit and push the same way: remove a cue in the Segmental
Fat panel that exists in training and not at inference. That is one hypothesis, and it is the
level at which the result has to be attributable. Reverting the 570 side effect to keep the v4
bytes would mean deliberately keeping the worse sheet, so it is not worth doing.

Issue #50's 570 half stays open. It is about the panel being a structural clone of Segmental
Lean, which this does not touch.

## Amendment (2026-09-10) — the geometry correction is kept; its stated rationale is not

The 2026-09-08 diagnosis held that the synthetic sheets were the **wrong shape**: they rendered
near-square (aspect ~0.949) and narrow (941–1251 px), so they were *upscaled* onto Donut's
2560x1920 canvas while a real phone photo is *downscaled* onto it. The model therefore learned
soft interpolated text and met sharp text at inference. The templates were corrected to A4
(0.702 / 0.701 against 0.707), the dataset regenerated at 2352+ px as JPEG, and the model
retrained from `donut-base`.

**The retrain did not close the gap.** Best v4 checkpoint scores 30/36 core fields against
`donut-both-v3`'s 33/36 on the real hold-out, level on the critical cut. `donut-both-v3` remains
the shipped model. Full numbers in `docs/ocr-eval-results.md`.

### What this does and does not establish

**The geometry correction stands.** A synthetic InBody sheet should be A4-shaped because a real
one is; that is right independently of what it does for accuracy, and reverting it would
reintroduce a known-false property. v4 also emits well-formed JSON *more* often than v3
(8/12 vs 6/12 on real photos), so the shape change was not simply harmful.

**The rationale attached to it is not supported.** Aspect ratio and pixel scale were advanced as
the explanation for the synthetic-to-real gap. Corrected, the gap did not close. Aspect alone
cannot carry the explanation in either direction: v3 at 0.949 is further from a real photo
(~0.563) than v4 at 0.702, and scores better.

**The test was compromised, so this is not a refutation.** The same regeneration widened the
Segmental Lean/Fat panel gutter on a **guess** rather than a measurement (issue #46), and the
sheet_05 panel crossing that the guess targeted survived it (`right_arm_kg`, 1/6 to 2/6). Two
changes shipped together, one of them unmeasured, and the pre-registered indicator did not move.
The honest reading is that **guessed geometry cannot test a geometry hypothesis.**

The same regeneration also regressed `percent_body_fat` from 6/6 to 3/6 (issue #48), which is
unexplained and further weakens any single-cause account of v4's behaviour.

### Consequence

Measuring the #46 gutters off a real printout is now a **precondition for any further retrain**,
not parallel work. A retrain on the current templates would be as uninterpretable as this one:
its negative result would not distinguish "geometry is the wrong explanation" from "the guessed
gutter is wrong".

Ground-truth invariants and the `InBodyPayload` contract remain untouched, as in every amendment
above.

