# InForm — backend

The application API for InForm's Track B walking skeleton
([issue #31](https://github.com/QeekOw/InForm/issues/31)). FastAPI, currently a
thin wrapper around the deterministic parts of the `inform` Python package that
lives at the repo root (`src/inform/`) — this service doesn't vendor or duplicate
any of that logic, it imports it directly.

## What it actually does

Three endpoints:

- `GET /` — service metadata (status, docs URL, health endpoint).
- `GET /health` — liveness check, returns `{"status": "ok", "service": "inform-api"}`.
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

## Deploying (Render)

The `sys.path` setup needs both `backend/` *and* the root `src/`
present in the deployed container, so there's a `Dockerfile` at the **repo
root** that makes this unambiguous: it `COPY`s exactly `backend/` and `src/`
into the image and starts uvicorn from `backend/`, reading `$PORT` the way
Render (and most PaaS hosts) inject it.

The deployment configuration is codified via `render.yaml` at the repo root:
- **Service Name**: `inform-api`
- **Environment**: Docker (`./Dockerfile` with repo root context)
- **Branch**: `main`
- **Auto-Deploy**: Enabled on push to `main`
- **Health Check Path**: `/health`

In Render's dashboard:
1. **New → Blueprint** (or **New → Web Service → connect this repo**).
2. Set branch to `main` with **Environment: Docker**.
3. Select the **Free** instance type.
4. Auto-deploy will trigger on every push merged to `origin/main`.

## Privacy & Known gaps

- **Privacy boundary (ADR-0005)**: Per ADR-0005, external LLM calls via
  `OPENAI_API_KEY` are strictly scoped for development/POC testing with
  synthetic or consented data. Real patient health data must never be
  transmitted to external cloud APIs. Without `OPENAI_API_KEY`, the service
  relies on the deterministic template synthesizer completely locally.
- **CORS is wide open** (`allow_origins=["*"]`) — fine for an initial deploy,
  worth scoping down to the Vercel origin once that URL is known.
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
