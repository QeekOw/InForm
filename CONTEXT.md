# InForm — Domain Context

The ubiquitous language for the **InBody AI Fitness Assistant** (concept paper:
*"Multimodal AI for Precision Fitness: A Deterministic Pipeline for InBody-Driven
Nutritional and Corrective Exercise Planning,"* BINUS —
[full text](docs/paper/STRIVE_ConceptPaper.pdf)).

The paper is a **starting point, not a specification**: it was written by one of this
project's own developers and the build takes inspiration from it. Where a documented
protocol in it conflicts with what the product needs, the product wins, and the ADR that
records the protocol says so.

InForm is a **deterministic four-stage pipeline**. Human-interpretable medical logic stays
deterministic; generative AI is confined to linguistic synthesis. This glossary is the
source of truth for terminology — use these terms verbatim in code, issues, and tests.

## The pipeline

```
InBody image ─▶ [1] OCR (Module 1) ──┐
User form ────────────────────────────┼─▶ fused input ─┬─▶ [2] Nutrition engine ─┐
                                       │                └─▶ [3] Exercise filter ──┤
                                       │                                          ▼
                                       │                                    Master JSON
                                       └──────────────────────────▶ [4] Plan synthesis ─▶ Daily plan
```

Modules 2 and 3 are independent and deterministic. Module 4 assembles the Daily plan:
deterministic code renders every actionable fact, while generative AI may add only a
non-actionable Coaching note.

## Glossary

