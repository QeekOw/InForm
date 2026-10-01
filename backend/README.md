# InForm — backend

The application API for InForm's Track B walking skeleton
([issue #31](https://github.com/QeekOw/InForm/issues/31)). FastAPI, currently a
thin wrapper around the deterministic parts of the `inform` Python package that
lives at the repo root (`src/inform/`) — this service doesn't vendor or duplicate
any of that logic, it imports it directly.

## What it actually does

Endpoints:

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

### Accounts & History (issues #41–#44)

Phase 2 added a Postgres-backed account and Scan history layer:

- `POST /auth/signup`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` —
  email + password, hashed with bcrypt. The session is a signed JWT carried in an
  `httpOnly` cookie, valid 30 days, so a signed-in person stays signed in on
  their next visit.
- `POST /scans` — saves a completed read as an **immutable Scan**: the Profile
  that produced it is frozen onto the Scan as a JSON snapshot (never a foreign
  key to a mutable row), alongside the effective InBody reading, the
  corrected/confirmed field lists, and the produced plan. Scanning again
  appends; Scans are never edited.
- `GET /scans` — History, newest first, with headline numbers and a
  corrected-fields marker.
- `GET /scans/{scan_id}` — one past Scan's full stored results. A Scan belonging
  to another account returns 404, never 403, so the response can't confirm the
  id exists.
- `GET /scans/current` — the most recent Scan plus `age_days` and `is_stale`.
  Staleness is decided **server-side** against `STALENESS_DAYS` (30) and is never
  computed by the frontend. A stale plan is returned in full: never hidden,
  expired, or recomputed.
- `DELETE /account` — permanently removes the account and, by FK cascade, every
  Scan belonging to it. No soft delete, no retained analytics copy (ADR-0011).

Still no OCR (Module 1) in this service, and still **no image is ever persisted**
(ADR-0011) — only the structured numeric extraction, the frozen Profile, and the
plan are stored.

## Environment variables

Copy `.env.example` to `.env` for local development. `.env` is gitignored;
`.env.example` is not, so never put real values in it.

| variable | purpose |
| --- | --- |
| `DATABASE_URL` | Postgres connection string. On Neon, use the **direct** hostname (no `-pooler`) — the pooled endpoint runs PgBouncer in transaction mode, which is incompatible with holding one transaction open across several statements, as both request-scoped sessions and the test suite's rolled-back-transaction fixture do. |
| `SESSION_SECRET` | Signing secret for session JWTs. Rotating it invalidates every existing session. |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins allowed to send credentials. No wildcard is possible once `allow_credentials=True`; browsers reject that pairing. Defaults to `http://localhost:3000`. |
| `ALLOW_INSECURE_COOKIES` | Set `true` **only** for local http development. Production leaves it unset so the session cookie is sent `Secure` + `SameSite=None` for cross-site use. |

Database schema is managed with Alembic from the `backend/` directory:

```bash
alembic upgrade head          # apply migrations
alembic revision --autogenerate -m "..."   # after changing db/models.py
```

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

The live service (`https://inform-7x9o.onrender.com`) was created in Render's
dashboard: **New → Web Service → connect this repo**, **Environment: Docker**, root
directory left as the repo root, **Free** instance. Its branch and auto-deploy settings
live in that dashboard (**Settings → Build & Deploy**), not in this repo.

`render.yaml` describes the same service as a Render Blueprint that tracks `main`. It
only applies to a service created with **New → Blueprint**. It does not change the
existing dashboard service, and deploying it would create a second service with its
own URL.

## Privacy & Known gaps

- **Privacy boundary (ADR-0005)**: Per ADR-0005, external LLM calls via
  `OPENAI_API_KEY` are strictly scoped for development/POC testing with
  synthetic or consented data. Real patient health data must never be
  transmitted to external cloud APIs. Without `OPENAI_API_KEY`, the service
  relies on the deterministic template synthesizer completely locally.
- **CORS is now restricted** to the origins in `ALLOWED_ORIGINS`, because a
  cross-site session cookie requires `allow_credentials=True`, which browsers
  refuse to pair with a wildcard origin. A deployment that forgets to set
  `ALLOWED_ORIGINS` will block its own frontend.
- **`/plan` is still stateless** — it computes and returns without saving.
  Persistence is opt-in via `POST /scans`, which requires a signed-in account.
  The whole anonymous flow still works with no account at all.
- **No password reset flow.** Deliberate scope choice for the smallest credible
  sign-in (issue #41); a forgotten password currently means a new account.

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
