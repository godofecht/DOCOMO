"""Strict earlier-to-later project effort evaluation using real completion-year cohorts.

Unlike leave-one-year-out CV, no training fold can contain projects completed
after the evaluated project's year. Year is ONLY a split key, never a predictor.
Data are historical and may still contain hindsight features or organisational
dependence; this is a stronger retrospective test, not prospective certification.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any

from .calibration import _metrics
from .project_benchmarks import _fit, _predict

TEMPORAL_SOURCES = ("nasa93", "desharnais")
MODELS = ("training_median", "size_only", "size_and_observed_drivers")


def evaluate_forward_years(name: str, projects: list[dict]) -> dict:
    if name not in TEMPORAL_SOURCES:
        raise ValueError("strict forward-year tests are supported only for NASA93 and Desharnais")
    if not isinstance(projects, list) or len(projects) < 30:
        raise ValueError("need actual historical projects with declared completion years")
    unit = projects[0]["effort_unit"]
    size_unit = projects[0]["size_unit"]
    feature_keys = sorted(projects[0]["planning_proxy_features"])
    years: dict[int, list[dict]] = defaultdict(list)
    ids = set()
    for row in projects:
        if row["source_id"] != name:
            raise ValueError("cannot pool different project corpora")
        if row["effort_unit"] != unit or row["size_unit"] != size_unit:
            raise ValueError("cannot pool incompatible project cost or size units")
        if set(row["planning_proxy_features"]) != set(feature_keys):
            raise ValueError("unexpected differences in historical feature schema")
        if row["record_id"] in ids:
            raise ValueError("duplicate historical project ID in forward test")
        ids.add(row["record_id"])
        group = row["holdout_group"]
        if not isinstance(group, str) or not group.startswith("year:"):
            raise ValueError("a real completion-year group is required")
        try:
            year = int(group.partition(":")[2])
        except ValueError as error:
            raise ValueError("noninteger completion-year group") from error
        if year != int(row["descriptors"].get(
            "year" if name == "nasa93" else "completion_year_code"
        )):
            raise ValueError("completion year does not match immutable source descriptor")
        years[year].append(row)

    # The challenger must have enough earlier accepted observations to fit
    # its full predictor basis; do not reduce the model after examining test scores.
    minimum_train = max(20, 3*(len(feature_keys)+1))
    evaluated = {model: [] for model in MODELS}
    all_results = []
    evaluated_years = []
    excluded_early_projects = []
    for year in sorted(years):
        train = [r for past in sorted(years) if past < year for r in years[past]]
        test = years[year]
        if len(train) < minimum_train:
            excluded_early_projects.extend(r["record_id"] for r in test)
            continue
        frozen = {
            model: _fit(train, model, feature_keys)
            for model in ("size_only", "size_and_observed_drivers")
        }
        center = statistics.median(r["effort"] for r in train)
        fold_predictions = {model: [] for model in MODELS}
        for row in test:
            predicted = {
                "training_median": center,
                **{model: _predict(row, frozen[model]) for model in frozen},
            }
            case = {
                "record_id": row["record_id"],
                "source_project_identifier": row["source_project_identifier"],
                "test_completion_year_code": year,
                "training_projects_completed_strictly_before_test_year": len(train),
                "actual_effort": row["effort"],
                "effort_unit": unit,
                "predictions": predicted,
                "prediction_error_by_model": {
                    model: prediction-row["effort"]
                    for model, prediction in predicted.items()
                },
            }
            all_results.append(case)
            for model in MODELS:
                pair = (row["effort"], predicted[model])
                evaluated[model].append(pair)
                fold_predictions[model].append(pair)

        evaluated_years.append({
            "year_code": year,
            "training_count": len(train),
            "test_count": len(test),
            "train_years": [y for y in sorted(years) if y < year],
            "metrics": {
                model: _metrics(
                    [observed for observed, _ in fold_predictions[model]],
                    [forecast for _, forecast in fold_predictions[model]],
                )
                for model in MODELS
            },
        })

    if not evaluated_years:
        return {
            "source_id": name,
            "status": "insufficient_early_year_history_for_fixed_model",
            "minimum_training_projects": minimum_train,
            "total_project_observations": len(projects),
            "unscored_early_projects": len(excluded_early_projects),
            "test_predictions": [],
            "warnings": [
                "No year had sufficient earlier completed projects to fit the fixed model.",
                "Never add later project outcomes to an earlier training fold to manufacture a backtest.",
            ],
        }

    scores = {
        model: _metrics([actual for actual,_ in evaluated[model]],
                        [forecast for _,forecast in evaluated[model]])
        for model in MODELS
    }
    baseline = scores["size_only"]["log_rmse"]
    gains = {
        model: 1 - scores[model]["log_rmse"]/baseline
        for model in MODELS
    }
    return {
        "source_id": name,
        "status": "strict_earlier_to_later_historical_backtest_not_prospective",
        "effort_unit": unit,
        "size_unit": size_unit,
        "historical_completion_year_codes": sorted(years),
        "minimum_training_projects": minimum_train,
        "total_project_observations": len(projects),
        "scored_future_year_projects": len(all_results),
        "unscored_early_projects": len(excluded_early_projects),
        "unscored_early_project_ids": excluded_early_projects,
        "evaluated_test_years": evaluated_years,
        "metrics": scores,
        "relative_log_rmse_reduction_vs_size_only": gains,
        "driver_improves_forward_year_log_rmse": gains["size_and_observed_drivers"] > 0,
        "test_predictions": all_results,
        "warnings": [
            "Every training year precedes the evaluated year. No future-outcome leakage via train/test split.",
            "Early projects are excluded because the fixed challenger cannot be trained yet; excluded counts and IDs are explicit.",
            "Original source drivers may be ex-post, so even chronological holdouts do not prove preplanning availability.",
            "Completion years may group dependent projects from the same organisation; independence and acceptance are unverified.",
            "Model hyperparameters were not tuned on these test years; these are still historical reused datasets.",
            "No observed AI-assisted developer workflow or whole-project independent acceptance is available in these records.",
        ],
    }


def evaluate_all_forward(corpus: dict) -> dict:
    if corpus.get("status") != "actual_published_historical_cost_observations":
        raise ValueError("requires original real completed-project records")
    by_source = {
        name: evaluate_forward_years(
            name, [r for r in corpus["records"] if r["source_id"] == name]
        ) for name in TEMPORAL_SOURCES
    }
    return {
        "status": "retrospective_strict_forward_year_project_effort_validation",
        "domains": by_source,
        "do_not_infer_prospective_ai_native_calibration": True,
    }
