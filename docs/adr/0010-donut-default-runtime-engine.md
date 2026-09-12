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

> **Superseded the same day** by the amendment at the end of this file, once the hold-out
> reached 12 of 12 labelled sheets and every cut reversed. Kept because how it went wrong
> is the point.

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

## Amendment (2026-09-12, later) — v5 becomes the default; the amendment above was decided at n=6

**This supersedes the amendment immediately above, which is left in place deliberately.** It
concluded "v3 stays the default" from a hold-out where 6 of 12 sheets were labelled. The
remaining six were hand-labelled the same day, and at n=12 every engine cut reverses. The
earlier amendment was not reasoned badly; it was reasoned on half the evidence, and #24 had
been saying so for weeks.

All three checkpoints scored live through the same engine, so all three get ADR-0011's crop:

| n=12, 132 labelled field observations | v3 | v4-e3750 | v5-e3750 |
|---|---|---|---|
| core fields | 61/72 | 56/72 | **63/72** |
| segmental lean | 31/60 | 42/60 | **52/60** |
| critical (LBM + limbs) | 43/72 | 53/72 | **64/72** |
| silent errors, sheets | 4/7 57.1% | 2/3 66.7% | **1/5 20.0%** |
| silent errors, fields | 4/77 5.2% | 3/33 9.1% | **1/55 1.8%** |
| unverified / flagged / unread | 7 / 0 / 5 | 3 / 8 / 1 | 5 / 6 / 1 |

At n=6 v3 led core fields 36/36 to 31/36 and the two engines were within a field of each other
elsewhere. At n=12 v5 leads every cut, and on segmental lean and critical fields it is not close:
52/60 against 31/60, and 64/72 against 43/72. The six sheets that happened to be labelled first
were the ones that flattered v3.

### Decision

**`INFORM_DONUT_CKPT` now defaults to `models/donut-both-v5`.**

The safety argument is the one CONTEXT.md asks for, and it points the same way as the accuracy:

- v3 leaves **5 of 12 sheets partly unread and flags nothing at all** — 0 flagged, 7 unverified,
  and 4 of those 7 carry a wrong value. Its errors arrive with no signal attached.
- v5 reads all but one sheet, flags 6, and **1 of its 5 unverified reads carries a wrong value**.
  Per field, 1.8% against v3's 5.2%.

v5 is both more accurate and more honest about what it got wrong. A wrong value that trips a
cross-check costs someone thirty seconds; a wrong value in an `unverified` read is the failure
this project is organised around avoiding.

### The one regression, stated plainly

`percent_body_fat` is **6/12 under v5 against v3's 12/12**. It is the only field where v3 wins,
and it is the reason v5's core-field lead is 2 observations rather than 10.

It does not outweigh the rest. PBF feeds the LBM cross-check (`lbm ≈ weight × (1 - pbf/100)`), so
a misread PBF is largely *why* v5 flags 6 sheets — the error is caught rather than shipped. Trading
a caught PBF error for 21 recovered critical-field observations is the trade this project's own
metric says to take.

It is also the field #52 was about, and #52's template fix is **not** in v5 — v5 trained before it.
So there is a specific, testable expectation for the next retrain rather than a hope.

### Consequences

- **The checkpoint has to be deployed.** `models/donut-both-v5` does not exist on any machine yet;
  v5's weights are at `D:/cera/kaggle_out_v5/donut-both-v5`. The failure is loud
  (`DonutCheckpointError`) and never falls back to the cloud VLM, so a missing checkpoint is an
  outage rather than a privacy incident. `errors.py`'s download hint now names the v5 kernel.
- **Per-epoch checkpoint dirs need the run root's processor files** copied in before they load
  (`processor_config.json`, `tokenizer.json`, `tokenizer_config.json`). v5's do not carry their own.
- **The v3 recorded reads are no longer a usable baseline.** They predate ADR-0011, so they replay
  uncropped. Re-record against the current engine before using them to compare anything.
- **This ADR has now been amended twice in one day in opposite directions.** That is the strongest
  available argument for #24's premise: an under-powered hold-out does not produce noisy answers,
  it produces confident wrong ones.
