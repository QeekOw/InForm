# InForm

InForm reads an InBody body-composition scan and a short intake form, then produces a personalized daily nutrition and corrective-exercise plan.

The idea it is built around: every medical and mathematical decision is made by deterministic code you can audit, and the language model only writes the prose around those numbers. It never changes them.

## What it does

You give it a photo of an InBody 270 or 570 result sheet plus the user's onboarding form. Four stages run:

![InForm pipeline diagram: an InBody scan and user form go through OCR and a fused input into the nutrition engine and exercise filter, which feed a Master JSON that the LLM synthesis stage turns into the daily plan.](docs/assets/pipeline.png)

1. **OCR** reads the structured metrics off the sheet: lean body mass, percent body fat, segmental lean analysis, visceral fat level, and so on.
2. **Nutrition engine** computes BMR (Katch-McArdle), TDEE, and calorie and macro targets from those metrics.
3. **Exercise filter** looks for bilateral asymmetry, a left/right lean gap over 5%, and picks corrective exercises. It runs independently of the nutrition engine.
4. **LLM synthesis** turns the first three stages into a readable daily plan. It only writes language; a validation step confirms it has not altered any number.

Stages 1 to 3 write a single Master JSON, which is the only thing stage 4 sees.

## Why it's built this way

Nutrition and fitness advice is health-adjacent, so the numbers have to be reproducible and explainable. Keeping every calculation in deterministic code, and letting the model touch only the wording, means any recommendation traces back to a formula and a value read off the scan rather than a model's guess.

For the terminology, the module contracts, and how the OCR engine was chosen, see [`CONTEXT.md`](CONTEXT.md) and the decision records in [`docs/adr/`](docs/adr/).
