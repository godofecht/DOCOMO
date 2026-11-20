"""Forecast only within domains of a documented calibration report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .forecast import forecast


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Domain-scoped DOCOMO point forecast')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding='utf-8'))
        spec = json.loads(args.input.read_text(encoding='utf-8'))
        result = forecast(report, spec)
    except (ValueError, OSError, TypeError) as exc:
        print(f'docomo-forecast: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
