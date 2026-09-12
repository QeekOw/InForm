# InForm — backend

The application API for InForm's Track B walking skeleton
([issue #31](https://github.com/QeekOw/InForm/issues/31)). FastAPI, currently a
thin wrapper around the deterministic parts of the `inform` Python package that
lives at the repo root (`src/inform/`) — this service doesn't vendor or duplicate
any of that logic, it imports it directly.

## What it actually does

Three endpoints:

- `GET /` and `GET /health` — liveness checks, return `{"status": "ok", ...}`.
- `POST /plan` — the real thing. Takes a `UserProfile` and a complete
  `InBodyPayload` (exact shape of `inform.user.UserProfile` /
  `inform.inbody.InBodyPayload` — FastAPI validates against those pydantic
  models directly), and runs:
  1. `inform.nutrition_engine.compute_targets` — Katch-McArdle BMR, TDEE, calorie
     target, macro split.
  2. `inform.exercise_filter.recommend_exercises` — bilateral-asymmetry detection
     and exercise selection against `inform.exercise_pool.DEFAULT_EXERCISE_POOL`.
  3. `inform.synthesis.generate.synthesize_plan` — Module 4's narrative text.

  Returns the `NutritionTargets` and `ExercisePlan` structured objects alongside
  the narrative, not folded into it — the frontend renders the audited numbers
  directly rather than trusting them only as restated inside generated prose,
  which is the whole point of "deterministic numbers, generative prose only."

That's it. No OCR (Module 1), no accounts, no database, no persistence.

## How it reaches the `inform` package

`main.py` adds the repo's `src/` to `sys.path` at import time rather than
installing `inform` as a dependency — deliberate, because Modules 2 and 3 (and
Module 4's fallback path) need only `pydantic`, not the heavy stuff
(`torch`/`transformers` for Donut, `openai` for the real LLM call). Importing
only `nutrition_engine`, `exercise_filter`, `exercise_pool`, `user`, `inbody`,
`master`, and `synthesis.generate` — never `pipeline.py` or `extract.py` — keeps
those heavy imports out of this service entirely.

`synthesize_plan(master, client=None)` is called with no OpenAI client. It tries
to construct one internally, and if that fails (no `openai` package installed,
no `OPENAI_API_KEY` set — both true here), it catches the failure and falls back
to `generate_fallback_plan`, a deterministic template. So the narrative text is
real prose, just not LLM-written, until an API key is wired up.

## Known gaps

- **Not deployed.** Runs locally only right now. The intended target is Railway,
  but there's an unverified risk worth checking first: the `sys.path` trick above
  assumes the deployed container has the whole repo tree (`backend/` *and* the
  sibling `src/`) present. If Railway's project root directory ends up set to
  `backend/` only, `../src` won't exist and every request will fail at import
  time. Point the root directory at the repo root with a
  `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` start command
  instead, or confirm Railway actually clones the full repo regardless — untested
  either way.
- **CORS is wide open** (`allow_origins=["*"]`) — fine for local dev, needs
  scoping down before this URL is public.
- **No real LLM narrative** — needs `OPENAI_API_KEY` in the environment; falls
  back safely without it, per above.
- **No auth, no persistence** — every `/plan` call is stateless; nothing is
  saved.

## Running locally

```bash
python -m venv .venv
./.venv/Scripts/activate        # Windows; source .venv/bin/activate elsewhere
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

`GET http://localhost:8000/health` should return `{"status":"ok",...}`. The
frontend expects this on `localhost:8000` by default (`NEXT_PUBLIC_API_URL`).

Quick smoke test against the real pipeline:

```bash
curl -X POST http://localhost:8000/plan \
  -H "Content-Type: application/json" \
  -d '{
    "user": {"age": 30, "biological_sex": "female", "activity_multiplier": 1.55, "fitness_goal": "fat_loss"},
    "inbody": {
      "weight_kg": 68.0, "lean_body_mass_kg": 50.0, "percent_body_fat": 26.5,
      "skeletal_muscle_mass_kg": 28.0, "basal_metabolic_rate_kcal": 1450.0,
      "segmental_lean": {"left_arm_kg": 2.4, "right_arm_kg": 2.7, "left_leg_kg": 7.8, "right_leg_kg": 7.9, "trunk_kg": 22.0},
      "source_device": "inbody_570", "visceral_fat_level": 8
    }
  }'
```

This matches the root README's worked example — the returned `target_calories_kcal`
should come back as `1747.5`.
