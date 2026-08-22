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
   validation check) and reject cleanly. The *mechanism* is engine-specific: the VLM has a
   direct signal (`is_inbody_sheet=false` → `NotAnInBodySheetError`); the fine-tuned Donut,
   having only ever seen InBody sheets in training, has no such signal, so a non-sheet surfaces
   as unparseable/invalid output → `MissingRequiredFieldsError`, or as parseable-but-incoherent
   output caught by the cross-check gate (§2) → the flag path. The *guarantee* is identical
   across engines — both fail closed and neither fabricates a number; only the error type
   differs. "Fail-closed applies to Donut exactly as to the VLM" (issue #8) is satisfied at the
   level of the guarantee, not the error taxonomy.
4. **Missing *optional* field is not a failure.** An absent `visceral_fat_level` on a 270 is
   expected `None` (ADR-0004), not an error — only *required* fields trigger the refuse path.

## Consequences

- The "anti-hallucination" claim is true at the OCR boundary, not just at Module 4.
- Symmetry with Module 4's drop-on-mutation → deterministic-fallback design.
- Requires a confidence signal from the engine and a clear re-upload UX (hand-off to the
  fullstack/UI owners).
- Pydantic validation + the cross-checks form the enforcement layer.

## Amendment (2026-08-23): partial extraction, not all-or-nothing

The original decision discarded the *whole* extraction whenever any single required field was
unreadable or a cross-check failed. On a real phone photo where one field is glare-washed, that
threw away every other correctly-read value — poor UX for no safety gain. `extract_inbody` now
returns an `InBodyExtraction { data, unread, flagged }`: the values that were read, the required
fields that were not (`unread`), and the fields a cross-check found suspect (`flagged`,
"verify"). The UI turns `unread`/`flagged` into a user-facing notice (out of Module 1's scope).

**The no-fabrication guarantee is unchanged** — unread fields carry no value; flagged fields are
real reads marked low-confidence; nothing is ever guessed. What changes:

1. **Unreadable required field → left `unread`, not a whole-sheet refuse.** Other fields are
   still returned.
2. **Cross-check breach → `flagged`, not a refuse.** A breach can't isolate the single misread,
   so every field feeding the check is flagged. `CrossCheckFailedError` is removed.
3. **Two hard-reject paths remain (still fail closed):** a non-InBody image
   (`NotAnInBodySheetError`), and the *floor case* where **nothing** readable came back
   (`MissingRequiredFieldsError`) — partial extraction only applies once some real data is read.
4. **Eval (ADR-0006) credits partial reads:** each field read *and* correct scores; `whole_sheet`
   requires all required fields read, all correct, and no flags. This raises per-field numbers
   vs the old all-or-nothing scoring, so pre-amendment figures are not directly comparable.

Design spec: `docs/superpowers/specs/2026-08-23-partial-inbody-extraction-design.md`.
