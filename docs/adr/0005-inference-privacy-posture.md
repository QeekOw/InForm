# ADR-0005: Cloud VLM for phase-1 POC; self-hosted Donut as the privacy endgame

**Status:** Accepted
**Date:** 2026-08-16
**Module:** 1 (OCR)
**Paper ref:** §3.2.1 (synthetic data for privacy), §3.4.1 (edge deployment), §3.4.3 (future PHI compliance)

## Context

Training-data privacy is solved by synthetic sheets (§3.2.1). **Inference** is different: a
real user uploads a real InBody sheet, which is health data. The phase-1 VLM baseline
(ADR-0002) can run either via a cloud API (OpenAI — best Structured Outputs support, fastest
to build) or self-hosted (Qwen2.5-VL — private, heavier GPU/setup).

The paper frames HIPAA/GDPR PHI handling as **future** work (§3.4.3) and touts on-device edge
processing for privacy (§3.4.1) — so a cloud API is in mild tension with its stated ethos,
but not with its stated *scope* (a datathon proof-of-concept).

## Decision

- **Phase-1 baseline runs on the cloud OpenAI VLM**, explicitly scoped as **POC only —
  synthetic or consented data, never real PHI.**
- The **permanent privacy answer is self-hosted Donut** (ADR-0002 phase 2), which is
  self-hosted by construction and aligns with §3.4.1's edge-deployment direction.
- Real-PHI compliance infrastructure remains future work, consistent with §3.4.3.

## Consequences

- Fastest path to an unblocked team, consistent with the paper's POC scope.
- A clear, documented data-handling boundary: no real patient data through the cloud engine.
- The final product's privacy posture (self-hosted Donut) is already on the roadmap, so the
  cloud dependency is a temporary scaffold, not a permanent commitment.
