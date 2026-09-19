<p align="center">
  <img src="frontend/public/brand/inform-logo-on-dark.png" alt="InForm" width="620">
</p>

<p align="center">
  <a href="https://in-form.vercel.app"><img src="https://img.shields.io/badge/Live_demo-Vercel-000000?logo=vercel&logoColor=white" alt="Open the InForm demo"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" alt="TypeScript 5">
  <img src="https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white" alt="Next.js 16">
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
</p>

<p align="center">
  Turn body-composition data into an explainable nutrition and training plan.
</p>

## Try it

**[Open the live demo →](https://in-form-chi.vercel.app)**

InForm is a web prototype for turning reviewed body-composition readings, a fitness goal, and an activity profile into daily calorie and macro targets plus a corrective exercise plan.

All actionable plan facts come from deterministic, auditable code. AI may provide an optional coaching note, but it cannot alter measurements, targets, exercises, or imbalance findings.

> InForm supports fitness planning. It is not a medical diagnosis or a substitute for professional advice.

## What you can do today

- Enter as a guest or complete a profile.
- Choose a sample scan, review its measurements, and correct or confirm values before a plan is created.
- Get daily nutrition targets and a training plan that flags meaningful left/right lean-mass asymmetry.
- Use the deployed frontend on Vercel, backed by the InForm API on Render.

## Current prototype scope

The app is intentionally transparent about what is and is not live yet:

- The web flow currently uses sample readings or clearly labelled demo values. Upload, camera, and PDF screens are part of the user experience, but uploaded files are **not yet processed by OCR**.
- Accounts, sign-in, saved history, and persistence are not implemented. The browser keeps the in-progress plan only for the current session.
- The app does not make device-specific compatibility promises in its public experience.

## How it works

```
Reviewed measurements + profile
            │
            ├──► Nutrition engine ─┐
            └──► Exercise filter ──┼──► Master payload ──► Daily plan
                                   │                         └──► Optional coaching note
                                   └── deterministic plan facts
```

![InForm pipeline: reviewed measurements and profile flow through deterministic nutrition and exercise stages into MasterPayload, then into a daily plan with an optional coaching note.](docs/assets/pipeline.png)

## Run it locally

Requirements: Python 3.11+, Node.js, and npm.

Start the API from one terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1       # macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend from a second terminal at the repository root:

```powershell
Copy-Item frontend/.env.local.example frontend/.env.local
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). `frontend/.env.local` sets `NEXT_PUBLIC_API_URL`; keep its local default for development or point it at a deployed API.

## Project layout

| Path | Purpose |
| --- | --- |
| `frontend/` | Next.js interface for onboarding, sample selection, review, profile input, and results |
| `backend/` | FastAPI service for samples, reads, and plan generation |
| `src/inform/` | Deterministic nutrition, exercise, validation, and plan-domain logic |
| `docs/assets/` | Brand and architecture assets used by this README |
| `tests/` | Unit and integration tests |

## Development

Run the Python test suite from the repository root:

```powershell
pip install -e ".[dev]"
pytest -q
```

For implementation details, see the [frontend guide](frontend/README.md), [backend API guide](backend/README.md), [domain context](CONTEXT.md), and [architecture decisions](docs/adr/).
