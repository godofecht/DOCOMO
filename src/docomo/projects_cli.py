"""Retrieve all source-pinned historical project observations and evaluate them.

The output distinguishes observed project-level human effort from AI tasks and
repository issue acceptance. No historical person-month is turned into an
AI productivity multiplier or compared directly to person-hour labels.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .project_benchmarks import evaluate_legacy_corpus
from .project_corpus import load_project_corpus
from .forward_years import evaluate_all_forward


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="docomo-projects",
                                description="Source-pinned real completed-project corpus and retrospective benchmarks")
    p.add_argument("--dataset-dir", type=Path, default=Path(".docomo-cache"))
    p.add_argument("--offline", action="store_true")
    p.add_argument("--output", type=Path,
                   help="Compact JSON summary with held-out errors; defaults to stdout")
    p.add_argument("--records-output", type=Path,
                   help="Optionally write normalized real project-by-project records to a separate JSON file")
    args = p.parse_args(argv)
    try:
        corpus = load_project_corpus(args.dataset_dir, offline=args.offline)
        results = evaluate_legacy_corpus(corpus)
        summary = {
            "schema_version": "1.0",
            "source_data": {key:value for key,value in corpus.items() if key != "records"},
            "evaluations": results,
            "strict_forward_year_validation": evaluate_all_forward(corpus),
            "calibration_status": "historical_real_effort_retrospective_not_ai_native",
            "cannot_claim": [
                "unique independent project count across datasets",
                "prospectively accepted AI-native project costs",
                "causal AI productivity coefficient",
                "shared effort unit across person-month and person-hour cohorts",
                "generalised model upgrade from historical exploratory backtests",
            ],
        }
        encoded = json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
        if args.records_output:
            args.records_output.parent.mkdir(parents=True, exist_ok=True)
            args.records_output.write_text(
                json.dumps(corpus, indent=2, sort_keys=True, allow_nan=False) + "\n",
                encoding="utf-8")
    except (OSError, ValueError, OverflowError) as error:
        print(f"docomo-projects: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
