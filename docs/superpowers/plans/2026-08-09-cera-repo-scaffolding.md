# CERA Repo Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the CERA Python backend — package skeleton, Pydantic JSON contracts, stubbed module interfaces, domain docs, and tooling — so each pipeline module can later be implemented in isolation.

**Architecture:** Backend-only Python `src/` layout. `src/cera/` holds one subpackage per pipeline stage (`ocr`, `nutrition`, `recommender`, `synthesis`) plus a central `schemas/` package that defines the JSON contracts between stages and a top-level `pipeline.py` orchestrator. Every module entry function has a typed signature and a docstring describing the paper's intended logic, but raises `NotImplementedError`. The Pydantic schemas are the real deliverable — they lock the inter-module boundaries.

**Tech Stack:** Python ≥3.11, Pydantic v2, OpenAI SDK. Optional `ocr` extra (torch + transformers). Dev tooling: pytest, ruff. Hatchling build backend.

**Note on TDD:** This is scaffolding — bodies are stubs and `tests/` stays empty per the spec (§9). The classic red-green rhythm does not apply. Each task instead follows **create files → smoke-check (`python -c` import/instantiation) → commit**. The smoke-check is the verification gate.

**Spec:** `docs/superpowers/specs/2026-08-09-cera-repo-scaffolding-design.md`

---

## File Structure

Created by this plan (all paths relative to repo root `C:\Users\sukse\CERA`):

| Path | Responsibility |
| ---- | -------------- |
| `pyproject.toml` | Project metadata, deps, ruff/pytest config, hatchling build |
| `.gitignore` | Python ignores |
| `.env.example` | Documents required env vars (`OPENAI_API_KEY`) |
| `src/cera/__init__.py` | Package root, `__version__`, module overview |
| `src/cera/schemas/__init__.py` | Re-exports all contracts |
| `src/cera/schemas/user.py` | `UserProfile` (onboarding form) |
| `src/cera/schemas/inbody.py` | `InBodyPayload`, `SegmentalLean` (Module 1 output) |
| `src/cera/schemas/nutrition.py` | `NutritionTargets` (Module 2 output) |
| `src/cera/schemas/exercise.py` | `Exercise`, `ExercisePlan`, `MovementType` (Module 3 output) |
| `src/cera/schemas/master.py` | `MasterPayload` (Module 4 input), `DailyPlan` (final output) |
| `src/cera/ocr/__init__.py` + `extract.py` | Module 1 stub `extract_inbody` |
| `src/cera/nutrition/__init__.py` + `engine.py` + `constants.py` | Module 2 stub `compute_targets` + Katch-McArdle constants |
| `src/cera/recommender/__init__.py` + `filter.py` + `constants.py` | Module 3 stub `recommend_exercises` + asymmetry threshold |
| `src/cera/synthesis/__init__.py` + `generate.py` + `validate.py` | Module 4 stubs `synthesize_plan`, `validate_no_mutation` |
| `src/cera/pipeline.py` | Orchestrator stub `run_pipeline` |
| `tests/__init__.py` | Empty test tree, ready for later |
| `CONTEXT.md` | Domain glossary (ubiquitous language) |
| `docs/adr/0001-katch-mcardle-over-mifflin.md` | Records the formula decision |
| `data/README.md` | Documents dataset + synthetic-gen plan (no data committed) |
| `README.md` | Expanded project overview + layout + quickstart (modify) |

---

## Task 1: Project metadata & hygiene files

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "cera"
version = "0.1.0"
description = "InBody AI Fitness Assistant — deterministic multimodal pipeline for nutritional and corrective exercise planning"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "openai>=1.0",
]

