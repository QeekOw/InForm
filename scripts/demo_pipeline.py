#!/usr/bin/env python3
"""Run the pipeline end-to-end: InBody image -> DailyPlan (with LLM synthesis).

Reads the sheet with the default self-hosted Donut engine (ADR-0010); pass
`--engine vlm` to use the cloud VLM instead. LLM synthesis always needs
OPENAI_API_KEY (it falls back to the deterministic plan if the key is missing
or synthesis fails). Donut needs a checkpoint (INFORM_DONUT_CKPT, default
models/donut-both-v3) and the training extra.

Usage:
    python scripts/demo_pipeline.py path/to/inbody_sheet.jpg \
        --age 30 --sex female --activity 1.55 --goal fat_loss [--engine donut|vlm]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from inform.errors import InBodyExtractionError, IncompleteExtractionError  # noqa: E402
from inform.exercise_pool import DEFAULT_EXERCISE_POOL  # noqa: E402
from inform.pipeline import assemble_master_payload, run_pipeline  # noqa: E402
from inform.user import UserProfile  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Path to an InBody 270/570 sheet photo")
    parser.add_argument("--age", type=int, default=30)
    parser.add_argument("--sex", choices=["male", "female"], default="female")
    parser.add_argument("--activity", type=float, default=1.55, help="Activity multiplier")
    parser.add_argument("--goal", choices=["hypertrophy", "fat_loss"], default="fat_loss")
    parser.add_argument(
        "--engine",
        choices=["donut", "vlm"],
        default="donut",
        help="OCR engine: self-hosted Donut (default) or the cloud VLM oracle",
    )
    args = parser.parse_args()

    user = UserProfile(
        age=args.age,
        biological_sex=args.sex,
        activity_multiplier=args.activity,
        fitness_goal=args.goal,
    )

    # None lets extract_inbody resolve the default Donut engine (ADR-0010).
    engine = None
    if args.engine == "vlm":
        from inform.engines import vlm

        engine = vlm.extract

    try:
        master = assemble_master_payload(args.image, user, DEFAULT_EXERCISE_POOL, engine=engine)
        daily_plan = run_pipeline(args.image, user, DEFAULT_EXERCISE_POOL, engine=engine)
    except IncompleteExtractionError as e:
        print(f"Extraction incomplete — cannot build a plan.\n  Unread: {e.unread}\n  Flagged: {e.flagged}")
        raise SystemExit(1)
    except InBodyExtractionError as e:
        print(f"Extraction rejected: {e}")
        raise SystemExit(1)

    print("=" * 60)
    print("MASTER PAYLOAD (Deterministic Consolidated Output)")
    print("=" * 60)
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
    print()
    print("=" * 60)
    print("SYNTHESIZED DAILY PLAN (Module 4)")
    print("=" * 60)
    print(daily_plan.narrative_text)


if __name__ == "__main__":
    main()
