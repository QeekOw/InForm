# InForm Repo Scaffolding — Design

**Date:** 2026-08-09
**Status:** Approved (design), pending implementation plan
**Scope:** Scaffolding only — structure, typed stubs, and domain docs. No working implementations.

## 1. Purpose

Stand up the `InForm` repo for the **InBody AI Fitness Assistant** described in the concept
paper *"Multimodal AI for Precision Fitness: A Deterministic Pipeline for InBody-Driven
Nutritional and Corrective Exercise Planning."*

The system is a four-stage deterministic pipeline. This deliverable creates the Python
package skeleton, the Pydantic schemas that define the JSON contracts between stages, the
domain documentation (`CONTEXT.md`, one seed ADR), and dependency/tooling files. Every
module entry function is present with a typed signature and docstring but raises
`NotImplementedError`. Later sessions fill in bodies one module at a time.

**Design principle:** the inter-module JSON contracts are the real product of this
scaffolding. If the schemas are right, each module can be built and tested in isolation.

## 2. The pipeline (from the paper)

```
InBody image ─▶ [1] OCR (Donut)  ─┐
User form ───────────────────────┼─▶ fused input ─┬─▶ [2] Nutrition engine ─┐
                                  │                └─▶ [3] Exercise filter ──┤
                                  │                                          ▼
                                  │                                    Master JSON
                                  │                                          │
                                  └───────────────────────────────▶ [4] LLM synthesis ─▶ Daily plan
```

Modules 2 and 3 are **independent** — both consume the fused (user + InBody) input and
produce structured output concurrently. Their outputs merge into the Master JSON, which is
the sole input to Module 4. Module 4 is a linguistic synthesizer only; it must not mutate
any deterministic number (enforced by validation — see §6).

## 3. Folder structure

```
InForm/
├── CLAUDE.md                       (exists)
├── README.md                       (exists — expand with project overview + layout)
├── CONTEXT.md                      (NEW — domain model + glossary)
├── pyproject.toml                  (NEW — deps + tooling)
├── .gitignore                      (NEW — Python)
├── .env.example                    (NEW — OPENAI_API_KEY, etc.)
├── docs/
│   ├── adr/
│   │   └── 0001-katch-mcardle-over-mifflin.md   (NEW — seed ADR)
│   └── agents/                     (exists)
├── src/inform/
│   ├── __init__.py
│   ├── schemas/                    ← Pydantic contracts (backbone)
│   │   ├── __init__.py
│   │   ├── user.py                 (UserProfile — onboarding form)
│   │   ├── inbody.py               (InBodyPayload, SegmentalLean)
│   │   ├── nutrition.py            (NutritionTargets)
│   │   ├── exercise.py             (Exercise, ExercisePlan)
│   │   └── master.py               (MasterPayload, DailyPlan)
│   ├── ocr/
│   │   ├── __init__.py
│   │   └── extract.py              (extract_inbody)
│   ├── nutrition/
│   │   ├── __init__.py
│   │   ├── engine.py               (compute_targets)
│   │   └── constants.py            (Katch-McArdle constant, thresholds)
│   ├── recommender/
│   │   ├── __init__.py
│   │   ├── filter.py               (recommend_exercises)
│   │   └── constants.py            (asymmetry threshold, goal rules)
│   ├── synthesis/
│   │   ├── __init__.py
│   │   ├── generate.py             (synthesize_plan)
│   │   └── validate.py             (dual-validation / drop-on-mutation)
│   └── pipeline.py                 (run_pipeline — orchestrates 1 → 2/3 → 4)
├── data/
│   └── README.md                   (points to exercise dataset + synthetic-gen plan)
└── tests/
    └── __init__.py                 (empty tree, ready for later TDD)
```

## 4. Module seams (stubbed interfaces)

Each module exposes one primary entry function. All bodies raise `NotImplementedError` with
a docstring describing the paper's intended logic.

| Module | File | Signature |
| ------ | ---- | --------- |
| 1 — Visual extraction | `ocr/extract.py` | `extract_inbody(image_path: Path) -> InBodyPayload` |
| 2 — Nutrition engine | `nutrition/engine.py` | `compute_targets(user: UserProfile, inbody: InBodyPayload) -> NutritionTargets` |
| 3 — Exercise recommender | `recommender/filter.py` | `recommend_exercises(user: UserProfile, inbody: InBodyPayload) -> ExercisePlan` |
| 4 — LLM synthesis | `synthesis/generate.py` | `synthesize_plan(master: MasterPayload) -> DailyPlan` |
| 4 — Validation | `synthesis/validate.py` | `validate_no_mutation(master: MasterPayload, plan: DailyPlan) -> DailyPlan` |
| Orchestrator | `pipeline.py` | `run_pipeline(image_path: Path, user: UserProfile) -> DailyPlan` |

## 5. Schemas (JSON contracts)

