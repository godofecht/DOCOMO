"""Research calibration command. Never emits an unqualified general-purpose AI multiplier."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .calibration import calibrate_ai_tasks, calibrate_projects, read_cocomo81, read_metr_early
from .datasets import fetch_dataset, provenance
from .hie import read_hie_tasks, benchmark_hie_tasks


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Calibrate and evaluate isolated historical/project and AI/task models')
    parser.add_argument('--dataset-dir', type=Path, default=Path('.docomo-cache'))
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--output', type=Path, help='Write JSON report to a file (defaults to stdout)')
    parser.add_argument('--bootstrap', type=int, default=400)
    args = parser.parse_args(argv)
    try:
        cocomo = fetch_dataset('cocomo81', args.dataset_dir, args.offline)
        metr = fetch_dataset('metr_early', args.dataset_dir, args.offline)
        hie = fetch_dataset('hie_tasks', args.dataset_dir, args.offline)
        result = {
            'schema_version': '1.0',
            'calibration_status': 'partial_domain_specific',
            'provenance': provenance(),
            'historical_effort': calibrate_projects(read_cocomo81(cocomo)),
            'early_ai_task_time': calibrate_ai_tasks(read_metr_early(metr), replicates=args.bootstrap),
            'hie_task_process_diagnostics': benchmark_hie_tasks(read_hie_tasks(hie)),
            'cannot_claim': ['AI-native project effort calibration', 'universal AI speed multiplier',
                             'modern COCOMO II validation', 'independently verified task acceptance',
                             'calibrated grounding probabilities or value weights'],
        }
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding='utf-8')
        else:
            print(encoded, end='')
    except (OSError, ValueError) as exc:
        print(f'docomo-calibrate: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
