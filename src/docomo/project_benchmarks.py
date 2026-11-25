"""Falsifiable historical project effort benchmarks by source domain.

Training-time standardisation and coefficients are fit within each held-out
group. Group identity is a completion-year cohort where available; otherwise
project ID modulo five is only a retrospective approximation, NOT a real
prospective test. Drivers are observational proxies, often recorded ex-post.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any

from .calibration import _metrics, _solve
from .project_corpus import PROJECT_SOURCES


def _fit(train: list[dict], model: str, keys: list[str]) -> dict:
    if model not in ("size_only", "size_and_observed_drivers"):
        raise ValueError("unknown historical model")
    fields = (["log_size"] if model == "size_only" else ["log_size", *keys])
    observations = []
    for row in train:
        feature = {"log_size": math.log(row["size"]), **row["planning_proxy_features"]}
        observations.append([float(feature[key]) for key in fields])
    columns = len(fields)
    if len(train) < max(20, 3 * columns):
        raise ValueError("too little training data for feature dimensionality")
    means = [statistics.mean(r[j] for r in observations) for j in range(columns)]
    stds = [statistics.pstdev(r[j] for r in observations) or 1.0 for j in range(columns)]
    x = [[1.0, *[(feature[j]-means[j])/stds[j] for j in range(columns)]]
         for feature in observations]
    y = [math.log(r["effort"]) for r in train]
    penalty = 4.0
    dim = columns + 1
    gram = [[math.fsum(r[i] * r[j] for r in x) +
             (penalty if i == j and i > 0 else 0.0)
             for j in range(dim)] for i in range(dim)]
    rhs = [math.fsum(r[i]*target for r,target in zip(x,y)) for i in range(dim)]
    beta = _solve(gram, rhs)
    return {"fields": fields, "means": means, "stds": stds, "coefficients": beta}


def _predict(row: dict, fit: dict) -> float:
    features = {"log_size": math.log(row["size"]), **row["planning_proxy_features"]}
    z = fit["coefficients"][0] + math.fsum(
        (features[key] - mean)/scale * coef
        for key,mean,scale,coef in zip(
            fit["fields"], fit["means"], fit["stds"], fit["coefficients"][1:]
        )
    )
    forecast = math.exp(z)
    if not math.isfinite(forecast) or forecast <= 0:
        raise ValueError("nonfinite historical effort forecast")
    return forecast


def evaluate_legacy_domain(name: str, projects: list[dict]) -> dict:
    if name not in PROJECT_SOURCES or not projects:
        raise ValueError("unknown or empty historical domain")
    if any(p["source_id"] != name for p in projects):
        raise ValueError("cannot pool different source domains or units")
    unit = projects[0]["effort_unit"]
    size_unit = projects[0]["size_unit"]
    if any(p["effort_unit"] != unit or p["size_unit"] != size_unit for p in projects):
        raise ValueError("inconsistent effort or size units")
    keys = sorted(projects[0]["planning_proxy_features"])
    if any(set(r["planning_proxy_features"]) != set(keys) for r in projects):
        raise ValueError("historical feature schema mismatch")

    groups = defaultdict(list)
    for project in projects:
        groups[project["holdout_group"]].append(project)
    if len(groups) < 5:
        raise ValueError("requires five or more independent or deterministic groups")
    outputs: dict[str,list[tuple[float,float]]] = {
        "training_median": [],
        "size_only": [],
        "size_and_observed_drivers": [],
    }
    fold_details = []
    for group, test in sorted(groups.items()):
        train = [r for g,items in groups.items() if g != group for r in items]
        if not train:
            raise ValueError("empty training fold")
        fits = {model:_fit(train,model,keys)
                for model in ("size_only", "size_and_observed_drivers")}
        median = statistics.median(row["effort"] for row in train)
        fold_details.append({
            "withheld_group": group,
            "training": len(train),
            "held_out": len(test),
            "training_unique_groups": len(groups)-1,
        })
        for r in test:
            outputs["training_median"].append((r["effort"], median))
            for model,fit in fits.items():
                outputs[model].append((r["effort"], _predict(r,fit)))

    measured = {name:_metrics([y for y,_ in pairs], [p for _,p in pairs])
                for name,pairs in outputs.items()}
    base = measured["size_only"]["log_rmse"]
    changes = {name:measured[name]["log_rmse"]/base-1 for name in outputs}
    folds_are_temporal = name in ("nasa93", "desharnais")
    return {
        "source_id": name, "n": len(projects),
        "unit": unit, "size_unit": size_unit,
        "evaluation": ("leave_one_historical_completion_year_out"
                       if folds_are_temporal else "project_id_modulo_five_retrospective"),
        "completion_years_or_id_groups": len(groups),
        "folds": fold_details,
        "metrics": measured,
        "relative_log_rmse_change_vs_size_only": changes,
        "candidate_amendment": {
            "hypothesis": "Pre-existing cost/complexity descriptors reduce held-out log-RMSE beyond a size-only baseline",
            "observed_driver_improves_heldout_log_rmse":
                measured["size_and_observed_drivers"]["log_rmse"] <
                measured["size_only"]["log_rmse"],
            "metric": "log_rmse",
            "eligible_for_ai_native_release": False,
            "reason": "historical data, potential hindsight features, no modern independently accepted development outcomes",
        },
        "warnings": [
            "All observations originate from one historical dataset; no cross-dataset cost units or task types were pooled.",
            "The held-out evaluation is retrospective, not a prospectively collected project cohort.",
            "Completion years isolate temporal cohorts for NASA93 and Desharnais; ID-modulo folds are not temporal validation.",
            "Source features may reflect completed scope rather than genuine planning-time features.",
            "Small or correlated project families can overstate out-of-sample generalisation.",
            "Only observed human effort is assessed, not functional acceptance, independent verification, AI use or machine cost.",
        ],
    }


def evaluate_legacy_corpus(corpus: dict) -> dict:
    if corpus.get("status") != "actual_published_historical_cost_observations":
        raise ValueError("expected audited real-project corpus")
    result = {}
    for name in PROJECT_SOURCES:
        projects = [row for row in corpus["records"] if row["source_id"] == name]
        result[name] = evaluate_legacy_domain(name, projects)
    return {
        "status": "retrospective_legacy_benchmarks_not_ai_native_calibration",
        "cohort_results": result,
        "amendments_supported": {
            name: result[name]["candidate_amendment"] for name in result
        },
        "unqualified_cross_domain_ranking_prohibited": True,
    }
