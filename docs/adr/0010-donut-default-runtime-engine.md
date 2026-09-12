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

## Amendment (2026-09-12) — v3 stays the default, on a narrower margin than it first looked

The decision above names `models/donut-both-v3` as the default checkpoint and calls
accuracy "a follow-up gate, not a blocker". That gate has now been run against the
hand-labelled real photos rather than synthetic hold-out (ADR-0006), for both retrains
since v3, and the default does not change. The reasoning is worth recording, because the
obvious reading of the numbers is wrong.

Scored on the photos as they arrive, v3 leads or ties every field cut and both retrains
look like regressions. Scored on the same photos cropped to the sheet (#53), v5-e3750 has
the best segmental lean (28/30 against v3's 27/30) and the best critical-field score
(34/36 against 33/36) of any engine, and its `segmental_lean.right_arm_kg` goes from 1/6
to 5/6. The 270 Segmental Fat fix that v5 was built for did work; the framing mismatch
was costing more than the fix was buying, so the uncropped hold-out scored it as a
regression. `docs/training.md` §4 carries both tables.

**`INFORM_DONUT_CKPT` continues to default to `models/donut-both-v3`**, because it is the
only engine that reads every core field, and its five-observation win on
`percent_body_fat` (6/6 against v5's 1/6) outweighs v5's two-observation lead elsewhere.
That margin rests on one field, and that field is #52.

Three consequences that outlive this comparison:

- **A retrain is promoted on the real hold-out, and the hold-out has to be measuring the
  right thing.** This one was scoring an input-framing gap and attributing it to the
  training data, which cost two retrains and an issue's worth of misattribution.
- **An engine ranking is only as good as the preprocessing both sides share.** Cropping
  did not change any checkpoint; it changed which one wins.
- **The comparison is under-powered and known to be.** 66 field observations across 6
  labelled sheets, with a silent-error denominator between one and three. It separates v3
  from v4 comfortably; it cannot settle v3 against v5 at a one-field margin. #24 is the
  constraint on every number quoted here.
