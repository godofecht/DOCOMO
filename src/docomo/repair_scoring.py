"""Consume *official SWE-bench harness schema v2* results for real validated issues.

This validates accounting and calculates conservative rates over the full
frozen 500-case denominator. A user-provided results.json is NOT proof of
execution: the actual oracle/test logs and agent sandbox remain unaudited.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping
from typing import Any

from .complexity import _wilson_interval
from .repair_corpus import DATASET_ID, REVISION, SHA256, EXPECTED_INSTANCES

CATEGORIES = {
    "resolved": "resolved_ids",
    "unresolved": "unresolved_ids",
    "error": "error_ids",
    "empty_patch": "empty_patch_ids",
    "incomplete": "incomplete_ids",
}
COUNTS = {
    "resolved": "resolved_instances",
    "unresolved": "unresolved_instances",
    "error": "error_instances",
    "empty_patch": "empty_patch_instances",
}
HEX40 = re.compile(r"[0-9a-fA-F]{40}\Z")


def _ids(report: Mapping, key: str, all_ids: set[str]) -> set[str]:
    raw = report.get(key)
    if not isinstance(raw, list) or any(not isinstance(x, str) for x in raw):
        raise ValueError(f"{key} must be an array of source case IDs")
    if len(raw) != len(set(raw)):
        raise ValueError(f"{key} contains duplicate IDs")
    values = set(raw)
    if not values.issubset(all_ids):
        raise ValueError(f"{key} includes unknown source case IDs")
    return values


def _count(report: Mapping, name: str) -> int:
    value = report.get(name)
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def score_official_repair_report(report: Mapping[str, Any], inventory: Mapping[str, Any],
                                 *, run_id: str, agent_model_id: str,
                                 harness_commit: str) -> dict:
    """Validate official report set relations before reporting any success rate.

    The official v2 report is from swebench/harness/reporting.py. The evaluator
    must independently verify run provenance, logs, image isolation and tool
    versions before these numbers can support scientific claims.
    """
    if not isinstance(report, Mapping) or report.get("schema_version") != 2:
        raise ValueError("requires official SWE-bench harness results.json schema_version=2")
    if (not isinstance(inventory, Mapping) or inventory.get("dataset") != DATASET_ID
            or inventory.get("revision") != REVISION
            or inventory.get("parquet_sha256") != SHA256
            or inventory.get("repair_issues") != EXPECTED_INSTANCES):
        raise ValueError("case inventory must identify the exact pinned SWE-bench Verified source")
    rows = inventory.get("cases")
    if not isinstance(rows, list) or len(rows) != EXPECTED_INSTANCES:
        raise ValueError("case inventory must include all 500 pinned source instances")
    ids = set()
    repos = {}
    for record in rows:
        if not isinstance(record, Mapping):
            raise ValueError("invalid pinned case inventory")
        case = record.get("instance_id")
        repository = record.get("repository")
        if not isinstance(case, str) or not isinstance(repository, str) or case in ids:
            raise ValueError("duplicate or invalid pinned issue ID")
        ids.add(case)
        repos[case] = repository
    if len(ids) != EXPECTED_INSTANCES:
        raise ValueError("incomplete pinned issue population")
    if not isinstance(run_id, str) or not run_id.strip() or len(run_id)>128:
        raise ValueError("run_id must identify original evaluator execution")
    if not isinstance(agent_model_id, str) or not agent_model_id.strip():
        raise ValueError("agent_model_id is required")
    if not isinstance(harness_commit, str) or not HEX40.fullmatch(harness_commit):
        raise ValueError("harness_commit must be pinned to a full 40-character Git SHA")
    if _count(report, "total_instances") != EXPECTED_INSTANCES:
        raise ValueError("official report must evaluate the full frozen 500-case population")

    statuses = {key:_ids(report, field, ids) for key,field in CATEGORIES.items()}
    for a in statuses:
        for b in statuses:
            if a < b and statuses[a] & statuses[b]:
                raise ValueError(f"official repair categories {a} and {b} overlap")
    union = set().union(*statuses.values())
    if union != ids:
        raise ValueError("official report omits known source cases from all outcome categories")
    for name,count_key in COUNTS.items():
        if _count(report, count_key) != len(statuses[name]):
            raise ValueError(f"{count_key} disagrees with the corresponding case IDs")

    submitted = _ids(report, "submitted_ids", ids)
    completed = _ids(report, "completed_ids", ids)
    if _count(report, "submitted_instances") != len(submitted):
        raise ValueError("submitted_instances does not match submitted_ids")
    if _count(report, "completed_instances") != len(completed):
        raise ValueError("completed_instances does not match completed_ids")
    if statuses["incomplete"] != ids - submitted:
        raise ValueError("incomplete cases must equal the frozen cases not submitted")
    if (not statuses["resolved"].issubset(completed) or
            not statuses["unresolved"].issubset(completed) or
            not completed.issubset(submitted) or
            not statuses["empty_patch"].issubset(submitted) or
            not statuses["error"].issubset(submitted) or
            completed & (statuses["empty_patch"] | statuses["incomplete"])):
        raise ValueError("submitted/completed/resolved case memberships contradict official report semantics")
    for key,count in (("infra_failure_ids","infra_failure_instances"),
                      ("ambiguous_failure_ids","ambiguous_failure_instances")):
        cases = _ids(report,key,ids)
        if not cases.issubset(statuses["unresolved"] | statuses["error"]):
            raise ValueError(f"{key} must be a subset of unresolved or errored cases")
        if _count(report, count) != len(cases):
            raise ValueError(f"{count} disagrees with case ID list")

    result_by_repo = {}
    for repo in sorted(set(repos.values())):
        subset = {case for case in ids if repos[case] == repo}
        successful = len(statuses["resolved"] & subset)
        result_by_repo[repo] = {
            "cases":len(subset), "reported_resolved":successful,
            "reported_resolved_fraction":successful/len(subset),
            "reported_unresolved":len(statuses["unresolved"] & subset),
            "reported_error":len(statuses["error"] & subset),
            "reported_unsubmitted":len(statuses["incomplete"] & subset),
        }
    passed=len(statuses["resolved"])
    low,high=_wilson_interval(passed,EXPECTED_INSTANCES,.95)
    status_counts = {name: len(values) for name,values in statuses.items()}
    return {
        "status":"official_report_format_and_case_accounting_validated_run_logs_unverified",
        "source_dataset":DATASET_ID, "source_revision":REVISION,
        "source_sha256":SHA256,
        "agent_model_id":agent_model_id, "run_id":run_id,
        "harness_commit":harness_commit.lower(),
        "cases":EXPECTED_INSTANCES,
        "reported_solved":passed,
        "reported_resolved_fraction":passed/EXPECTED_INSTANCES,
        "reported_resolved_wilson_95pct": [low,high],
        "category_counts":status_counts,
        "infrastructure_failures_not_excluded_from_denominator":True,
        "unsubmitted_and_error_cases_not_excluded_from_denominator":True,
        "by_repository":result_by_repo,
        "evaluation_artifacts_independently_verified":False,
        "predictive_cost_calibration_status":"not_measured",
        "limitations":[
            "This validates a submitted official harness report's schema and population accounting, not whether the tests actually ran.",
            "Pass/fail labels must be checked against original official SWE-bench Docker logs and image/tool versions by an independent evaluator.",
            "An agent may have accessed gold patches or future commits unless sandbox policy is independently enforced.",
            "SWE-bench issue resolution has no developer labor or machine billing label and cannot calibrate whole-project cost.",
            "Do not select a solved-only subset or drop infrastructure failures from the 500-case reported denominator.",
        ],
    }
