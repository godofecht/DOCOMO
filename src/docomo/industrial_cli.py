"""Inspect or ingest original Mendeley industrial effort data with a pinned mapping.

Never guesses worksheet columns or labels the model's estimates as coding time.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .industrial_stories import evaluate_industrial_estimators, import_industrial_stories
from .xlsx_source import _safe_archive, _sheet_paths, read_xlsx_sheet


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docomo-industrial",
                                     description="Audit real source XLSX and compare original human/AI effort estimates")
    sub = parser.add_subparsers(dest="mode", required=True)
    inspect = sub.add_parser("inspect", help="Show source SHA256, sheet names and literal header candidates")
    inspect.add_argument("workbook", type=Path)
    inspect.add_argument("--sheet", help="Inspect one explicitly named visible worksheet")
    score = sub.add_parser("score", help="Validate and score a pinned real v2 workbook")
    score.add_argument("workbook", type=Path)
    score.add_argument("--mapping", type=Path, required=True)
    score.add_argument("--output", type=Path)
    score.add_argument("--records-output", type=Path)
    score.add_argument("--bootstrap", type=int, default=1000)
    score.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args(argv)
    try:
        if args.mode == "inspect":
            archive, sha = _safe_archive(args.workbook)
            try:
                sheets = _sheet_paths(archive)
            finally:
                archive.close()
            result = {"source_sha256": sha,
                      "source_origin_verified": False,
                      "worksheets": [{"name":s["name"],"state":s["state"]} for s in sheets]}
            if args.sheet:
                sheet = read_xlsx_sheet(args.workbook, sheet_name=args.sheet)
                result["requested_worksheet"] = args.sheet
                result["first_rows"] = [
                    {"row_number": index,
                     "cells": {str(col): value for col,value in sorted(sheet["rows"][index].items())},
                     "formula_columns": sorted(col for row,col in sheet["formula_cells"] if row == index)}
                    for index in sorted(sheet["rows"])[:10]
                ]
        else:
            config = json.loads(args.mapping.read_text(encoding="utf-8"))
            corpus = import_industrial_stories(args.workbook, config)
            result = evaluate_industrial_estimators(
                corpus, bootstrap_replicates=args.bootstrap, seed=args.seed
            )
            if args.records_output:
                args.records_output.parent.mkdir(parents=True, exist_ok=True)
                args.records_output.write_text(json.dumps(
                    corpus, indent=2, sort_keys=True, allow_nan=False
                ) + "\n", encoding="utf-8")
        encoded = json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n"
        if args.mode == "score" and args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded,encoding="utf-8")
        else:
            print(encoded,end="")
    except (OSError,ValueError,TypeError,OverflowError,KeyError,json.JSONDecodeError) as error:
        print(f"docomo-industrial: {error}",file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    raise SystemExit(main())
