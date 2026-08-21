# ADR-0008: OCR failure handling — fail closed, never fabricate

**Status:** Accepted
**Date:** 2026-08-16
**Module:** 1 (OCR)
**Paper ref:** (silent — this ADR fills a gap); mirrors §3.3 Module 4 drop-on-mutation fallback

## Context

The paper does not address extraction failure, but on real phone photos it is inevitable:
blurred/glare-washed digits, or an uploaded image that is not an InBody sheet. For a system
whose thesis is "medically precise, no hallucination," silently guessing a value (e.g.
`lean_body_mass_kg`) would poison every downstream number and violate the premise. The failure
path is therefore load-bearing for the core claim.

## Decision

**Fail closed. Never fabricate a number to fill a gap.**

1. **Required field not read confidently → refuse.** Return a structured error naming the
   field(s) and request a clearer re-upload, rather than emit a low-confidence number.
2. **Cross-check gate.** If extracted `LBM` disagrees with `weight × (1 − PBF/100)` beyond
   tolerance, or printed `BMR` disagrees with the Katch–McArdle recompute, flag the sheet as a
   likely misread and block/queue it rather than pass it downstream (uses ADR-0003 checks).
3. **Reject non-InBody input.** Detect images that are not InBody sheets (low field-match / a
   validation check) and reject cleanly.
4. **Missing *optional* field is not a failure.** An absent `visceral_fat_level` on a 270 is
   expected `None` (ADR-0004), not an error — only *required* fields trigger the refuse path.

## Consequences

- The "anti-hallucination" claim is true at the OCR boundary, not just at Module 4.
- Symmetry with Module 4's drop-on-mutation → deterministic-fallback design.
- Requires a confidence signal from the engine and a clear re-upload UX (hand-off to the
  fullstack/UI owners).
- Pydantic validation + the cross-checks form the enforcement layer.
