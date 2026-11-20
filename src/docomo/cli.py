"""Command line entry point for DOCOMO JSON assessments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .complexity import assess_complexity
from .grounding import assess_grounding


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docomo", description="Evaluate grounding and observed engineering effort")
    parser.add_argument("mode", choices=("grounding", "complexity"))
    parser.add_argument("input", type=Path, help="UTF-8 JSON assessment file")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = assess_grounding(payload) if args.mode == "grounding" else assess_complexity(payload)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"docomo: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
