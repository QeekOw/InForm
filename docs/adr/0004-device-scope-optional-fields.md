# ADR-0004: Support InBody 270 + 570; make device-specific fields optional

**Status:** Accepted
**Date:** 2026-08-16
**Module:** 1 (OCR) → contract for Module 3 (recommender)
**Paper ref:** §3.3 (2,500× InBody 270 + 2,500× 570), §3.1.3.2 (visceral-fat exercise rule)

## Context

The paper trains on two device layouts, 2,500 sheets each: **InBody 270** and **InBody 570**.
It implicitly assumes both produce the same fields. They do not.

Verified against InBody's own material
([270S interpretation](https://inbodycanada.ca/inbody-270s-result-sheet-interpretation/),
[570 result sheets](https://shop.inbodyusa.com/products/inbody570-result-sheets)):

| Field | InBody 270 | InBody 570 |
| --- | --- | --- |
| Weight, LBM, PBF, SMM, BMR | ✅ | ✅ (BMR programmable) |
| Segmental Lean (4 limbs + trunk) | ✅ | ✅ |
| **Visceral Fat Level** | ❌ not reported | ✅ (programmable, can be absent) |

The **InBody 270 does not print Visceral Fat Level at all**, and on the 570 it is a
*programmable* output that may be absent. Yet §3.1.3.2's rule ("fat loss + high visceral fat
→ more HIIT") depends on it — so 2,500 of the paper's training sheets cannot produce a field
the pipeline keys on. Treating `visceral_fat_level` as always-present would force the
extractor to hallucinate, violating the anti-hallucination thesis.

## Decision

- **Keep both devices in scope** (match the paper's contribution).
- `visceral_fat_level: int | None` — **optional**. A missing value on a 270 is expected, not a
  failure (interacts with ADR-0008).
- All other InBody fields are **required** (both devices print them).
- Add `source_device: Literal["inbody_270", "inbody_570"]` to `InBodyPayload` so downstream
  knows the provenance.
- **Module 3 must define a fallback** when `visceral_fat_level is None` — e.g. skip the
  visceral-fat rule and rely on `fitness_goal` alone. (Handed to the recommender owner.)

## Consequences

- Schema honestly represents device capability; no fabricated visceral-fat values.
- Module 3 gains a required branch for the no-visceral-fat case.
- Synthetic generation (ADR-0007) must render 270 sheets *without* a visceral-fat field.

## Correction (issue #13, 2026-08-22) — the InBody 270 *does* print Visceral Fat Level

The Context table above (sourced from InBody-Canada 270**S** marketing material) claims the 270
does not report Visceral Fat Level. **Real hardware disproves this.** Two real InBody 270 result
sheets — the hand-labeled phone hold-out (`D:\inform\data\real_holdout`, Visceral Fat Level 7) and
a clean official 270 sample (Level 11), both tagged `[InBody270]` — print it plainly. Empirical
sheets beat the doc citation.

Revised decision:

- **The 270 prints Visceral Fat Level; extract it.** `visceral_fat_level` is now populated for
  **both** devices (synthetic 270 sheets render it — ADR-0007 amendment).
- `visceral_fat_level: int | None` **stays optional** — some 270 configs may still omit it, and
  it remains programmable/absent on the 570 — so the anti-hallucination guarantee (ADR-0008 §4:
  a missing *optional* field is expected `None`, not a failure) is unchanged.
- **Module 3 gains 270 users for the visceral-fat HIIT rule** (§3.1.3.2), which this ADR had
  previously denied them. The `None` fallback branch is still required for the absent case.

Net: the field is now *available on both devices* rather than *270-never*, but its **optionality
is preserved** — no fabricated value is ever emitted.
