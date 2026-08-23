# InForm

**InForm turns an InBody body-composition scan and a short intake form into a personalized daily nutrition and corrective-exercise plan — deterministically.**

It is the reference implementation of the concept paper *"Multimodal AI for Precision Fitness: A Deterministic Pipeline for InBody-Driven Nutritional and Corrective Exercise Planning"* (BINUS). The guiding principle: every medical and mathematical decision is made by deterministic code you can audit; a generative model is confined to writing the prose around those numbers and may never change them.

## What it does

Given a photo of an InBody 270 or 570 result sheet plus the user's onboarding form, InForm runs a four-stage pipeline:

![InForm pipeline: an InBody scan and user form flow through OCR into a fused input, then a deterministic nutrition engine and exercise filter consolidate into a Master JSON, which a separate generative LLM synthesis stage turns into the daily plan without changing any number.](docs/assets/pipeline.png)

1. **OCR** — reads the structured metrics off the InBody sheet (lean body mass, percent body fat, segmental lean analysis, visceral fat level, …).
2. **Nutrition engine** — computes BMR (Katch–McArdle), TDEE, and calorie/macro targets from those metrics. Deterministic.
3. **Exercise filter** — detects bilateral asymmetry (>5% left/right lean deviation) and selects targeted corrective exercises. Deterministic, independent of stage 2.
4. **LLM synthesis** — assembles stages 1–3 into a readable daily plan. It is a *linguistic* synthesizer only; validation enforces that it never mutates a deterministic number.

Stages 1–3 produce a consolidated **Master JSON**, the single source of truth handed to stage 4.

## Why deterministic

Fitness and nutrition guidance is health-adjacent — the numbers have to be reproducible and explainable. InForm draws a hard line between the **deterministic** core (all calculations) and the **generative** layer (wording only), so any recommendation traces back to a formula and a scanned value rather than a model's guess.

For terminology, the module contracts, and the OCR engine strategy, see [`CONTEXT.md`](CONTEXT.md) and the decision records in [`docs/adr/`](docs/adr/).
