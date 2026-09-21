# Module 4: Plan Synthesis

Module 4 assembles a readable `DailyPlan` from the deterministic `MasterPayload` produced by
Modules 1–3. The backend owns every actionable fact; an LLM may add only a bounded,
non-actionable coaching note. See
[ADR-0013](adr/0013-keep-actionable-plan-facts-deterministic.md).

## Flow

1. `synthesize_plan(master)` asks OpenAI Structured Outputs for a `CoachingDraft`.
2. The backend rejects blank, quantitative, prescriptive, nutrition, exercise, imbalance, or
   diagnostic content.
3. The accepted coaching note is prepended to the backend-rendered nutrition targets,
   exercises, and imbalance findings.
4. `validate_no_mutation(master, plan)` requires exact structured values and the exact
   deterministic narrative section.
5. Invalid output or an API failure is discarded immediately; `generate_fallback_plan(master)`
   returns the complete deterministic plan without an LLM retry.

`DailyPlan.narrative_source` records whether an accepted coaching note was generated or the
fallback was used. The public `POST /plan` response continues to return canonical `nutrition`
and `exercises` alongside the assembled narrative.

## Main files

- `src/inform/master.py`: `MasterPayload`, `CoachingDraft`, and `DailyPlan` contracts.
- `src/inform/synthesis/generate.py`: coaching generation, validation, and final assembly.
- `src/inform/synthesis/validate.py`: deterministic rendering, exact integrity checks, and
  fallback generation.
- `tests/test_synthesis.py`, `tests/test_validation.py`, and `tests/test_api_plan.py`: generated,
  invalid-output, integrity, fallback, and API behavior.