[project.optional-dependencies]
ocr = [
    "torch>=2.0",
    "transformers>=4.40",
]
dev = [
    "pytest>=8.0",
    "ruff>=0.5",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/cera"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
build/
dist/
.venv/
venv/
env/

# Tooling
.pytest_cache/
.ruff_cache/
.mypy_cache/

# Environment
.env

# OS / editor
.DS_Store
.idea/
.vscode/
```

- [ ] **Step 3: Create `.env.example`**

```dotenv
# Copy to .env and fill in. Required by Module 4 (LLM synthesis).
OPENAI_API_KEY=your-api-key-here
```

- [ ] **Step 4: Install the package (dev extras) to verify metadata is valid**

Run: `pip install -e ".[dev]"`
Expected: installs pydantic, openai, pytest, ruff and `cera` (editable) with no error. (Does NOT pull torch — that is the separate `ocr` extra.)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore .env.example
git commit -m "chore: add project metadata and hygiene files"
```

---

## Task 2: Package skeleton (all `__init__.py` + empty test tree)

**Files:**
- Create: `src/cera/__init__.py`
- Create: `src/cera/schemas/__init__.py` (placeholder for now; filled in Task 3)
- Create: `src/cera/ocr/__init__.py`
- Create: `src/cera/nutrition/__init__.py`
- Create: `src/cera/recommender/__init__.py`
- Create: `src/cera/synthesis/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `src/cera/__init__.py`**

```python
"""CERA — InBody AI Fitness Assistant.

A deterministic, four-stage multimodal pipeline:
    1. OCR (Donut) — extract InBody biometrics into structured JSON.
    2. Nutrition engine — Katch-McArdle macronutrient targets from Lean Body Mass.
    3. Exercise recommender — constraint-based corrective movement selection.
    4. LLM synthesis — zero-shot linguistic synthesis of the deterministic outputs.

Deterministic medical/caloric logic is kept out of the generative module to
minimize hallucination risk.
"""

__version__ = "0.1.0"
```

- [ ] **Step 2: Create the subpackage `__init__.py` files**

`src/cera/schemas/__init__.py` (temporary — replaced in Task 3):

```python
"""Pydantic contracts — the JSON boundaries between pipeline stages."""
```

`src/cera/ocr/__init__.py`:

```python
"""Module 1 — visual extraction (Donut OCR)."""
```

`src/cera/nutrition/__init__.py`:

```python
"""Module 2 — deterministic nutrition engine (Katch-McArdle)."""
```

`src/cera/recommender/__init__.py`:

```python
"""Module 3 — constraint-based exercise recommender."""
```

`src/cera/synthesis/__init__.py`:

```python
"""Module 4 — LLM synthesis and validation."""
```

- [ ] **Step 3: Create the empty test tree**

`tests/__init__.py`:

```python
```

(An empty file — the test tree exists but holds no tests yet, per spec §9.)

- [ ] **Step 4: Smoke-check the package imports**

Run: `python -c "import cera; print(cera.__version__)"`
Expected: prints `0.1.0`

- [ ] **Step 5: Commit**

```bash
git add src/cera tests
git commit -m "feat: add package skeleton and empty test tree"
```

---

## Task 3: Pydantic schema contracts

**Files:**
- Create: `src/cera/schemas/user.py`
- Create: `src/cera/schemas/inbody.py`
- Create: `src/cera/schemas/nutrition.py`
- Create: `src/cera/schemas/exercise.py`
- Create: `src/cera/schemas/master.py`
- Modify: `src/cera/schemas/__init__.py` (replace placeholder with re-exports)

- [ ] **Step 1: Create `src/cera/schemas/user.py`**

```python
"""User onboarding form — captured at the start of the pipeline."""

from typing import Literal

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """Baseline metrics captured by the onboarding form.

    Note on fields unused by the BMR calculation: the nutrition engine uses the
    Katch-McArdle formula, which derives BMR from Lean Body Mass alone. ``age``
    and ``biological_sex`` are therefore NOT inputs to the calorie calculation.
    They are retained for goal/activity context and a possible future
    Mifflin-St Jeor fallback. See docs/adr/0001-katch-mcardle-over-mifflin.md.
    """

    age: int = Field(..., ge=0, description="Age in years. Not used by Katch-McArdle BMR.")
    biological_sex: Literal["male", "female"] = Field(
        ..., description="Biological sex. Not used by Katch-McArdle BMR."
    )
    activity_multiplier: float = Field(
        ...,
        ge=1.0,
        le=2.5,
        description="TDEE = BMR x this. E.g. 1.2 sedentary ... 1.9 very active.",
    )
    fitness_goal: Literal["hypertrophy", "fat_loss"] = Field(
        ..., description="Drives macro split and exercise selection."
    )
```

- [ ] **Step 2: Create `src/cera/schemas/inbody.py`**

```python
"""InBody extraction payload — the structured output of Module 1 (Donut OCR)."""

from pydantic import BaseModel, Field


class SegmentalLean(BaseModel):
    """Segmental Lean Analysis — per-limb lean mass, basis for asymmetry detection."""

    left_arm_kg: float = Field(..., ge=0)
    right_arm_kg: float = Field(..., ge=0)
    left_leg_kg: float = Field(..., ge=0)
    right_leg_kg: float = Field(..., ge=0)
    trunk_kg: float = Field(..., ge=0)


class InBodyPayload(BaseModel):
    """Biometric matrix extracted from an InBody report image.

    ``lean_body_mass_kg`` is the authoritative input to Katch-McArdle. It is
    distinct from ``skeletal_muscle_mass_kg`` (SMM): LBM is all fat-free mass,
    SMM counts skeletal muscle only. ``basal_metabolic_rate_kcal`` is the
    device-reported BMR, kept as a cross-check only — the nutrition engine
    recomputes BMR via Katch-McArdle for determinism.
    """

    weight_kg: float = Field(..., ge=0)
    lean_body_mass_kg: float = Field(
        ..., ge=0, description="LBM — authoritative for Katch-McArdle."
    )
    skeletal_muscle_mass_kg: float = Field(
        ..., ge=0, description="SMM — distinct from LBM."
    )
    percent_body_fat: float = Field(..., ge=0, le=100, description="PBF, percent.")
    basal_metabolic_rate_kcal: float = Field(
        ..., ge=0, description="Device-reported BMR. Cross-check only, not authoritative."
    )
    visceral_fat_level: int = Field(..., ge=0)
    segmental_lean: SegmentalLean
```

- [ ] **Step 3: Create `src/cera/schemas/nutrition.py`**

```python
"""Deterministic nutrition targets — the output of Module 2."""

from pydantic import BaseModel, Field


class NutritionTargets(BaseModel):
    """Exact caloric and macronutrient targets.

    ``bmr_kcal`` is computed via Katch-McArdle (``370 + 21.6 * LBM_kg``);
    ``tdee_kcal`` applies the activity multiplier; ``target_calories_kcal``
    applies the fitness-goal adjustment.
    """

    bmr_kcal: float = Field(..., ge=0, description="Katch-McArdle BMR.")
    tdee_kcal: float = Field(..., ge=0, description="BMR x activity_multiplier.")
    target_calories_kcal: float = Field(..., ge=0, description="TDEE adjusted for goal.")
    protein_g: float = Field(..., ge=0)
    carbs_g: float = Field(..., ge=0)
    fats_g: float = Field(..., ge=0)
    fiber_g: float = Field(..., ge=0)
```

- [ ] **Step 4: Create `src/cera/schemas/exercise.py`**

```python
"""Exercise recommendation output — the output of Module 3."""

from typing import Literal

from pydantic import BaseModel, Field

MovementType = Literal["corrective_unilateral", "bilateral_compound", "cardio_hiit"]


class Exercise(BaseModel):
    """A single recommended movement.

    Field names mirror the hasaneyldrm/exercises-dataset taxonomy
    (target, bodyPart, equipment, secondaryMuscles).
    """

    name: str
    target: str = Field(..., description="Primary target muscle.")
    body_part: str
    equipment: str
    secondary_muscles: list[str] = Field(default_factory=list)
    movement_type: MovementType


class ExercisePlan(BaseModel):
    """Recommended movements plus the imbalances that justified them."""

    exercises: list[Exercise] = Field(default_factory=list)
    detected_imbalances: list[str] = Field(
        default_factory=list,
        description="Human-readable, e.g. 'L/R leg SMM deviation 7%'.",
    )
```

- [ ] **Step 5: Create `src/cera/schemas/master.py`**

```python
"""Master JSON contract and the final daily plan."""

from pydantic import BaseModel, Field

from cera.schemas.exercise import ExercisePlan
from cera.schemas.inbody import InBodyPayload
from cera.schemas.nutrition import NutritionTargets
from cera.schemas.user import UserProfile


class MasterPayload(BaseModel):
    """Consolidated deterministic output — the sole input to Module 4."""

    user: UserProfile
    inbody: InBodyPayload
    nutrition: NutritionTargets
    exercises: ExercisePlan


class DailyPlan(BaseModel):
    """Final synthesized plan.

    ``narrative_text`` is the LLM's linguistic output. The echoed deterministic
    fields let ``synthesis.validate.validate_no_mutation`` confirm the LLM did
    not alter any number from Module 2.
    """

    narrative_text: str
    target_calories_kcal: float = Field(..., ge=0)
    protein_g: float = Field(..., ge=0)
    carbs_g: float = Field(..., ge=0)
    fats_g: float = Field(..., ge=0)
    fiber_g: float = Field(..., ge=0)
```

- [ ] **Step 6: Replace `src/cera/schemas/__init__.py` with re-exports**

```python
"""Pydantic contracts — the JSON boundaries between pipeline stages."""

from cera.schemas.exercise import Exercise, ExercisePlan, MovementType
from cera.schemas.inbody import InBodyPayload, SegmentalLean
from cera.schemas.master import DailyPlan, MasterPayload
from cera.schemas.nutrition import NutritionTargets
from cera.schemas.user import UserProfile

__all__ = [
    "UserProfile",
    "InBodyPayload",
    "SegmentalLean",
    "NutritionTargets",
    "Exercise",
    "ExercisePlan",
    "MovementType",
    "MasterPayload",
    "DailyPlan",
]
```

- [ ] **Step 7: Smoke-check that every schema imports and instantiates**

Run:
```bash
python -c "
from cera.schemas import (
    UserProfile, InBodyPayload, SegmentalLean, NutritionTargets,
    Exercise, ExercisePlan, MasterPayload, DailyPlan,
)
seg = SegmentalLean(left_arm_kg=3, right_arm_kg=3, left_leg_kg=9, right_leg_kg=9, trunk_kg=25)
ib = InBodyPayload(weight_kg=70, lean_body_mass_kg=55, skeletal_muscle_mass_kg=32,
                   percent_body_fat=21, basal_metabolic_rate_kcal=1550,
                   visceral_fat_level=7, segmental_lean=seg)
u = UserProfile(age=28, biological_sex='male', activity_multiplier=1.4, fitness_goal='hypertrophy')
n = NutritionTargets(bmr_kcal=1558, tdee_kcal=2181, target_calories_kcal=2400,
                     protein_g=170, carbs_g=250, fats_g=70, fiber_g=30)
ep = ExercisePlan(exercises=[Exercise(name='Bulgarian Split Squat', target='quads',
                  body_part='upper legs', equipment='dumbbell',
                  secondary_muscles=['glutes'], movement_type='corrective_unilateral')],
                  detected_imbalances=['L/R leg SMM deviation 7%'])
m = MasterPayload(user=u, inbody=ib, nutrition=n, exercises=ep)
print('schemas OK', m.model_dump_json()[:40])
"
```
Expected: prints `schemas OK {...` with no validation error.

- [ ] **Step 8: Commit**

```bash
git add src/cera/schemas
git commit -m "feat: add Pydantic schema contracts for the pipeline"
```

---

## Task 4: Stubbed module interfaces

**Files:**
- Create: `src/cera/ocr/extract.py`
- Create: `src/cera/nutrition/constants.py`
- Create: `src/cera/nutrition/engine.py`
- Create: `src/cera/recommender/constants.py`
- Create: `src/cera/recommender/filter.py`
- Create: `src/cera/synthesis/generate.py`
- Create: `src/cera/synthesis/validate.py`
- Create: `src/cera/pipeline.py`

- [ ] **Step 1: Create `src/cera/ocr/extract.py`**

```python
"""Module 1 — Visual extraction (Donut Document Understanding Transformer).

Maps an InBody report image directly to a structured payload, bypassing a
traditional OCR step. To be fine-tuned on ~5,000 synthetic InBody sheets
(InBody 270 / 570) with blur/rotation/lighting augmentation.
"""

from pathlib import Path

from cera.schemas.inbody import InBodyPayload


def extract_inbody(image_path: Path) -> InBodyPayload:
    """Extract the biometric matrix from an InBody report image.

    Intended logic: run the fine-tuned Donut model over the image and parse the
    generated token sequence into an ``InBodyPayload``.
    """
    raise NotImplementedError("Module 1 (Donut extraction) not yet implemented.")
```

- [ ] **Step 2: Create `src/cera/nutrition/constants.py`**

```python
"""Constants for the deterministic nutrition engine."""

# Katch-McArdle: BMR = KATCH_MCARDLE_BASE + KATCH_MCARDLE_LBM_COEFF * LBM_kg
KATCH_MCARDLE_BASE: float = 370.0
KATCH_MCARDLE_LBM_COEFF: float = 21.6
```

- [ ] **Step 3: Create `src/cera/nutrition/engine.py`**

```python
"""Module 2 — Deterministic nutrition engine (Katch-McArdle).

Computes BMR from Lean Body Mass, applies the activity multiplier for TDEE,
adjusts for the fitness goal, and distributes the caloric target into exact
macronutrient grams. Contains no generative logic.
"""

from cera.schemas.inbody import InBodyPayload
from cera.schemas.nutrition import NutritionTargets
from cera.schemas.user import UserProfile


def compute_targets(user: UserProfile, inbody: InBodyPayload) -> NutritionTargets:
    """Compute exact caloric and macronutrient targets.

    Intended logic:
        bmr = KATCH_MCARDLE_BASE + KATCH_MCARDLE_LBM_COEFF * inbody.lean_body_mass_kg
        tdee = bmr * user.activity_multiplier
        target = tdee adjusted for user.fitness_goal
        then deterministically split into protein/carbs/fats/fiber grams.
    """
    raise NotImplementedError("Module 2 (nutrition engine) not yet implemented.")
```

- [ ] **Step 4: Create `src/cera/recommender/constants.py`**

```python
"""Constants for the constraint-based exercise recommender."""

# Bilateral limb deviation above this fraction triggers corrective unilateral work.
BILATERAL_ASYMMETRY_THRESHOLD: float = 0.05  # 5%
```

- [ ] **Step 5: Create `src/cera/recommender/filter.py`**

```python
"""Module 3 — Deterministic constraint-based exercise filtering.

Detects muscle imbalances from Segmental Lean Analysis and queries the
hasaneyldrm/exercises-dataset taxonomy (target, bodyPart, equipment) with
exact-match Boolean logic to prioritize safe corrective movements. Goal-driven
adaptation modulates selection (hypertrophy -> bilateral compounds; fat loss +
high visceral fat -> more cardio/HIIT).
"""

from cera.schemas.exercise import ExercisePlan
from cera.schemas.inbody import InBodyPayload
from cera.schemas.user import UserProfile


def recommend_exercises(user: UserProfile, inbody: InBodyPayload) -> ExercisePlan:
    """Recommend corrective and goal-aligned exercises.

    Intended logic: compare each bilateral limb pair in
    ``inbody.segmental_lean``; where deviation exceeds
    ``BILATERAL_ASYMMETRY_THRESHOLD``, prioritize unilateral corrective
    movements, then fill the remainder per ``user.fitness_goal``.
    """
    raise NotImplementedError("Module 3 (exercise recommender) not yet implemented.")
```

- [ ] **Step 6: Create `src/cera/synthesis/generate.py`**

```python
"""Module 4 — Natural Language Generation interface.

Injects the Master JSON into a zero-shot LLM (OpenAI Structured Outputs) that
acts strictly as a linguistic synthesizer, producing an empathetic daily plan
without altering any deterministic number.
"""

from cera.schemas.master import DailyPlan, MasterPayload


def synthesize_plan(master: MasterPayload) -> DailyPlan:
    """Synthesize the human-readable daily plan from deterministic outputs.

    Intended logic: call the LLM with a strict JSON Schema, then hand the result
    to ``validate_no_mutation`` before returning.
    """
    raise NotImplementedError("Module 4 (LLM synthesis) not yet implemented.")
```

- [ ] **Step 7: Create `src/cera/synthesis/validate.py`**

```python
"""Module 4 — Backend validation guard against numerical mutation.

Second half of the dual-validation mechanism: after the API-level JSON Schema,
Pydantic-validate the LLM output and confirm it did not mutate any deterministic
number. On mutation, the caller drops the response and falls back to
deterministic template text.
"""

from cera.schemas.master import DailyPlan, MasterPayload


def validate_no_mutation(master: MasterPayload, plan: DailyPlan) -> DailyPlan:
    """Confirm the LLM preserved every deterministic figure.

    Intended logic: compare ``plan``'s calorie/macro fields against
    ``master.nutrition``; raise (or signal fallback) on any mismatch.
    """
    raise NotImplementedError("Module 4 validation not yet implemented.")
```

- [ ] **Step 8: Create `src/cera/pipeline.py`**

```python
"""End-to-end orchestration of the four-stage pipeline.

Runs Module 1, fuses the result with the user form, runs Modules 2 and 3
(independent), consolidates into the Master JSON, then runs Module 4.
"""

from pathlib import Path

from cera.nutrition.engine import compute_targets
from cera.ocr.extract import extract_inbody
from cera.recommender.filter import recommend_exercises
from cera.schemas.master import DailyPlan, MasterPayload
from cera.schemas.user import UserProfile
from cera.synthesis.generate import synthesize_plan


def run_pipeline(image_path: Path, user: UserProfile) -> DailyPlan:
    """Run the full pipeline from an InBody image + user form to a daily plan.

    Intended flow:
        inbody = extract_inbody(image_path)             # Module 1
        nutrition = compute_targets(user, inbody)       # Module 2 (independent)
        exercises = recommend_exercises(user, inbody)   # Module 3 (independent)
        master = MasterPayload(user=user, inbody=inbody,
                               nutrition=nutrition, exercises=exercises)
        return synthesize_plan(master)                  # Module 4
    """
    raise NotImplementedError("Pipeline orchestration not yet implemented.")
```

- [ ] **Step 9: Smoke-check that every stub imports and raises `NotImplementedError`**

Run:
```bash
python -c "
from pathlib import Path
import cera.ocr.extract as m1
import cera.nutrition.engine as m2
import cera.recommender.filter as m3
import cera.synthesis.generate as m4
import cera.synthesis.validate as m4v
import cera.pipeline as p
from cera.nutrition.constants import KATCH_MCARDLE_BASE, KATCH_MCARDLE_LBM_COEFF
from cera.recommender.constants import BILATERAL_ASYMMETRY_THRESHOLD

assert (KATCH_MCARDLE_BASE, KATCH_MCARDLE_LBM_COEFF) == (370.0, 21.6)
assert BILATERAL_ASYMMETRY_THRESHOLD == 0.05

for fn, args in [
    (m1.extract_inbody, (Path('x'),)),
    (p.run_pipeline, (Path('x'), None)),
]:
    try:
        fn(*args)
    except NotImplementedError:
        pass
    else:
        raise SystemExit(f'{fn.__name__} did not raise NotImplementedError')
print('stubs OK')
"
```
Expected: prints `stubs OK` with no assertion error.

- [ ] **Step 10: Commit**

```bash
git add src/cera
git commit -m "feat: add stubbed module interfaces and constants"
```

---

## Task 5: Domain docs (CONTEXT.md, ADR, data README, README)

**Files:**
- Create: `CONTEXT.md`
- Create: `docs/adr/0001-katch-mcardle-over-mifflin.md`
- Create: `data/README.md`
- Modify: `README.md` (replace the single-line placeholder)

- [ ] **Step 1: Create `CONTEXT.md`**

```markdown
# CERA — Domain Context

The ubiquitous language for the InBody AI Fitness Assistant. Use these terms exactly
in code, schemas, issues, and tests. Where two terms are easily confused, the
distinction is called out — do not treat them as synonyms.

## Core pipeline

- **Pipeline** — the four-stage deterministic flow: OCR -> nutrition -> recommender ->
  synthesis. Deterministic logic stays in human-interpretable control; generation is
  confined to linguistic tasks.
- **Deterministic-vs-generative boundary** — the design's central rule. Modules 1-3
  and all medical/caloric math are deterministic. Module 4 (LLM) may only rephrase,
  never recompute. Enforced by validation.
- **Master JSON / MasterPayload** — the consolidated deterministic output (user +
  InBody + nutrition + exercises) that is the sole input to Module 4.

## Body composition

- **LBM — Lean Body Mass** — total fat-free mass (kg). The authoritative input to the
  Katch-McArdle BMR formula.
- **SMM — Skeletal Muscle Mass** — skeletal muscle only (kg). A subset of LBM.
  **SMM != LBM** — never substitute one for the other.
- **PBF — Percent Body Fat** — body fat as a percentage of weight. Lets LBM be
  cross-checked as `weight * (1 - PBF/100)`.
- **Visceral Fat Level** — InBody's ordinal visceral-fat rating. High values raise
  cardio/HIIT frequency for fat-loss goals.
- **Segmental Lean Analysis** — per-limb lean mass (both arms, both legs, trunk). The
  basis for bilateral-asymmetry detection.
- **Bilateral asymmetry** — a left/right deviation in a limb pair. Above the threshold
  (>5%) it triggers targeted unilateral corrective movements.

## Nutrition

- **BMR — Basal Metabolic Rate** — resting energy expenditure. Computed here via
  Katch-McArdle from LBM. The InBody device also reports a BMR; that value is a
  cross-check only, not authoritative.
- **Katch-McArdle formula** — `BMR = 370 + 21.6 * LBM_kg`. The authoritative BMR
  method for this system. See ADR-0001 for why, over Mifflin-St Jeor.
- **TDEE — Total Daily Energy Expenditure** — `BMR * activity_multiplier`.
- **Activity multiplier** — the sedentary-to-active scalar applied to BMR for TDEE.
- **Fitness goal** — `hypertrophy` or `fat_loss`. Drives both the macro split and
  exercise selection.

## Exercise recommendation

- **Constraint-based filtering** — deterministic Boolean/exact-match querying over the
  exercise dataset. Deliberately not vector/embedding similarity (hallucination risk).
- **Exercises dataset** — the open-source hasaneyldrm/exercises-dataset, keyed by
  `target`, `bodyPart`, `equipment`, `secondaryMuscles`.
- **Corrective unilateral movement** — a single-limb exercise (e.g. Bulgarian Split
  Squat) prescribed to correct a detected bilateral asymmetry.
```

- [ ] **Step 2: Create `docs/adr/0001-katch-mcardle-over-mifflin.md`**

```markdown
# ADR-0001: Katch-McArdle is the authoritative BMR formula (over Mifflin-St Jeor)

**Status:** Accepted
**Date:** 2026-08-09

## Context

The concept paper is internally inconsistent about the nutrition formula. The
abstract, section 3.1.2 (Deterministic Nutritional Engine), and section 3.3 (Modeling
Approach) all specify the **Katch-McArdle** formula, which derives BMR from Lean Body
Mass. But section 2.1.1 (Literature Review) states that nutritional requirements are
calculated using the **Mifflin-St Jeor** equation, which derives BMR from weight,
height, age, and sex. These are different formulas and cannot both be the
implementation.

## Decision

**Katch-McArdle is authoritative:** `BMR = 370 + 21.6 * LBM_kg`.

Rationale:
- It is the paper's stated differentiator — using InBody-derived LBM rather than
  generic total weight is the whole premise (abstract, section 3.1.2).
- It appears in three of the four relevant sections; Mifflin-St Jeor appears once, in
  the literature review.

## Consequences

- The `UserProfile` fields `age` and `biological_sex` are **not** inputs to the BMR
  calculation. They are retained for goal/activity context and a possible future
  Mifflin-St Jeor fallback, which would need them.
- The InBody-reported BMR (`InBodyPayload.basal_metabolic_rate_kcal`) is a cross-check
  only; the engine recomputes BMR via Katch-McArdle for determinism.
```

- [ ] **Step 3: Create `data/README.md`**

```markdown
# Data

This directory holds datasets and data-generation scripts for the pipeline. No data is
committed yet — this file records the plan.

## Exercise dataset (Module 3)

The recommender is grounded in the open-source **hasaneyldrm/exercises-dataset**
(https://github.com/hasaneyldrm/exercises-dataset). A JSON taxonomy keyed by `target`,
`bodyPart`, `equipment`, and `secondaryMuscles`. To be vendored here or fetched at
build time (decision deferred to Module 3 implementation).

## Synthetic InBody sheets (Module 1)

Real InBody sheets are unavailable due to health-privacy constraints. Module 1 will
train on ~5,000 synthetic sheets, evenly split between InBody 270 and InBody 570
layouts (2,500 each), with randomized values/dates and augmentation (Gaussian blur,
lighting gradients, spatial distortion). The generator script will live here.

## Nutrition standards (Module 2)

No training data — Module 2 is deterministic (Katch-McArdle). A future food-level
feature may integrate the USDA FoodData Central database.
```

- [ ] **Step 4: Replace `README.md`**

```markdown
# CERA — InBody AI Fitness Assistant

A hyper-personalized, multimodal AI system that turns an InBody body-composition
report into a precise, safe daily fitness plan. Deterministic medical and caloric
logic is deliberately decoupled from the generative layer to minimize hallucination
risk.

## Pipeline

1. **OCR (Donut)** — extract InBody biometrics from a report image into structured JSON.
2. **Nutrition engine** — Katch-McArdle macronutrient targets from Lean Body Mass.
3. **Exercise recommender** — constraint-based corrective movement selection.
4. **LLM synthesis** — zero-shot linguistic synthesis of the deterministic outputs,
   guarded so it never mutates a number.

## Layout

```
src/cera/
├── schemas/       # Pydantic JSON contracts between stages
├── ocr/           # Module 1 — Donut extraction
├── nutrition/     # Module 2 — Katch-McArdle engine
├── recommender/   # Module 3 — constraint-based filter
├── synthesis/     # Module 4 — LLM synthesis + validation
└── pipeline.py    # orchestration
```

Domain vocabulary lives in `CONTEXT.md`; decisions in `docs/adr/`.

## Status

Scaffolding only — module bodies are stubs (`NotImplementedError`). See
`docs/superpowers/plans/` for the implementation plan.

## Development

```bash
pip install -e ".[dev]"   # core + pytest + ruff (no torch)
pip install -e ".[ocr]"   # add torch + transformers for Module 1
ruff check .
```

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` for Module 4.
```

- [ ] **Step 5: Verify the docs files exist and are non-empty**

Run: `ls -la CONTEXT.md docs/adr/0001-katch-mcardle-over-mifflin.md data/README.md README.md`
Expected: all four listed with non-zero size.

- [ ] **Step 6: Commit**

```bash
git add CONTEXT.md docs/adr data/README.md README.md
git commit -m "docs: add domain glossary, ADR-0001, data plan, and README"
```

---

## Task 6: Final verification and push

**Files:** none (verification + push only)

- [ ] **Step 1: Lint the whole package**

Run: `ruff check .`
Expected: `All checks passed!` (fix any reported issue, then re-run until clean).

- [ ] **Step 2: Full import smoke test**

Run:
```bash
python -c "
import cera
import cera.pipeline
from cera.schemas import MasterPayload, DailyPlan
from cera.nutrition.constants import KATCH_MCARDLE_BASE
from cera.recommender.constants import BILATERAL_ASYMMETRY_THRESHOLD
print('import smoke OK', cera.__version__)
"
```
Expected: prints `import smoke OK 0.1.0`

- [ ] **Step 3: Confirm working tree is clean and review the log**

Run: `git status --short && git log --oneline -7`
Expected: no uncommitted changes; the five task commits plus prior history visible.

- [ ] **Step 4: Push to origin**

Run: `git push origin main`
Expected: refs updated on `github.com/QeekOw/CERA`.

---

## Self-Review

**Spec coverage** (against `2026-08-09-cera-repo-scaffolding-design.md`):
- §3 folder structure → Tasks 1, 2, 4, 5 create every listed path (incl. `recommender/constants.py`). ✓
- §4 module seams → Task 4 (all five entry functions + orchestrator). ✓
- §5 schemas → Task 3 (all five schema files + re-exports). ✓
- §6 deterministic rules → encoded as constants (Tasks 4) + stub docstrings + CONTEXT/ADR (Task 5). ✓
- §7 domain docs → Task 5 (CONTEXT.md + ADR-0001, SMM/LBM + formula distinctions). ✓
- §8 dependencies → Task 1 (`pyproject.toml`, optional `ocr`, dev group). ✓
- §9 out-of-scope → honored: all bodies raise `NotImplementedError`; `tests/` empty; no frontend; `data/README.md` documents-only. ✓

**Placeholder scan:** No "TBD"/"handle edge cases"/"write tests for the above" — every code step shows complete file content. ✓

**Type consistency:** Names used across tasks match — `InBodyPayload.lean_body_mass_kg`, `NutritionTargets` (bmr/tdee/target + 4 macros), `MasterPayload(user, inbody, nutrition, exercises)`, `DailyPlan.narrative_text` + echoed macros, `MovementType` literals, `KATCH_MCARDLE_BASE`/`_LBM_COEFF`, `BILATERAL_ASYMMETRY_THRESHOLD`. The Task 3 Step 7 and Task 4 Step 9 smoke-checks exercise these exact signatures. ✓
