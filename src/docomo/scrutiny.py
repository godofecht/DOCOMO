"""Falsification-first DOCOMO amendment docket.

Evidence is extracted directly from real published project backtests, not
self-reported benchmark scores. A historical backtest can suggest a candidate
but cannot authorize a predictive model release for AI-native projects.
"""
from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .project_corpus import PROJECT_SOURCES, EXPECTED_ROWS

FROZEN_V1_DOMAINS = ("cocomo81", "nasa93", "china", "desharnais")

_ALLOWED = {"proposal_id", "schema_version", "hypothesis", "target",
            "champion", "challenger", "domains", "minimum_improvement_fraction",
            "maximum_allowed_regression_fraction", "minimum_improving_domains",
            "scope", "proposed_feature_timing"}
_CANDIDATES = {"size_only", "size_and_observed_drivers", "training_median"}
_ID = re.compile(r"[a-z0-9][a-z0-9._-]{3,127}\Z")


def _finite(value: Any, name: str, minimum: float, maximum: float) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be finite in [{minimum}, {maximum}]")
    return float(value)


def validate_proposal(candidate: Mapping[str, Any]) -> dict:
    if not isinstance(candidate, Mapping) or set(candidate) != _ALLOWED:
        raise ValueError("amendment must declare every required field and no extras")
    if candidate["schema_version"] not in ("1.0", "1.1"):
        raise ValueError("unsupported proposal schema")
    if not isinstance(candidate["proposal_id"], str) or not _ID.fullmatch(candidate["proposal_id"]):
        raise ValueError("proposal_id must be a stable, versioned slug")
    for name in ("hypothesis", "target", "scope"):
        if not isinstance(candidate[name], str) or not candidate[name].strip():
            raise ValueError(f"{name} must be nonempty")
    if candidate["target"] != "historical_project_human_effort":
        raise ValueError("this scorer supports only historical project effort, not AI-native costs")
    domains = candidate["domains"]
    expected = (FROZEN_V1_DOMAINS if candidate["schema_version"] == "1.0"
                else PROJECT_SOURCES)
    if not isinstance(domains,list) or domains != list(expected):
        raise ValueError(f"all {len(expected)} predeclared historical effort domains required in source order; no cherry-picking")
    if (candidate["champion"] not in _CANDIDATES or candidate["challenger"] not in _CANDIDATES
            or candidate["champion"] == candidate["challenger"]):
        raise ValueError("amendment must compare distinct supported estimator models")
    timing = candidate["proposed_feature_timing"]
    if timing not in ("planning_time_independently_verified", "historical_recorded_or_unknown"):
        raise ValueError("feature timing must be declared")
    min_improvement = _finite(candidate["minimum_improvement_fraction"],
                              "minimum_improvement_fraction", 0, 1)
    max_regression = _finite(candidate["maximum_allowed_regression_fraction"],
                             "maximum_allowed_regression_fraction", 0, 1)
    count = candidate["minimum_improving_domains"]
    if type(count) is not int or not 1 <= count <= len(expected):
        raise ValueError(f"minimum_improving_domains must be 1..{len(expected)}")
    return {
        **dict(candidate),
        "domains": list(expected),
        "minimum_improvement_fraction": min_improvement,
        "maximum_allowed_regression_fraction": max_regression,
    }


def validate_evidence_registry(catalog: Mapping[str, Any], source_report: dict) -> dict:
    if not isinstance(catalog, Mapping) or catalog.get("schema_version") != "1.0":
        raise ValueError("invalid evidence registry")
    domains = catalog.get("domains")
    if not isinstance(domains, list) or not domains:
        raise ValueError("evidence registry requires domains")
    by_id = {}
    for record in domains:
        if not isinstance(record, Mapping) or "id" not in record:
            raise ValueError("malformed evidence domain")
        if record["id"] in by_id:
            raise ValueError("duplicate evidence source IDs")
        by_id[record["id"]] = record
    from_report = source_report.get("source_data", {})
    datasets = from_report.get("datasets", [])
    for row in datasets:
        name = row["source_id"]
        if name not in by_id or by_id[name].get("data_status") != "source_pinned_ingested":
            raise ValueError(f"unregistered or non-ingested data in effort report: {name}")
        if by_id[name].get("observed") != row["project_observations"]:
            raise ValueError(f"mismatched empirical source count for {name}")
        if by_id[name].get("label") != row["effort_unit"]:
            raise ValueError(f"mismatched empirical outcome unit for {name}")
        if row["project_observations"] != EXPECTED_ROWS[name]:
            raise ValueError(f"unexpected row count from {name}")
    if {r["source_id"] for r in datasets} != set(PROJECT_SOURCES):
        raise ValueError("must benchmark all four historical sources with original labels")
    return {"registered_sources": len(domains), "ingested_historical_sources": len(datasets),
            "historical_project_records": sum(r["project_observations"] for r in datasets)}


