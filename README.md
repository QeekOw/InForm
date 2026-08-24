# InForm

InForm reads an InBody body-composition scan and a short intake form, then produces a personalized daily nutrition and corrective-exercise plan.

The idea it is built around: every medical and mathematical decision is made by deterministic code you can audit, and the language model only writes the prose around those numbers. It never changes them. A recommendation always traces back to a formula and a value read off the scan, not to a model's guess.

## What it does

You give it a photo of an InBody 270 or 570 result sheet plus the user's onboarding form. Four stages run:

![InForm pipeline diagram: an InBody scan and user form go through OCR and a fused input into the nutrition engine and exercise filter, which feed a Master JSON that the LLM synthesis stage turns into the daily plan.](docs/assets/pipeline.png)

1. **OCR (Module 1)** reads the structured metrics off the sheet: lean body mass, percent body fat, segmental lean analysis, visceral fat level, and so on.
2. **Nutrition engine (Module 2)** computes BMR (Katch-McArdle), TDEE, and calorie and macro targets from those metrics.
3. **Exercise filter (Module 3)** looks for bilateral asymmetry, a left/right lean gap over 5%, and selects corrective exercises. It runs independently of the nutrition engine.
4. **LLM synthesis (Module 4)** turns the first three stages into a readable daily plan. It only writes language, and a validation step confirms it has not altered any number.

Stages 1 to 3 write a single consolidated object, the `MasterPayload` (the "Master JSON"), which is the only thing stage 4 sees.

## Why it is built this way

Nutrition and fitness advice is health-adjacent, so the numbers have to be reproducible and explainable. InForm draws a hard line between the deterministic core (all calculations) and the generative layer (wording only). Two mechanisms hold that line:

- Module 2 recomputes BMR from lean body mass with Katch-McArdle. The BMR printed on the device sheet is treated as a cross-check value only, never as the source of truth.
- Module 4 runs a dual validation. The deterministic figures are echoed as structured fields and checked exactly, and the narrative prose is scanned so a mutated calorie figure cannot slip through. If the model changes a number, or the call fails, the plan falls back to a deterministic template.

## Project layout

```
src/inform/
  formulas.py          Shared body-composition formulas (Katch-McArdle BMR)
  user.py              UserProfile (onboarding form)
  inbody.py            InBodyPayload / PartialInBody / SegmentalLean schemas
  extract.py           Module 1 seam: extract_inbody() + cross-check flags
  engines/
    vlm.py             OCR engine A: vision-language model (phase-1 baseline)
    donut.py           OCR engine B: fine-tuned Donut (self-hosted, phase 2)
  nutrition.py         NutritionTargets schema
  nutrition_engine.py  Module 2: compute_targets()
  exercise.py          Exercise / ExercisePlan schemas
  exercise_filter.py   Module 3: recommend_exercises()
  exercise_pool.py     Stopgap candidate exercise set for the demo
  master.py            MasterPayload (Modules 1-3) and DailyPlan (Module 4)
  synthesis/
    generate.py        Module 4: synthesize_plan()
    validate.py        Dual-validation guard + deterministic fallback
  pipeline.py          Orchestrator: run_pipeline()
  evaluate.py          OCR accuracy scoring against ground truth
  synthetic/           Synthetic InBody sheet generation (for OCR eval/training)
  training/            Donut fine-tuning (dataset + train loop)
```

Domain terms and the rules behind each module live in [`CONTEXT.md`](CONTEXT.md). Design decisions are recorded in [`docs/adr/`](docs/adr/).

## Install

Requires Python 3.11 or newer.

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The base install is deliberately light (Pydantic, OpenAI SDK, Pillow). The heavier Donut fine-tuning stack (torch, transformers) is a separate extra:

```
pip install -e ".[training]"
```

Live OCR extraction and LLM synthesis call OpenAI, so set `OPENAI_API_KEY` before running the pipeline on a real image. If synthesis fails or the key is missing, Module 4 returns the deterministic fallback plan rather than erroring.

## Quick start

Run the whole pipeline on an InBody photo:

```
python scripts/demo_pipeline.py path/to/inbody_sheet.jpg \
    --age 30 --sex female --activity 1.55 --goal fat_loss
```

It prints the consolidated `MasterPayload` and then the synthesized daily plan.

As a library:

```python
from pathlib import Path

from inform.pipeline import run_pipeline
from inform.user import UserProfile
from inform.exercise_pool import DEFAULT_EXERCISE_POOL

user = UserProfile(
    age=30,
    biological_sex="female",
    activity_multiplier=1.55,
    fitness_goal="fat_loss",
)

plan = run_pipeline(Path("inbody_sheet.jpg"), user, DEFAULT_EXERCISE_POOL)
print(plan.narrative_text)
```

For a deterministic run with no live model, `assemble_master_payload()` gives you Modules 1 to 3 (the `MasterPayload`) on its own, and you can pass a mock client into `run_pipeline(..., llm_client=...)`.

## OCR engines

Module 1 fills one seam, `extract_inbody(image_path)`, and exactly one engine plugs into it at a time. They are swappable alternatives, not layers:

- The **VLM engine** is a general vision-language model used as the phase-1 baseline and the permanent evaluation oracle. It is scoped to synthetic and consented images, never real personal health data, until the Donut engine lands (ADR-0005).
- The **Donut engine** is a Document Understanding Transformer fine-tuned on synthetic InBody sheets. It is self-hosted with no per-call cost and is the paper's core contribution.

The `synthetic/` package renders realistic InBody 270 and 570 sheets with known ground-truth values, which is what the Donut engine trains on and what `evaluate.py` scores both engines against. See [ADR-0002](docs/adr/0002-vlm-baseline-then-donut.md).

## Tests

```
pytest -q
```

The suite covers each module in isolation plus the end-to-end pipeline, including the fail-closed extraction paths and the Module 4 no-mutation guard.

## Status

This is a working proof of concept. Modules 1 to 4 run end to end on synthetic sheets, and the deterministic contracts between them are stable. The VLM engine is the active OCR path; the Donut engine has its training harness in place but is not yet trained and evaluated. `exercise_pool.py` ships a small stopgap exercise set so the demo runs; production would inject a full dataset.
