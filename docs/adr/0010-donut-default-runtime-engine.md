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

## Amendment (2026-09-12) — v3 stays the default; v4 and v5 were measured and both lost

The decision above names `models/donut-both-v3` as the default checkpoint and calls
accuracy "a follow-up gate, not a blocker". That gate has now been run twice, against
the hand-labelled real photos rather than synthetic hold-out (ADR-0006), and it changes
nothing about the default — which is worth recording, because two retrains produced no
promotion and a reader would otherwise assume the newest checkpoint ships.

v3 leads or ties every field cut: core 33/36 against v4-e3750's 30 and
v5-e3750's 28, segmental lean 23/30 against 20 and 15, critical 26/36 against
v4's 26 and v5's 21. The full table, and the command that prints it, are in
`docs/training.md` §4.

**`INFORM_DONUT_CKPT` continues to default to `models/donut-both-v3`.** v4 regressed
`percent_body_fat` from 6/6 to 3/6 (#48, closed 2026-09-12) and v5 took it to 1/6 while
also losing eight field observations elsewhere. v5's `unread = 0` is the part to notice:
it declines nothing, so its errors arrive as confident values rather than as gaps a
person is asked to fill.

Two consequences that outlive this comparison:

- **A retrain is promoted on the real hold-out or not at all.** Both v4 and v5 were built
  to fix a defect visible in the synthetic geometry, and both did fix it there. Neither
  improved the engine. `docs/training.md` §4 is the procedure.
- **The comparison is under-powered and known to be.** 66 field observations across 6
  labelled sheets, with a silent-error denominator between one and three. It can separate
  v3 from v5; it cannot resolve a small improvement. #24 is the constraint on every
  number quoted here, and reading these results as precise would be a mistake.
