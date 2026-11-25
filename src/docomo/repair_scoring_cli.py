"""Consume an official SWE-bench v2 results.json on a frozen Verified case inventory."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

from .repair_scoring import score_official_repair_report


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="docomo-score-repairs",
        description="Validate 500-case official SWE-bench report accounting; does NOT authenticate execution logs",
    )
    p.add_argument("--inventory", type=Path, required=True,
                   help="Metadata-only source-pinned output from docomo-repairs")
    p.add_argument("--official-results", type=Path, required=True,
                   help="results.json produced by official SWE-bench harness version 2")
    p.add_argument("--run-id", required=True)
    p.add_argument("--agent-model-id", required=True)
    p.add_argument("--harness-commit", required=True,
                   help="40-character Git commit of independent SWE-bench evaluation harness")
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        file_bytes = args.official_results.read_bytes()
        report = json.loads(file_bytes.decode("utf-8"))
        evaluated = score_official_repair_report(
            report,inventory,run_id=args.run_id,
            agent_model_id=args.agent_model_id,harness_commit=args.harness_commit,
        )
        evaluated["submitted_official_results_json_sha256"] = hashlib.sha256(file_bytes).hexdigest()
        output = json.dumps(evaluated,indent=2,sort_keys=True,allow_nan=False)+"\n"
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(output,encoding="utf-8")
        else:
            print(output,end="")
    except (OSError,ValueError,TypeError,UnicodeError,json.JSONDecodeError) as error:
        print(f"docomo-score-repairs: {error}",file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
