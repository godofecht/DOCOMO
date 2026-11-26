"""Scrutinize a model amendment by recomputing all actual project benchmarks."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .project_benchmarks import evaluate_legacy_corpus
from .project_corpus import load_project_corpus
from .forward_years import evaluate_all_forward
from .scrutiny import open_json, scrutinize_amendment


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docomo-scrutiny",
        description="Challenge a registered DOCOMO amendment across all four real project effort datasets",
    )
    parser.add_argument("--proposal", type=Path, default=Path("catalog/driver_amendment.json"))
    parser.add_argument("--registry", type=Path, default=Path("catalog/evidence_registry.json"))
    parser.add_argument("--dataset-dir", type=Path, default=Path(".docomo-cache"))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        corpus = load_project_corpus(args.dataset_dir, offline=args.offline)
        benchmark = evaluate_legacy_corpus(corpus)
        report = {
            "source_data": {key:value for key,value in corpus.items() if key != "records"},
            "evaluations": benchmark,
            "strict_forward_year_validation": evaluate_all_forward(corpus),
            "calibration_status": "historical_real_effort_retrospective_not_ai_native",
        }
        review = scrutinize_amendment(open_json(args.proposal), report, open_json(args.registry))
        result = json.dumps(review, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
    except (OSError, ValueError, OverflowError) as error:
        print(f"docomo-scrutiny: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
