# ADR-0009: Module 3 fallback when visceral_fat_level is absent

**Status:** Accepted
**Date:** 2026-08-22
**Module:** 3 (exercise recommender)
**Paper ref:** §3.1.3.2 (visceral-fat exercise rule)

## Context

[ADR-0004](0004-device-scope-optional-fields.md) made `visceral_fat_level: int | None`
optional on `InBodyPayload`: the InBody 270 never reports it, and it is a programmable
(sometimes-absent) output on the 570. It explicitly deferred one decision to Module 3's
owner: what the exercise recommender does when the field is `None`, since the paper's rule
("fat loss + high visceral fat → more HIIT", §3.1.3.2) has no value to key on in that case.

Per [ADR-0008](0008-ocr-failure-handling.md), a missing *optional* field is an expected
outcome, not a failure — so this is not a fail-closed scenario. The recommender must still
produce a complete, usable exercise plan.

## Decision

- When `visceral_fat_level is None`, Module 3 **skips the visceral-fat-driven HIIT-weighting
  rule entirely** and bases exercise selection on `fitness_goal` (and bilateral asymmetry,
  independently of visceral fat) alone.
- Module 3 **never imputes or guesses** a visceral-fat value to keep the rule active.
- This is not an error path: a `None` value produces a normal `ExercisePlan`, not a rejection
  or a flagged/degraded result. It applies identically whether the source is an InBody 270
  (always `None`) or a 570 with the field unprogrammed (`None`).
- The HIIT-weighting rule itself (what counts as "high" visceral fat, how much it shifts
  exercise selection) is out of scope for this ADR — that is Module 3's implementation detail
  once a value *is* present. This ADR only settles the absent-value branch.

## Consequences

- Module 3 gains one required branch: `if payload.visceral_fat_level is not None: apply
  HIIT-weighting modifier; else: skip it.`
- Every InBody 270 payload, and any 570 payload with the field unprogrammed, deterministically
  takes the skip branch — this must be covered by Module 3's test suite (an InBody 270 input
  must never error or produce an incomplete plan).
- Users on simpler devices (270) or with the 570's optional output unset receive a plan
  driven by their stated goal and detected asymmetries, without a fabricated visceral-fat
  signal influencing it.
