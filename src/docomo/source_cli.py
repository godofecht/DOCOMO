"""CLI for local original-document SHA256 checks (never claims source authenticity)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .source_audit import audit_primary_sources


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docomo-source-audit",
                                     description="Reconcile project records against local copies of original evidence")
    parser.add_argument("input", type=Path, help="Source evidence index JSON document")
    parser.add_argument("--source-root", type=Path, required=True,
                        help="Existing local folder containing copied original supporting files")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result = audit_primary_sources(payload, args.source_root)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"docomo-source-audit: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
