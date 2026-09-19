# Keep Actionable Plan Facts Deterministic

**Status:** Accepted
**Date:** 2026-09-19

Module 4 may use an LLM for a bounded, non-actionable Coaching note, but every nutrition target, prescribed exercise, and imbalance finding in the final Daily plan is rendered directly from `MasterPayload`. Correct structured echoes do not prove that free-form prose is faithful, and prose heuristics cannot close that gap, so the LLM supplies voice while deterministic code owns the prescription.

The final integrity check requires exact agreement with `MasterPayload`; numeric mutation tolerances are unnecessary because the backend owns formatting. Invalid coaching output or an LLM failure is discarded immediately in favor of the deterministic fallback, with no retry, and the plan records whether its narrative source was generated or fallback.
