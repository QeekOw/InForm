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

## Amendment (2026-09-15): the 270 prints limbs to two decimals

A real 270 prints arm and leg lean mass to two decimals. Every synthetic sheet printed one, and
every checkpoint trained on them sometimes returns a real arm with its last digit cut off (#59,
ADR-0008's 2026-09-13 amendment). From this commit the 270 generates, prints and labels its four
limbs to two decimals. Trunk stays at one, as on a real sheet. The 570 keeps one decimal: the
hold-out has no real 570, so nothing says what it prints.

**The label spells a limb the way the sheet prints it.** `model_dump_json` writes an arm printed
`3.40` as `3.4`, and a three-character arm target is the habit being removed. So
`synthetic.label_json` writes the four limbs to the device's decimals, and `generate_dataset`
writes that file. JSON parses `3.40` as `3.4`, so the payload, the scorer and everything else that
reads a label are unchanged. It lives in the generator module so `generator_fingerprint()` covers
it.

What moved, checked against the previous commit over seeds 0-299:

- **570:** payload, filled template and label identical on 300/300.
- **270:** every scalar identical on 300/300, and each limb within 0.05 of its old value. Trunk
  still absorbs the rounding remainder and moved by more than 0.1 on 21/300. At one decimal it
  cannot take up a two-decimal limb total, so the segments now sum to LBM within 0.05 kg rather
  than exactly (171/300 are off by a few hundredths). A real 270's segments do not sum to LBM at
  all, so this loosens a synthetic nicety, not a property of real sheets.

Two things this knowingly leaves open.

**Legs of 10 kg or more.** 141 of 300 generated 270 sheets carry one, printed `##.##`. Every real
leg in the hold-out is under 10 kg, so whether a real 270 prints `10.46` or `10.5` is unobserved.
Two decimals throughout is the simpler rule. If a real sheet shows otherwise, `_LIMB_DECIMALS` is
the line to change.

**ADR-0008's arm check now fires on correct synthetic reads.** An arm ending in zero parses back
with one decimal, and beside a two-decimal leg the check flags it. Up to 35 of 300 generated 270
sheets have such an arm. Synthetic 270 whole-sheet accuracy on sets from this commit loses that
much for a reason unrelated to the model, and is not comparable with earlier sets.

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

## Amendment (2026-09-18) — quoted PBF target and paired promotion gate

The v7 limb-label correction fixed the arm reads but caused a real-photo PBF cross-field
attribution regression, including the format-shape-bleed subtype. The rendered PBF field itself
remained a numeric value with one decimal place. The next retrain therefore changes only its
training-target representation, not its rendered spelling, physiology, layout, or augmentation.

### Decision

- Render PBF as the existing numeric one-decimal value, but serialize its JSON target as a quoted
  one-decimal string. The parser must accept that target and retain PBF's numeric runtime
  interface.
- Keep the v7 limb representations unchanged. No additional formatting or augmentation change is
  part of this experiment.
- Per [ADR-0013](0013-retire-inbody-570.md), v8 generation, training, and evaluation use only
  InBody 270 sheets. Generate 5,000 such sheets to preserve the prior training-set size.
- Score every planned v8 checkpoint against the fixed 12-sheet development regression set. A
  candidate requires PBF at least 10/12, both arms at 12/12, and a flagged/unread split no worse
  than v5; record the v5 split before comparing it.
- Freeze the candidate checkpoint and training recipe before scoring it once against an independent
  confirmation set of at least five newly collected real InBody 270 sheets. Until that set passes,
  v5 remains the default.

### Consequences

The experiment is falsifiable: a failed gate ends this formatting line of investigation rather
than adding another synthetic-data variation. Tests cover rendered one-decimal PBF spelling and
quoted-target parser compatibility without using real hold-out data.
