# ADR-0003: Extract Lean Body Mass directly, with a weight×PBF cross-check

**Status:** Accepted
**Date:** 2026-08-16
**Module:** 1 (OCR) → contract for Module 2 (nutrition)
**Paper ref:** §3.1.1 (OCR output list), §3.1.2 / §3.3 (Katch–McArdle uses LBM)

## Context

Module 2's Katch–McArdle formula — `BMR = 370 + 21.6 × LBM_kg` — is built on **Lean Body
Mass (LBM)**, described in §3.1.2/§3.3 as the authoritative input. But the paper's OCR output
list in §3.1.1 (BMR, PBF, SMM, Visceral Fat, Segmental Lean) **never includes LBM or plain
weight**. The pipeline's central number therefore has no stated source — a gap in the paper.

Both InBody 270 and 570 print **Lean Body Mass** and **Weight** as their own line items
(verified — see ADR-0004), so the value is available to read directly.

## Decision

- **Extract `weight_kg` and `lean_body_mass_kg` directly off the sheet** and treat the printed
  `lean_body_mass_kg` as **authoritative** (the device measures it more accurately than a
  weight×PBF estimate).
- **Compute `weight_kg × (1 − PBF/100)` as a cross-check.** If the printed LBM and the derived
  value disagree beyond tolerance, flag the sheet as a likely OCR misread (see ADR-0008).
- `InBodyPayload` therefore carries `weight_kg` and `lean_body_mass_kg` in addition to the
  paper's listed fields. This **extends the paper** to close the LBM-source gap.

## Consequences

- Module 2 has an unambiguous, authoritative LBM input.
- The redundancy the sheet already provides (weight, PBF, LBM) becomes free misread detection.
- `InBodyPayload` field set is a superset of the paper's §3.1.1 list — documented divergence.
- Do **not** conflate LBM with SMM; they are different quantities (see `CONTEXT.md`).
