"""Human-validated real repository issues as a separate acceptance-evaluation domain.

The 500 SWE-bench Verified problems are NOT whole-project costs or observed
developer hours. The pin includes an immutable Hugging Face dataset revision
and SHA-256 of the original Parquet bytes. Only issue text and pre-fix commits
can be exported to an agent. Gold patches/tests NEVER appear in agent tasks.

Parquet reading requires the optional project extra: pip install '.[repair]'.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

DATASET_ID = "SWE-bench/SWE-bench_Verified"
REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"
PATH = "data/test-00000-of-00001.parquet"
SHA256 = "030cfd7f2a704c4c0226e7f104c725a3b41230b1d3517f9c915ad7ea5be3fa25"
EXPECTED_INSTANCES = 500
MAX_BYTES = 20_000_000
URL = f"https://huggingface.co/datasets/{DATASET_ID}/resolve/{REVISION}/{PATH}"
HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
REPO = re.compile(r"^[^/\s]+/[^/\s]+$")


def fetch_verified_repair_cases(directory: Path, *, offline: bool = False) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "swe_bench_verified.parquet"
    if target.exists():
        content = target.read_bytes()
        if hashlib.sha256(content).hexdigest() != SHA256:
            raise ValueError("SWE-bench Verified parquet checksum mismatch")
        return target
    if offline:
        raise FileNotFoundError("pinned SWE-bench Verified source not cached")
    request = urllib.request.Request(URL, headers={"User-Agent": "DOCOMO-Research/0.13"})
    with urllib.request.urlopen(request, timeout=90) as response:
        content = response.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES or hashlib.sha256(content).hexdigest() != SHA256:
        raise ValueError("SWE-bench Verified pinned download SHA256 mismatch or oversized file")
    target.write_bytes(content)
    return target


def _table(path: Path) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as error:
        raise ValueError("repair-case import requires optional package: pip install 'docomo[repair]'") from error
    table = pq.read_table(path)
    required = {
        "instance_id", "repo", "base_commit", "problem_statement",
        "patch", "test_patch", "FAIL_TO_PASS", "PASS_TO_PASS",
    }
    if not required.issubset(table.column_names):
        raise ValueError(f"pinned SWE-bench Verified source lacks required evaluation columns: {sorted(required-set(table.column_names))}")
    return table.to_pylist()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: missing text")
    return value


def read_verified_repairs(path: Path) -> dict:
    """Inventory all human-validated repairs without exposing gold/oracles to agents."""
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        raise ValueError("SWE-bench Verified source bytes are not the pinned dataset")
    rows = _table(path)
    if len(rows) != EXPECTED_INSTANCES:
        raise ValueError("SWE-bench Verified expected 500 source issue instances")
    cases = []
    prompts = []
    identifiers = set()
    repositories = Counter()
    for entry in rows:
        identity = _text(entry.get("instance_id"), "instance_id")
        repository = _text(entry.get("repo"), "repo")
        base = _text(entry.get("base_commit"), "base_commit")
        issue = _text(entry.get("problem_statement"), "problem_statement")
        gold = _text(entry.get("patch"), "gold patch")
        test_patch = _text(entry.get("test_patch"), "gold test patch")
        if identity in identifiers or not REPO.fullmatch(repository) or not HEX40.fullmatch(base):
            raise ValueError(f"invalid or duplicated issue instance: {identity}")
        identifiers.add(identity)
        repositories[repository] += 1
        # Gold hashes are evaluator-private metadata. Never export raw patches.
        cases.append({
            "instance_id": identity,
            "repository": repository,
            "pre_fix_commit": base.lower(),
            "source": DATASET_ID,
            "repair_evaluation": "human_validated_solvable_issue_not_replayed_here",
            "issue_sha256": hashlib.sha256(issue.encode("utf-8")).hexdigest(),
            "gold_patch_sha256": hashlib.sha256(gold.encode("utf-8")).hexdigest(),
            "gold_test_patch_sha256": hashlib.sha256(test_patch.encode("utf-8")).hexdigest(),
            "developer_human_minutes": None,
            "machine_expenditure": None,
            "whole_project_acceptance": False,
            "agent_run_outcome": None,
            "source_revision": REVISION,
        })
        prompts.append({
            "instance_id": identity,
            "repo": repository,
            "base_commit": base.lower(),
            "problem_statement": issue,
            "evaluation_protocol": "official SWE-bench Verified harness; independent evaluator owns tests",
            "original_gold_patch_included": False,
            "oracle_tests_included": False,
        })
    return {
        "status": "pinned_human_validated_repair_cases_not_cost_projects",
        "dataset": DATASET_ID, "revision": REVISION,
        "parquet_sha256": SHA256, "source_url": URL,
        "repair_issues": len(cases),
        "repositories": dict(sorted(repositories.items())),
        "repository_count": len(repositories),
        "source_validation": "original Parquet SHA256 and required human-validated issue fields",
        "evaluated_agent_runs": 0,
        "original_human_effort_minutes_available": False,
        "original_machine_spend_available": False,
        "independent_full_project_acceptance": False,
        "cases": cases,
        "agent_prompts": prompts,
        "limitations": [
            "The human validation concerns issue solvability and fairness, not end-to-end completed project delivery.",
            "No agent has been executed by DOCOMO; issue records do not imply a new model's pass rate.",
            "Prompts may still be contaminated by public later commits; independent sandboxing and clean-base enforcement remain essential.",
            "Do not provide gold patches, gold test patches or future repository history to the candidate agent.",
            "Reproducing pass/fail requires official SWE-bench evaluation images and logs; test metadata alone is not a result.",
            "Neither human working minutes nor model inference charges can be inferred from the repair issue dataset.",
        ],
    }