- **LBM (Lean Body Mass)** — total body mass minus fat mass. The **authoritative** input to
  the Katch–McArdle BMR formula. Read directly off the InBody sheet; cross-checked against
  `weight × (1 − PBF/100)`. See [ADR-0003](docs/adr/0003-extract-lbm-directly.md). **On a real
  InBody result sheet this quantity is labeled "Fat Free Mass" (Research Parameters), not "Lean
  Body Mass"** — InBody uses the two interchangeably, so `lean_body_mass_kg` is read from the
  FFM row (issue #13 / ADR-0007).
- **SMM (Skeletal Muscle Mass)** — the mass of skeletal muscle specifically. **Distinct from
  LBM** (LBM also includes water, organs, bone mineral). Katch–McArdle uses LBM, *not* SMM.
  Do not conflate them.
- **PBF (Percent Body Fat)** — body fat as a percentage of total weight. Used to cross-check
  LBM. A **cross-field attribution error** is an OCR read whose value is attributed to PBF from
  a different field; **format-shape bleed** is its observed subtype where a limb-style numeric
  shape appears in the PBF read.
- **BMR (Basal Metabolic Rate)** — resting daily calorie need. Computed deterministically via
  **Katch–McArdle** `BMR = 370 + 21.6 × LBM_kg`. The device also prints a BMR value; that
  printed value is a **cross-check only**, not authoritative (the engine recomputes for
  determinism). Katch–McArdle chosen over Mifflin–St Jeor — see ADR-0001 (reserved).
- **TDEE (Total Daily Energy Expenditure)** — `BMR × activity_multiplier`. Basis for calorie
  targets.
- **Visceral Fat Level** — abdominal-organ fat rating. Printed by **both** the InBody 270 and
  570 (confirmed on two real 270 sheets — ADR-0004 correction, issue #13), but a *programmable*
  output that may be absent on some configs, so still modeled as optional (`int | None`). See
  [ADR-0004](docs/adr/0004-device-scope-optional-fields.md).
- **Segmental Lean Analysis** — per-segment lean mass for the five body segments: left arm,
  right arm, left leg, right leg, trunk. Basis for bilateral-asymmetry detection.
- **Segmental Fat Analysis** — per-segment *fat* mass, printed for the same five segments and
  in the same units. Nothing in InForm reads it: it is not in the schema and no module consumes
  it. It matters because it is the nearest neighbour of **Segmental Lean Analysis** on the page,
  and a read that strays into it returns a plausible number for the wrong quantity — the
  sheet_05 panel crossing. A synthetic sheet must therefore render it the way the device does,
  even though no value is scored, or the model learns to tell the two panels apart by a cue that
  exists only in training ([ADR-0007](docs/adr/0007-synthetic-data-generation.md), issue #50).
- **Confirmed measurement** — a measured value the person has reviewed and accepted as shown,
  or corrected. A correction counts as confirmation, with a reminder to check it against the
  source sheet. Confirmation records the person's review; it is not an independent validation
  of the measurement.
- **Bilateral asymmetry** — a lean-mass deviation between confirmed readings for a left/right
  limb pair. Each pair is assessed independently once both readings are confirmed. A deviation
  **> 5%** triggers targeted unilateral corrective exercises (Module 3).
- **Core fields** — the scalar values on a sheet (weight, LBM, PBF, SMM, BMR, Visceral Fat
  Level), as against the five **Segmental Lean** values. Scored and reported separately,
  because a limb carries a relative tolerance the scalars do not
  ([ADR-0006](docs/adr/0006-ocr-evaluation-protocol.md)).
- **InBody 270** — the sole supported Module 1 device layout. It reports Visceral Fat Level
  (ADR-0004 correction, issue #13); its BMR and Visceral Fat outputs are programmable.
- **InBody 570** — a retired device layout, outside Module 1's training, evaluation, and runtime
  scope. Its prior synthetic data is archival rather than active training or evaluation data.
- **Development regression set** — the fixed 12-sheet real InBody 270 set used to select a
  candidate OCR checkpoint. It is not independent promotion evidence.
- **Independent confirmation set** — at least five newly collected real InBody 270 sheets, kept
  unseen until the candidate checkpoint and its training recipe are frozen. It confirms a
  promotion decision and must not tune that candidate.
- **Promotion gate** — the evidence required to replace the default OCR checkpoint: on the
  development regression set, PBF is at least 10/12, both arms are 12/12, and the flagged/unread
  split is no worse than v5; the frozen candidate must then pass independent confirmation.
- **Sheet source** — what the person handed InForm: a **photo** they took, a **PDF** whose first
  page is rendered in the browser (issue #81), or a **sample** picked from the gallery. The image
  submitted to `/reads` looks the same either way, so the source rides along on the request and
  decides how a refusal is worded — a PDF uploader is never told to retake a photo in good
  lighting (issue #83). The refusal itself does not vary: ADR-0008 stays fail-closed.
- **Master JSON (`MasterPayload`)** — the consolidated deterministic output of Modules 1–3;
  the sole input to Module 4.
- **Daily plan** — the user-facing nutrition and exercise plan. Its targets, prescribed
  exercises, and imbalance findings are deterministic; it remains complete when no generated
  coaching is available.
- **Coaching note** — optional generated encouragement that gives the Daily plan a personal
  voice without adding measurements, targets, prescriptions, or diagnostic claims.
- **Deterministic / generative boundary** — the architectural rule that every actionable plan
  fact comes from deterministic code; generative AI supplies voice only. See
  [ADR-0013](docs/adr/0013-keep-actionable-plan-facts-deterministic.md).

## Module 1 (OCR) — the two engines

Module 1 fills one seam: `extract_inbody(image_path) -> InBodyExtraction` (the read values plus
`unread`/`flagged` lists; `.as_payload()` promotes a clean, complete read to an `InBodyPayload`).
Exactly one *engine* plugs into that seam at a time. They are swappable alternatives, not layers:

- **Donut engine** — a Document Understanding Transformer (`naver-clova-ix/donut-base`)
  **fine-tuned** on synthetic InBody sheets — the paper's core contribution; self-hosted, no
  per-call cost, on-device-capable. The **default runtime engine**; its checkpoint lives
  outside the repo (loaded by local path).
- **VLM engine** — a general vision-language model (OpenAI, zero/few-shot, Structured
  Outputs). No training. Now the **evaluation oracle** only: an explicitly-chosen engine,
  never the runtime default and never a runtime fallback.

See [ADR-0002](docs/adr/0002-vlm-baseline-then-donut.md) and
[ADR-0010](docs/adr/0010-donut-default-runtime-engine.md).

## Read outcomes

Every sheet an engine reads lands in exactly one **read outcome**. The distinction that matters
is not how much was read but **whether a person is required to look at it**.

- **refused** — nothing readable. The person is shown a calm explanation, not an error.
- **unread** — some fields missing, no cross-check objection. The person supplies them.
- **flagged** — a cross-check objected. The person compares the value against the sheet and
  confirms or corrects it.
- **unverified** — every field read and no cross-check objected. The engine has no objection,
  which is not the same as the read being right, so the name states the risk rather than the
  hope. _Avoid_: usable, clean, good.

**No read reaches a plan unseen.** Every read passes a confirmation step, `unverified` ones
included, so `unverified` is a transient state and never a terminal one. A person confirms or
corrects what the engine read before any plan is built.

- **Silent error** — a wrong value inside an `unverified` read: wrong, and carrying no signal
  that anything is wrong. Confirmation is what stands between it and a plan, and confirmation
  is a person reading a screen, so the protection is real but not absolute. It remains the
  **headline measure** of an engine's fitness, because every other failure announces itself.
  Per-field accuracy is a diagnostic, not the headline: it counts a thirty-second correction
  and a wrong number in someone's plan the same.
- **A silent-error rate alone does not rank an engine**, and is read beside the read outcomes
  or not at all. An engine that flags or under-reads every sheet produces no `unverified` reads
  and therefore no silent errors, which is a perfect score for something nobody can use.
  Measured, not hypothetical: two of the four v4 checkpoints score exactly that way. Silent
  error is the measure of **risk** and the outcome split is the measure of **cost** — what the
  engine asks of a person — and an engine is judged on both.
- **Measured field** — a value an engine read. **Corrected field** — a value a person typed,
  recorded alongside the measured fields and never merged into them. Confirming a `flagged`
  value leaves it a measured field; only changing it makes a corrected field.
