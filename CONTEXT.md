# InForm — Domain Context

The ubiquitous language for the **InBody AI Fitness Assistant** (concept paper:
*"Multimodal AI for Precision Fitness: A Deterministic Pipeline for InBody-Driven
Nutritional and Corrective Exercise Planning,"* BINUS —
[full text](docs/paper/STRIVE_ConceptPaper.pdf)).

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
                                       └──────────────────────────▶ [4] LLM synthesis ─▶ Daily plan
```

Modules 2 and 3 are independent and deterministic. Module 4 is a linguistic synthesizer
only — it must never mutate a deterministic number (enforced by validation).

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
  LBM.
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
- **Bilateral asymmetry** — a lean-mass deviation between a left/right limb pair. A deviation
  **> 5%** triggers targeted unilateral corrective exercises (Module 3).
- **Core fields** — the scalar values on a sheet (weight, LBM, PBF, SMM, BMR, Visceral Fat
  Level), as against the five **Segmental Lean** values. Scored and reported separately,
  because a limb carries a relative tolerance the scalars do not
  ([ADR-0006](docs/adr/0006-ocr-evaluation-protocol.md)).
- **InBody 270 / InBody 570** — the two device layouts in scope. Both report Visceral Fat Level
  (ADR-0004 correction, issue #13); the 570 reports more, and BMR / Visceral Fat are
  programmable outputs. See [ADR-0004](docs/adr/0004-device-scope-optional-fields.md).
- **Master JSON (`MasterPayload`)** — the consolidated deterministic output of Modules 1–3;
  the sole input to Module 4.
- **Deterministic / generative boundary** — the architectural rule that all numbers are
  computed by deterministic code; the LLM only writes prose around them and may never change
  them.

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
