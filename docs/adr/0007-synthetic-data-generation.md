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
