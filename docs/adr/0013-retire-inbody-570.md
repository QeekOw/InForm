# ADR-0013: Retire InBody 570; support InBody 270 only

**Status:** Accepted
**Date:** 2026-09-18
**Module:** 1 (OCR)
**Supersedes:** ADR-0004's multi-device scope and ADR-0007's two-device generation scope

## Context

The project has real InBody 270 photos for development and confirmation, but no real InBody 570
photos. Continuing to generate, train on, evaluate, or claim runtime support for the 570 would
make its quality unmeasurable and dilute the controlled v8 experiment.

## Decision

- InBody 270 is the sole supported Module 1 layout.
- Future generation, training, development scoring, and independent confirmation use only the
  270.
- Runtime refuses an image that is not established as a supported 270 layout, using the existing
  fail-closed `InBodyExtraction` outcome; the `extract_inbody(image_path) -> InBodyExtraction`
  seam remains unchanged.
- Remove active 570 generation paths, tests, documentation, and source-device validation as part
  of implementation.
- Retain existing 570 datasets and checkpoints on `D:` as archives. They are not active training
  or evaluation inputs and are not deleted by this decision.

## Consequences

The supported-device claim now matches the available real-photo evidence. Reintroducing 570
requires new real-photo evidence and a fresh ADR; it is not a configuration switch.
