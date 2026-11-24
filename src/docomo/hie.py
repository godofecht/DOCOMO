"""Task-level human–LLM effort benchmark; not AI-native project cost calibration.

Story points and assigned LLM are known before execution. Prompt iteration,
validation, correction and file-change counts are post-execution diagnostics.
"""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from typing import Any

from .calibration import _metrics, _solve

PROCESS = ("Prompt_Iterations", "Corrective_Prompts", "Context_Prompts",
           "Modified_Files", "Validation_Detected", "Manual_Corrections")
REQUIRED = {"Execution_Id", "Developer", "LLM", "Story_Points", "Actual_Time_Min", *PROCESS}
MODELS = ("training_median", "story_points", "story_points_llm", "post_execution_diagnostic")


def read_hie_tasks(path: str | Path) -> list[dict[str, Any]]:
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("HIE task data missing expected fields")
        raw = list(reader)
    if not raw:
        raise ValueError("HIE dataset is empty")
    ids: set[int] = set()
    observations = []
    for line, r in enumerate(raw, start=2):
        try:
            identity = int(r["Execution_Id"])
            developer = r["Developer"].strip()
            llm = r["LLM"].strip()
            story_points = int(r["Story_Points"])
            minutes = float(r["Actual_Time_Min"])
            process = {name: int(r[name]) for name in PROCESS}
        except (TypeError, ValueError, AttributeError) as error:
            raise ValueError(f"invalid task data on row {line}") from error
        if (identity < 1 or identity in ids or not developer or not llm
                or story_points < 1 or minutes <= 0 or not math.isfinite(minutes)
                or any(value < 0 for value in process.values())):
            raise ValueError(f"invalid task or duplicate ID on row {line}")
        ids.add(identity)
        observations.append({"id": identity, "developer": developer, "llm": llm,
                             "story_points": story_points, "actual_minutes": minutes,
                             "process": process})
    return observations


def _features(row: dict, model: str, families: tuple[str, ...]) -> list[float]:
    values = [math.log1p(row["story_points"])]
    if model in ("story_points_llm", "post_execution_diagnostic"):
        values += [float(row["llm"] == name) for name in families[1:]]
    if model == "post_execution_diagnostic":
        values += [math.log1p(row["process"][name]) for name in PROCESS]
    return values


def _fit(rows: list[dict], model: str, families: tuple[str, ...]) -> dict:
    if model == "training_median":
        return {"model": model, "value": statistics.median(r["actual_minutes"] for r in rows)}
    x = [_features(r, model, families) for r in rows]
    columns = len(x[0])
    if len(x) <= columns + 1:
        raise ValueError("too few training examples")
    means = [statistics.mean(row[j] for row in x) for j in range(columns)]
    scales = [statistics.pstdev(row[j] for row in x) or 1.0 for j in range(columns)]
    design = [[1.0] + [(row[j] - means[j]) / scales[j] for j in range(columns)]
              for row in x]
    target = [math.log(row["actual_minutes"]) for row in rows]
    dim = columns + 1
    ridge = 1.0
    gram = [[math.fsum(row[i] * row[j] for row in design)
             + (ridge if i == j and i > 0 else 0.0)
             for j in range(dim)] for i in range(dim)]
    rhs = [math.fsum(row[i] * y for row, y in zip(design, target)) for i in range(dim)]
    return {"model": model, "coefficient": _solve(gram, rhs),
            "means": means, "scales": scales}


def _predict(row: dict, fit: dict, families: tuple[str, ...]) -> float:
    if fit["model"] == "training_median":
        return fit["value"]
    features = _features(row, fit["model"], families)
    linear = fit["coefficient"][0] + math.fsum(
        (x - mean) / scale * weight
        for x, mean, scale, weight in zip(
            features, fit["means"], fit["scales"], fit["coefficient"][1:]
        )
    )
    value = math.exp(linear)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("numerical failure in HIE prediction")
    return value


def benchmark_hie_tasks(rows: list[dict], folds: int = 5) -> dict:
    """Cross-validate by developer, not by row. Task-family leakage remains unknown."""
    if not isinstance(rows, list) or len(rows) < 30:
        raise ValueError("need at least 30 real task observations")
    developers = sorted({r["developer"] for r in rows})
    families = tuple(sorted({r["llm"] for r in rows}))
    if len(developers) < folds or len(families) < 2 or not 3 <= folds <= 8:
        raise ValueError("insufficient developer/LLM diversity")
    assignment = {dev: i % folds for i, dev in enumerate(developers)}
    paired = {name: [] for name in MODELS}
    fold_info = []
    for k in range(folds):
        train = [r for r in rows if assignment[r["developer"]] != k]
        test = [r for r in rows if assignment[r["developer"]] == k]
        if not train or not test:
            raise ValueError("empty developer-held-out fold")
        fold_info.append({"fold": k,
                          "training_developers": len({r["developer"] for r in train}),
                          "held_out_developers": len({r["developer"] for r in test}),
                          "held_out_tasks": len(test)})
        for name in MODELS:
            fitted = _fit(train, name, families)
            paired[name].extend((r["actual_minutes"], _predict(r, fitted, families))
                                for r in test)
    metrics = {name: _metrics([y for y, _ in values], [p for _, p in values])
               for name, values in paired.items()}
    baseline = metrics["story_points"]["log_rmse"]
    return {
        "domain": "alaswad_hie_2026_task_duration",
        "status": "exploratory_domain_specific_task_benchmark",
        "tasks": len(rows), "developers": len(developers), "llms": list(families),
        "folds": folds, "validation": "held-out developers; task/repository identities unknown",
        "fold_details": fold_info,
        "outcome": "human task-completion time in minutes",
        "metrics": metrics,
        "log_rmse_change_relative_to_story_points": {
            name: metrics[name]["log_rmse"] / baseline - 1 for name in MODELS
        },
        "predictor_timing": {
            "story_points": "pre-execution",
            "story_points_llm": "pre-execution after LLM assignment",
            "post_execution_diagnostic": "RETROSPECTIVE ONLY: process indicators measured during execution",
        },
        "limitations": [
            "This is a task-level explanatory benchmark, not an AI-native COCOMO project calibration.",
            "Process predictors may be consequences of elapsed work: never use diagnostic scores as ex-ante forecasting performance.",
            "The source CSV lacks task and repository identifiers: developer holdouts cannot prevent repeated-task leakage.",
            "No human-only controls, therefore no causal AI productivity effect is identifiable.",
            "No independently audited acceptance or machine expenditure is reported.",
            "The source paper itself treats predictive modeling as exploratory rather than validated.",
        ],
    }
