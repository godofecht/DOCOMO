"""Export 500 human-validated SWE-bench issues without exposing gold patches."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .repair_corpus import fetch_verified_repair_cases, read_verified_repairs


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="docomo-repairs",
        description="Read 500 source-pinned real repository repair cases; not a cost estimator",
    )
    parser.add_argument("--dataset-dir", type=Path, default=Path(".docomo-cache"))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--index-output", type=Path,
                        help="Metadata inventory containing source hashes only, never gold patch bytes")
    parser.add_argument("--agent-prompts-output", type=Path,
                        help="Optional JSONL with issue descriptions and pre-fix commits only")
    args = parser.parse_args(argv)
    try:
        path = fetch_verified_repair_cases(args.dataset_dir, offline=args.offline)
        inventory = read_verified_repairs(path)
        prompts = inventory.pop("agent_prompts")
        encoded = json.dumps(inventory, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.index_output:
            args.index_output.parent.mkdir(parents=True, exist_ok=True)
            args.index_output.write_text(encoded, encoding="utf-8")
        else:
            print(encoded, end="")
        if args.agent_prompts_output:
            args.agent_prompts_output.parent.mkdir(parents=True, exist_ok=True)
            with args.agent_prompts_output.open("w", encoding="utf-8") as output:
                for row in prompts:
                    output.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    except (OSError, ValueError) as error:
        print(f"docomo-repairs: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
