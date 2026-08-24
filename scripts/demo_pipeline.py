#!/usr/bin/env python3
"""Run the pipeline end-to-end: InBody image -> MasterPayload.

Requires OPENAI_API_KEY (Module 1's VLM engine calls the real OpenAI API).
Module 4 (LLM synthesis) isn't wired into run_pipeline yet, so this prints
the deterministic MasterPayload — the daily-plan narrative isn't part of
this demo until that module lands.

Usage:
    python scripts/demo_pipeline.py path/to/inbody_sheet.jpg \\
        --age 30 --sex female --activity 1.55 --goal fat_loss
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from inform.errors import IncompleteExtractionError, InBodyExtractionError  # noqa: E402
from inform.exercise_pool import DEFAULT_EXERCISE_POOL  # noqa: E402
from inform.pipeline import run_pipeline  # noqa: E402
from inform.user import UserProfile  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to an InBody 270/570 sheet photo")
    parser.add_argument("--age", type=int, default=30)
    parser.add_argument("--sex", choices=["male", "female"], default="female")
    parser.add_argument("--activity", type=float, default=1.55, help="Activity multiplier")
    parser.add_argument("--goal", choices=["hypertrophy", "fat_loss"], default="fat_loss")
    args = parser.parse_args()

    user = UserProfile(
        age=args.age,
        biological_sex=args.sex,
        activity_multiplier=args.activity,
        fitness_goal=args.goal,
    )

    try:
        master = run_pipeline(args.image, user, DEFAULT_EXERCISE_POOL)
    except IncompleteExtractionError as e:
        print(f"Extraction incomplete — cannot build a plan.\n  Unread: {e.unread}\n  Flagged: {e.flagged}")
        raise SystemExit(1)
    except InBodyExtractionError as e:
        print(f"Extraction rejected: {e}")
        raise SystemExit(1)

    print(master.model_dump_json(indent=2))
    print()
    print(f"BMR: {master.nutrition.bmr_kcal:.0f} kcal  |  TDEE: {master.nutrition.tdee_kcal:.0f} kcal")
    print(
        f"Target: {master.nutrition.target_calories_kcal:.0f} kcal  "
        f"(P {master.nutrition.protein_g:.0f}g / C {master.nutrition.carbs_g:.0f}g / "
        f"F {master.nutrition.fats_g:.0f}g / Fiber {master.nutrition.fiber_g:.0f}g)"
    )
    if master.exercises.detected_imbalances:
        print("Detected imbalances:", ", ".join(master.exercises.detected_imbalances))
    print("Exercises:", ", ".join(ex.name for ex in master.exercises.exercises))


if __name__ == "__main__":
    main()