def scrutinize_amendment(proposal: Mapping[str, Any],
                         report: Mapping[str, Any],
                         registry: Mapping[str, Any]) -> dict:
    p = validate_proposal(proposal)
    if report.get("calibration_status") != "historical_real_effort_retrospective_not_ai_native":
        raise ValueError("cannot promote unlabelled or non-historical benchmark data")
    source_check = validate_evidence_registry(registry, dict(report))
    benchmark = report.get("evaluations", {})
    if benchmark.get("status") != "retrospective_legacy_benchmarks_not_ai_native_calibration":
        raise ValueError("requires actual completed-project heldout benchmark report")
    data = benchmark.get("cohort_results", {})
    if set(data) != set(PROJECT_SOURCES):
        raise ValueError("missing or added evaluation domains would bias the amendment")
    outcomes = []
    all_promising = 0
    fails = []
    for name in p["domains"]:
        item = data[name]
        if item["n"] != EXPECTED_ROWS[name]:
            raise ValueError(f"{name}: inconsistent project row count in benchmark")
        metrics = item["metrics"]
        base = float(metrics[p["champion"]]["log_rmse"])
        candidate = float(metrics[p["challenger"]]["log_rmse"])
        if not all(math.isfinite(x) and x > 0 for x in (base, candidate)):
            raise ValueError("benchmark error must be finite and positive")
        improvement = 1 - candidate/base
        success = improvement >= p["minimum_improvement_fraction"]
        significant_regression = improvement < -p["maximum_allowed_regression_fraction"]
        all_promising += int(success)
        if significant_regression:
            fails.append(name)
        outcomes.append({
            "dataset": name,
            "projects": EXPECTED_ROWS[name],
            "outcome_unit": item["unit"],
            "validation": item["evaluation"],
            "champion_log_rmse": base,
            "challenger_log_rmse": candidate,
            "relative_improvement_fraction": improvement,
            "meets_minimum_improvement": success,
            "exceeds_regression_budget": significant_regression,
            "negative_result": improvement <= 0,
        })
    performance = all_promising >= p["minimum_improving_domains"] and not fails
    temporal = report.get("strict_forward_year_validation")
    forward_results = []
    temporal_success = False
    if temporal is not None:
        if not isinstance(temporal, Mapping) or temporal.get("status") != "retrospective_strict_forward_year_project_effort_validation":
            raise ValueError("invalid strict-forward validation report")
        results = temporal.get("domains")
        if not isinstance(results, Mapping) or set(results) != {"nasa93", "desharnais"}:
            raise ValueError("strict-forward benchmark must evaluate NASA93 and Desharnais")
        for name in ("nasa93", "desharnais"):
            item = results[name]
            if item.get("status") != "strict_earlier_to_later_historical_backtest_not_prospective":
                forward_results.append({"dataset": name, "status": item.get("status"),
                                        "relative_log_rmse_improvement": None,
                                        "regression_exceeds_budget": None})
                continue
            if (item.get("total_project_observations") != EXPECTED_ROWS[name]
                    or item.get("scored_future_year_projects",0) <= 0):
                raise ValueError(f"{name}: strict-forward source evidence is incomplete")
            metrics = item["metrics"]
            base = float(metrics[p["champion"]]["log_rmse"])
            challenger = float(metrics[p["challenger"]]["log_rmse"])
            if not all(math.isfinite(z) and z>0 for z in (base, challenger)):
                raise ValueError("invalid strict-forward predictive error")
            gain = 1 - challenger/base
            forward_results.append({
                "dataset": name, "status": item["status"],
                "scored_future_year_projects": item["scored_future_year_projects"],
                "unscored_early_projects": item["unscored_early_projects"],
                "champion_log_rmse": base,
                "challenger_log_rmse": challenger,
                "relative_log_rmse_improvement": gain,
                "meets_minimum_improvement": gain >= p["minimum_improvement_fraction"],
                "regression_exceeds_budget": gain < -p["maximum_allowed_regression_fraction"],
                "negative_result": gain <= 0,
            })
        temporal_success = (
            len(forward_results) == 2 and
            all(r["relative_log_rmse_improvement"] is not None
                and not r["regression_exceeds_budget"] for r in forward_results) and
            any(r["meets_minimum_improvement"] for r in forward_results)
        )
    feature_verified = p["proposed_feature_timing"] == "planning_time_independently_verified"
    # We do not have original planning timestamps for the historical predictors:
    # a proposal claim alone cannot make them independently verified.
    release_gate = {
        "cross_source_legacy_benchmark_screen": performance,
        "strict_forward_year_screen": temporal_success,
        "predictors_proven_available_at_planning": False,
        "prospective_unseen_project_holdout_passed": False,
        "independent_acceptance_and_cost_labels_audited": False,
        "human_ai_machine_workflows_and_versions_matched": False,
        "external_reproducibility_and_counterexample_review": False,
        "maintainer_and_independent_reviewer_approval": False,
        "postrelease_monitoring_and_rollback_plan_registered": False,
    }
    if p["proposed_feature_timing"] == "planning_time_independently_verified":
        # Must be supported by actual independent source measurements, not just text.
        raise ValueError("historical sources cannot establish independent planning-time feature availability")
    result = {
        "proposal_id": p["proposal_id"],
        "target": p["target"], "hypothesis": p["hypothesis"],
        "champion": p["champion"], "challenger": p["challenger"],
        "datasets_scrutinized": outcomes,
        "additional_registered_domains_not_in_frozen_proposal": [name for name in PROJECT_SOURCES if name not in p["domains"]],
        "positive_domains": all_promising,
        "substantial_regressions": fails,
        "historical_performance_screen_passed": performance,
        "strict_forward_year_screen_passed": temporal_success,
        "strict_forward_year_challenges": forward_results,
        "release_gates": release_gate,
        "release_status": "research_candidate_not_eligible_for_ai_native_release",
        "requested_model_upgrade_automatically_authorized": False,
        "falsification_findings": [
            f"{x['dataset']}: historical {x['validation']} showed a "
            f"{'regression' if x['relative_improvement_fraction'] < 0 else 'relative improvement'} "
            f"of {abs(x['relative_improvement_fraction'])*100:.2f}% in log-RMSE."
            for x in outcomes
        ],
        "forward_falsification_findings": [
            f"{r['dataset']}: strict-year-forward testing "
            + (f"improved log-RMSE by {r['relative_log_rmse_improvement']*100:.2f}%"
               if r['relative_log_rmse_improvement'] is not None
               and r['relative_log_rmse_improvement'] >= 0
               else (f"REGRESSED log-RMSE by {-r['relative_log_rmse_improvement']*100:.2f}%"
                     if r['relative_log_rmse_improvement'] is not None
                     else "had insufficient earlier-year training evidence"))
            for r in forward_results
        ],
        "evidence_integrity": source_check,
        "next_scrutiny": [
            "Independently audit whether every candidate feature was available before effort was incurred.",
            "Replicate a preregistered release decision on external unseen modern AI-native projects, across repositories and time.",
            "Retain all rejected and contradicted hypotheses in the public versioned docket; do not erase negative datasets.",
            "The frozen 1.0 proposal evaluates only its originally four named domains; revision 1.1 is a separately preregistered six-domain challenge.",
            "Test interval coverage, failure-aware costs and specification drift against locked baselines.",
            "Demand strong outcomes on strictly forward-year completed-project cohorts, not only years held out against future years.",
            "Require separate independent review and a rollback plan; no automatic model promotion from retrospective data.",
        ],
    }
    return result


def open_json(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as file:
        content = json.load(file)
    if not isinstance(content, dict):
        raise ValueError(f"{path} must contain an object")
    return content
