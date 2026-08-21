"""Head-to-head: score the Donut engine against the VLM baseline on the same
labeled set, through the full extract_inbody seam (cross-check gate included),
per ADR-0002 / ADR-0006. This is the accuracy comparison the paper reports.

    python -m cera.compare --data-dir <held-out> --donut-checkpoint <ckpt>

Run once per ground-truth source (synthetic, real hold-out) and report each
separately — the synthetic->real gap is the honest number (ADR-0006).
"""
import argparse
from functools import partial
from pathlib import Path

from cera.engines import donut, vlm
from cera.evaluate import AccuracyReport, evaluate, load_labeled_set
from cera.extract import Engine, extract_inbody


def compare(engines: dict[str, Engine], data_dir: Path) -> dict[str, AccuracyReport]:
    """Score each named engine on the same held-out set, through the seam so
    the cross-check gate applies to every engine identically (ADR-0008)."""
    labeled_set = load_labeled_set(data_dir)
    return {
        name: evaluate(partial(extract_inbody, engine=engine), labeled_set)
        for name, engine in engines.items()
    }


def _format(reports: dict[str, AccuracyReport]) -> str:
    names = list(reports)
    fields = list(next(iter(reports.values())).per_field_accuracy)
    width = max(len(f) for f in fields + ["critical (mean)"]) + 2
    header = "field".ljust(width) + "".join(n.rjust(12) for n in names)
    lines = [header, "-" * len(header)]
    for field in fields:
        row = field.ljust(width)
        row += "".join(f"{reports[n].per_field_accuracy[field]:11.1%} " for n in names)
        lines.append(row.rstrip())
    lines.append("-" * len(header))

    def _mean(report: AccuracyReport) -> float:
        cut = report.critical_field_accuracy
        return sum(cut.values()) / len(cut) if cut else 0.0

    critical = "critical (mean)".ljust(width)
    critical += "".join(f"{_mean(reports[n]):11.1%} " for n in names)
    lines.append(critical.rstrip())
    whole = "whole_sheet".ljust(width)
    whole += "".join(f"{reports[n].whole_sheet_accuracy:11.1%} " for n in names)
    lines.append(whole.rstrip())
    return "\n".join(lines)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Compare Donut vs VLM on a labeled set.")
    parser.add_argument("--data-dir", type=Path, required=True, help="Held-out png/json pairs")
    parser.add_argument("--donut-checkpoint", type=Path, required=True)
    parser.add_argument(
        "--skip-vlm", action="store_true", help="Score Donut only (no OpenAI calls)"
    )
    args = parser.parse_args()

    engines: dict[str, Engine] = {"donut": donut.load_engine(args.donut_checkpoint)}
    if not args.skip_vlm:
        engines["vlm"] = vlm.extract

    reports = compare(engines, args.data_dir)
    print(_format(reports))


if __name__ == "__main__":
    _main()
