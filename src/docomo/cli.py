"""Command line entry point for DOCOMO's auditable JSON assessments."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .complexity import assess_complexity
from .grounding import assess_grounding
from .cocomo2 import estimate_cocomo_ii
from .manifests import validate_project, assess_readiness

MODES = {
    'grounding': assess_grounding,
    'complexity': assess_complexity,
    'cocomo2': estimate_cocomo_ii,
    'manifest': validate_project,
    'readiness': assess_readiness,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='docomo', description='Evidence-grounded software complexity and effort estimation')
    parser.add_argument('mode', choices=tuple(MODES))
    parser.add_argument('input', type=Path, help='UTF-8 JSON assessment file')
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding='utf-8'))
        result = MODES[args.mode](payload)
    except (OSError, ValueError, json.JSONDecodeError, TypeError) as error:
        print(f'docomo: {error}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
