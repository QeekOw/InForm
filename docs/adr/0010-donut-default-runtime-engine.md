# ADR-0010: Donut is the default runtime engine; VLM is the eval oracle

**Status:** Accepted (supersedes the "VLM is the default baseline" framing of ADR-0002)
**Date:** 2026-08-26
**Module:** 1 (OCR)

## Context

ADR-0002 built two swappable engines behind the `extract_inbody` seam and made the
cloud VLM the default while the fine-tuned Donut was still being produced. Donut is now
fine-tuned (trained on Kaggle, output folder `donut-both-v3`) and is the paper's actual
contribution and the privacy endgame (ADR-0005). The integration gap was that nothing
wired `donut.load_engine` into the runtime; `pipeline.py`/`extract.py` only reached the
VLM.

## Decision

- **Donut is the default runtime engine.** `extract_inbody(image_path, engine=None)` and
  the pipeline resolve `engine=None` to `default_engine()`, which builds Donut from the
  checkpoint at `INFORM_DONUT_CKPT` (default `models/donut-both-v3`, a local dir; hub-id support is a
  future option). The 809 MB weights stay out of git (`models/` is gitignored).
- **The VLM is demoted to the evaluation oracle only** (ADR-0002's "never run together in
  production" is preserved): it is never a runtime fallback, only an explicitly-chosen
  engine passed into `evaluate.py` or a test.
- **Missing checkpoint or missing training extra fails loudly** (`DonutCheckpointError`),
  never silently falls back to the cloud VLM.

## Considered Options

- **Keep VLM default, Donut opt-in**: safer given Donut is unvalidated on real photos, but
  it leaves the project's core contribution off the runtime path. Rejected: the whole point
  of the project is the self-hosted Donut OCR.
- **Donut primary with VLM runtime fallback**: rejected: it would run both engines in
  production (violates ADR-0002) and is a privacy footgun (see below).

## Consequences

- **No silent cloud fallback.** A user who believes they are on self-hosted Donut would, on
  a missing checkpoint, have real health data shipped to the cloud VLM, which ADR-0005 says
  must never see real PHI. Failing loudly is the only honest behavior; the error tells the
  caller to download the checkpoint or install the `training` extra.
- **Accuracy is a follow-up gate, not a blocker.** Donut was fine-tuned on synthetic sheets
  and is unmeasured on real photos. Before trusting it on real uploads, run `evaluate.py`
  (Donut vs the VLM oracle) once the checkpoint is on disk.
- **Tests do not need the 809 MB blob.** Engine selection is verified with a stub engine and
  a fail-loud path pointed at a nonexistent dir; a real-checkpoint test skips when absent.
