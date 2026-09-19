<p align="center">
  <img src="frontend/public/brand/inform-logo-on-dark.png" alt="InForm" width="620">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" alt="TypeScript 5">
  <img src="https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white" alt="Next.js 16">
  <img src="https://img.shields.io/badge/React-19-149ECA?logo=react&logoColor=white" alt="React 19">
  <img src="https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?logo=tailwindcss&logoColor=white" alt="Tailwind CSS 4">
</p>

<p align="center">
  Turn an InBody scan into an explainable nutrition and corrective-exercise plan.
</p>

InForm is an InBody AI Fitness Assistant. It combines an InBody result sheet with a person's profile and goal to produce daily calorie and macro targets plus an exercise plan that accounts for left/right muscle imbalances.

The important distinction: the plan's actionable facts are calculated by deterministic, auditable code. AI may add an optional coaching note, but it cannot change measurements, targets, or prescriptions.

> InForm supports fitness planning and is not a medical diagnosis or substitute for professional advice.

## What it does

- Reads supported InBody 270 and 570 result sheets through OCR, or accepts confirmed measurements directly.
- Calculates BMR, TDEE, calorie targets, macros, and fibre from the profile and body-composition data.
- Detects bilateral lean-mass asymmetries and selects corrective unilateral exercises when appropriate.
- Returns a structured Daily plan; narrative coaching is optional and constrained to non-actionable text.

## How it works

```
InBody image ──► OCR ──────────────┐
Profile + goal ────────────────────┼──► Nutrition engine ─┐
                                  └──► Exercise filter ──┼──► Daily plan
                                                          └──► Optional coaching note
```

The nutrition engine and exercise filter are independent deterministic modules. The final synthesis layer renders their output and validates that generated prose has not changed any plan facts.

![InForm pipeline diagram: an InBody scan and profile flow through OCR, nutrition, exercise selection, and synthesis to produce a daily plan.](docs/assets/pipeline.png)

## Quick start: deterministic core

Requirements: Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1       # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

The deterministic core needs neither an API key nor an InBody image. You can construct an `InBodyPayload` directly, or generate a practice sheet with `inform.synthetic.generate_sheet(...)`.

## Run the web app locally

The repository has a Next.js frontend and a FastAPI backend. Start each from a separate terminal at the repository root.

```powershell
# Terminal 1: API
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2: web app
Copy-Item frontend/.env.local.example frontend/.env.local
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The supplied environment file points the frontend to `http://localhost:8000`; change `NEXT_PUBLIC_API_URL` for a deployed API.

## Run a scan-to-plan demo

For an InBody image, install the optional OCR dependencies and provide an OpenAI key for AI-assisted plan wording:

```powershell
pip install -e ".[training]"
$env:OPENAI_API_KEY = "sk-..."     # macOS/Linux: export OPENAI_API_KEY=sk-...
python scripts/demo_pipeline.py path/to/inbody_sheet.jpg --age 30 --sex female --activity 1.55 --goal fat_loss
```

By default the image is read with the local Donut engine. Set `INFORM_DONUT_CKPT` when its checkpoint is not at `models/donut-both-v3`. Alternatively, pass `--engine vlm` to use a vision-language model. If plan synthesis is unavailable or violates the validation rules, InForm returns its deterministic fallback plan.

## Project layout

| Path | Purpose |
| --- | --- |
| `src/inform/` | Deterministic domain logic, data contracts, OCR seam, and plan synthesis |
| `backend/` | FastAPI service for plans, reads, and samples |
| `frontend/` | Next.js user interface for onboarding, scan upload, profile input, and results |
| `tests/` | Unit and integration tests |
| `docs/adr/` | Architectural decisions |
| `CONTEXT.md` | Authoritative domain vocabulary and pipeline rules |

## Design principles

1. **Deterministic plan facts.** Measurements, targets, exercises, and imbalance findings always come from code.
2. **Generative AI is bounded.** It supplies an optional coaching voice, never new medical or training claims.
3. **Fail closed.** When OCR data is incomplete or generated content fails validation, the system does not silently invent a result.
4. **Explainability first.** Structured nutrition and exercise outputs are returned alongside any prose so the UI can render the audited values directly.

## Learn more

- [Domain context and terminology](CONTEXT.md)
- [Architecture decisions](docs/adr/)
- [Backend API guide](backend/README.md)
- [OCR evaluation notes](docs/ocr-eval-results.md)

## Contributing

Run `pytest -q` before opening a pull request. Keep domain terminology consistent with [CONTEXT.md](CONTEXT.md), and record consequential architectural choices in `docs/adr/`.
