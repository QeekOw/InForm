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

**Metrics** (numeric, exact within tolerance — default ±0.1 unit per field):

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
