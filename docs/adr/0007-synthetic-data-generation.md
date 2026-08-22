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
