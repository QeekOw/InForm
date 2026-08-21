# ADR-0002: VLM baseline first, then fine-tuned Donut

**Status:** Accepted
**Date:** 2026-08-16
**Module:** 1 (OCR / visual extraction)
**Paper ref:** §3.1.1, §3.3 (Donut, fine-tuned on ~5,000 synthetic sheets)

## Context

Module 1 must turn an InBody sheet image into a structured `InBodyPayload`. The concept
paper commits to a **fine-tuned Donut** (Document Understanding Transformer), trained with
Cross-Entropy loss on next-token JSON prediction over ~5,000 synthetic sheets. This is the
paper's novel contribution.

Research (`docs/research/2026-08-16-ocr-inbody-extraction.md`) recommends a schema-constrained
**vision-language model (VLM)** in zero/few-shot for v1: no InBody Donut checkpoint exists,
real training data is scarce, and fine-tuning needs a synthetic dataset + GPU before anything
works. Meanwhile the whole downstream team is blocked until `extract_inbody` returns valid
data.

These pull in opposite directions: Donut is the paper's deliverable; a VLM is the pragmatic
unblock.

## Decision

Build **both, in sequence**:

1. **Phase 1 — VLM baseline.** Implement `extract_inbody` with a VLM + OpenAI Structured
   Outputs first. Unblocks the team in days and serves as the **evaluation oracle** for
   ground-truth comparison.
2. **Phase 2 — Donut.** Build the synthetic dataset (ADR-0007) and fine-tune Donut. Swap it
   into the same `extract_inbody` seam and measure it against the VLM baseline.

The VLM and Donut are **swappable engines behind one seam**, never layered and never run
together in production. Their only runtime relationship is at evaluation time.

## Consequences

- Downstream modules (nutrition, recommender) are unblocked immediately by the VLM baseline.
- The paper's contribution (fine-tuned Donut) is preserved and produced.
- The VLM provides a benchmark to quantify Donut's accuracy (ties into ADR-0006).
- Two engines to maintain during overlap; mitigated by a shared seam and shared schema.
- Cloud VLM has a privacy caveat at inference — see ADR-0005.