**`UserProfile`** (onboarding form)
- `age: int` — collected; **not** used by Katch–McArdle BMR. Reserved for goal/activity
  context and a possible future Mifflin fallback. Docstring must say so.
- `biological_sex: Literal["male", "female"]` — same note as `age`.
- `activity_multiplier: float` — TDEE = BMR × this (e.g. 1.2 sedentary … 1.9 very active).
- `fitness_goal: Literal["hypertrophy", "fat_loss"]`.

**`InBodyPayload`** (Module 1 output)
- `weight_kg: float`
- `lean_body_mass_kg: float` — **authoritative** input to Katch–McArdle.
- `skeletal_muscle_mass_kg: float` — SMM; distinct from LBM (see glossary).
- `percent_body_fat: float` — PBF; allows deriving LBM = weight × (1 − PBF/100) as a check.
- `basal_metabolic_rate_kcal: float` — BMR as reported by the device; **cross-check only**,
  not authoritative (engine recomputes via Katch–McArdle for determinism).
- `visceral_fat_level: int`
- `segmental_lean: SegmentalLean`

**`SegmentalLean`** — `left_arm_kg`, `right_arm_kg`, `left_leg_kg`, `right_leg_kg`,
`trunk_kg`. Basis for bilateral-asymmetry detection.

**`NutritionTargets`** (Module 2 output)
- `bmr_kcal: float` (computed: `370 + 21.6 × lean_body_mass_kg`)
- `tdee_kcal: float` (`bmr_kcal × activity_multiplier`)
- `target_calories_kcal: float` (TDEE adjusted for `fitness_goal`)
- `protein_g`, `carbs_g`, `fats_g`, `fiber_g: float`

**`Exercise`** — `name`, `target` (primary muscle), `body_part`, `equipment`,
`secondary_muscles: list[str]`, `movement_type: Literal["corrective_unilateral",
"bilateral_compound", "cardio_hiit"]`. Fields mirror the `hasaneyldrm/exercises-dataset`
taxonomy (`target`, `bodyPart`, `equipment`, `secondaryMuscles`).

**`ExercisePlan`** (Module 3 output) — `exercises: list[Exercise]`,
`detected_imbalances: list[str]` (human-readable, e.g. "L/R leg SMM deviation 7%").

**`MasterPayload`** (Module 4 input) — `user: UserProfile`, `inbody: InBodyPayload`,
`nutrition: NutritionTargets`, `exercises: ExercisePlan`.

**`DailyPlan`** (Module 4 output) — `narrative_text: str` plus the echoed deterministic
fields (calories + macros) so `validate.py` can confirm the LLM did not mutate them.

## 6. Key deterministic rules (encoded as stub docstrings + constants)

- **Katch–McArdle:** `BMR = 370 + (21.6 × LBM_kg)`. See `nutrition/constants.py`.
- **Bilateral asymmetry threshold:** `> 5%` deviation between a limb pair triggers targeted
  unilateral corrective movements. Constant in `recommender/constants.py`.
- **Goal-driven adaptation:** hypertrophy → prioritize progressive-overload bilateral
  compounds; fat-loss + high visceral fat → raise cardio/HIIT frequency.
- **Dual validation (Module 4):** OpenAI Structured Outputs (JSON Schema) at the API level;
  Pydantic validation at the backend. If any deterministic number is mutated, drop the
  generative response and fall back to deterministic template text.

## 7. Domain docs

**`CONTEXT.md`** — glossary of the ubiquitous language, following the
`docs/agents/domain.md` convention. Must explicitly distinguish:
- **SMM vs LBM** — Skeletal Muscle Mass ≠ Lean Body Mass. Katch–McArdle uses LBM.
- **Katch–McArdle vs Mifflin–St Jeor** — see ADR-0001.
- LBM, PBF, TDEE, BMR, Visceral Fat, Segmental Lean Analysis, bilateral asymmetry,
  Master JSON, the deterministic-vs-generative boundary.

**`docs/adr/0001-katch-mcardle-over-mifflin.md`** — records that the paper is internally
inconsistent (abstract/§3.1.2/§3.3 say Katch–McArdle; §2.1.1 says Mifflin–St Jeor), and
that **Katch–McArdle is authoritative** because it is the paper's stated LBM-based
differentiator and appears in three of four relevant sections. Notes that `age`/`sex` are
therefore unused by the BMR calculation and retained for other purposes.

## 8. Dependencies (`pyproject.toml`)

- Core: `pydantic`, `openai`. Python ≥ 3.11.
- Optional `ocr` group: `torch`, `transformers` (heavy ML deps, installable separately so
  core logic can be used without PyTorch).
- Dev group: `pytest`, `ruff`.

## 9. Out of scope (explicitly deferred)

- Any working implementation (all bodies raise `NotImplementedError`).
- Frontend / UI (backend-only for now; monorepo split deferred).
- Training the Donut model or generating synthetic data (`data/README.md` documents the
  plan only).
- Test bodies (empty `tests/` tree only).
