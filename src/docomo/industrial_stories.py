"""Evaluate the original Mendeley ten-project industrial user-story estimates.

Only observed historical person-hours are outcomes. ChatGPT/DeepSeek/Copilot/
Gemini columns are *effort predictions*, not time spent coding with AI.
The original workbook must be supplied and SHA-256-pinned by the data owner;
there is intentionally no hard-coded guessed v2 file digest or worksheet layout.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .calibration import _metrics
from .xlsx_source import read_xlsx_sheet

DOI = "10.17632/ytmwsf2997.2"
SOURCE_URL = "https://data.mendeley.com/datasets/ytmwsf2997/2"
METHODS = ("human_expert", "planning_poker", "chatgpt", "deepseek", "copilot", "gemini")
REQUIRED = ("project_id", "story_id", "actual_person_hours", *METHODS)
EXPECTED_PROJECTS = 10
MIN_STORIES = 101


def _nonblank(value: Any, label: str) -> str:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{label} cannot be empty/boolean")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"{label} cannot be a fractional identifier")
        return str(int(value))
    text = str(value).strip()
    if not text:
        raise ValueError(f"{label} cannot be empty")
    return text


def _hours(value: Any, label: str) -> float:
    if type(value) not in (float, int):
        raise ValueError(f"{label} must be a numeric Excel cell in person-hours, not text")
    amount = float(value)
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError(f"{label} must be positive finite person-hours")
    return amount


def _schema(mapping: Mapping[str, Any]) -> dict:
    if not isinstance(mapping, Mapping):
        raise ValueError("source mapping must be an object")
    if set(mapping) != {"schema_version", "dataset_doi", "source_version",
                        "source_sha256", "worksheet", "header_row", "columns"}:
        raise ValueError("mapping must declare exact version, SHA256, worksheet and column names")
    if (mapping["schema_version"] != "1.0" or mapping["dataset_doi"] != DOI
            or type(mapping["source_version"]) is not int or mapping["source_version"] != 2):
        raise ValueError("this adapter requires the original Mendeley dataset v2")
    sha = mapping["source_sha256"]
    if (not isinstance(sha, str) or len(sha) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in sha)):
        raise ValueError("source_sha256 must be the independently recorded original workbook digest")
    sheet = mapping["worksheet"]
    if not isinstance(sheet, str) or not sheet.strip():
        raise ValueError("worksheet must be a named existing visible source worksheet")
    header_row = mapping["header_row"]
    if type(header_row) is not int or not 1 <= header_row <= 1000:
        raise ValueError("header_row must be an explicit Excel row number")
    columns = mapping["columns"]
    if not isinstance(columns, Mapping) or set(columns) != set(REQUIRED):
        raise ValueError("columns must map project ID, story ID, actual effort and all six original estimators")
    if any(not isinstance(v, str) or not v.strip() for v in columns.values()):
        raise ValueError("all source column headings must be nonblank")
    if len(set(columns.values())) != len(columns):
        raise ValueError("the source columns must be distinct")
    return dict(mapping)


def import_industrial_stories(workbook: str | Path,
                              mapping: Mapping[str, Any]) -> dict:
    """Import all original XLSX observations and fail closed on unknown rows.

    The importer does not infer worksheet layout, effort units, missing values
    or formulas. It cannot establish provenance of the source author from an
    internally provided file alone.
    """
    config = _schema(mapping)
    sheet = read_xlsx_sheet(workbook, sheet_name=config["worksheet"])
    if sheet["source_sha256"].lower() != config["source_sha256"].lower():
        raise ValueError("original Mendeley v2 XLSX SHA256 differs from preregistered source")
    start = config["header_row"]
    headers = sheet["rows"].get(start)
    if not headers:
        raise ValueError("declared source header row was not found")
    heading_to_col = {}
    for col, cell in headers.items():
        if (start, col) in sheet["formula_cells"]:
            raise ValueError("header row may not contain formulas")
        if isinstance(cell, str) and cell.strip():
            if cell in heading_to_col:
                raise ValueError(f"duplicate source worksheet heading: {cell}")
            heading_to_col[cell] = col
    missing = sorted(set(config["columns"].values()) - set(heading_to_col))
    if missing:
        raise ValueError(f"original source column headings were not found: {missing}")
    cols = {field: heading_to_col[header] for field, header in config["columns"].items()}
    seen = set()
    records = []
    row_count = 0
    for row_number in sorted(sheet["rows"]):
        if row_number <= start:
            continue
        cells = sheet["rows"][row_number]
        if not cells or all(cells.get(col) is None for col in cols.values()):
            continue
        row_count += 1
        for field, col in cols.items():
            if (row_number, col) in sheet["formula_cells"]:
                raise ValueError(f"formula-derived source observation not allowed: row {row_number} field {field}")
        project = _nonblank(cells.get(cols["project_id"]), f"row {row_number} project_id")
        story = _nonblank(cells.get(cols["story_id"]), f"row {row_number} story_id")
        if (project, story) in seen:
            raise ValueError(f"duplicate original project/story pair {project}/{story}")
        seen.add((project, story))
        actual = _hours(cells.get(cols["actual_person_hours"]), f"row {row_number} actual person-hours")
        estimates = {
            method: _hours(cells.get(cols[method]), f"row {row_number} {method} person-hours")
            for method in METHODS
        }
        records.append({
            "record_id": f"{project}::{story}",
            "project_id": project, "story_id": story,
            "source_excel_row": row_number, "actual_person_hours": actual,
            "original_person_hour_estimates": estimates,
            "source_doi": DOI, "source_version": 2,
            "observed_ai_development_cost": False,
            "ai_columns_are_predictions_not_development": True,
        })
    projects = {r["project_id"] for r in records}
    if len(projects) != EXPECTED_PROJECTS or len(records) < MIN_STORIES:
        raise ValueError(
            f"expected ten real industrial projects and over 100 complete user stories, got "
            f"{len(projects)} projects and {len(records)} complete stories"
        )
    return {
        "schema_version": "1.0",
        "status": "original_workbook_checksum_verified_source_origin_not_independently_authenticated",
        "source_doi": DOI, "source_url": SOURCE_URL,
        "source_license": "CC BY 4.0", "source_sha256": sheet["source_sha256"],
        "source_version": 2, "worksheet": config["worksheet"],
        "source_header_row": start, "source_rows_imported": row_count,
        "records": records, "projects": len(projects), "stories": len(records),
        "methods": list(METHODS), "human_effort_unit": "person_hours",
        "reported_hidden_sheets": sheet["hidden_sheets"],
        "warnings": [
            "Dataset origin and original developer effort logs have not been independently authenticated.",
            "All AI model columns are retrospective effort estimates, not evidence of AI-assisted coding performance.",
            "Identical prompts after delivery may give hindsight advantage; timing/protocol requires study review.",
            "No human-only and AI-enabled coding treatments are identified by this dataset.",
            "Only source-manifest and byte integrity were checked; ten project clusters remain a small sample.",
        ],
    }


def _pairs(rows: list[dict], method: str) -> tuple[list[float], list[float]]:
    return [r["actual_person_hours"] for r in rows], [
        r["original_person_hour_estimates"][method] for r in rows
    ]


def _project_metrics(rows: list[dict], method: str) -> dict:
    actual, predicted = _pairs(rows, method)
    total_actual = math.fsum(actual)
    total_predicted = math.fsum(predicted)
    return {
        **_metrics(actual, predicted),
        "sum_actual_person_hours": total_actual,
        "sum_predicted_person_hours": total_predicted,
        "total_signed_error_person_hours": total_predicted - total_actual,
        "total_absolute_error_person_hours": abs(total_predicted - total_actual),
        "median_signed_story_error_person_hours": statistics.median(
            p - y for y,p in zip(actual,predicted)
        ),
    }


def evaluate_industrial_estimators(imported: Mapping[str, Any],
                                    *, bootstrap_replicates: int = 1000,
                                    seed: int = 2026) -> dict:
    """Fair paired source-estimator comparison by ten entire project clusters.

    Zero learned coefficients, so this does NOT call its retrospective scoring
    an external forward prediction trial. Bootstrap is descriptive only.
    """
    if (not isinstance(imported, Mapping)
            or imported.get("status") != "original_workbook_checksum_verified_source_origin_not_independently_authenticated"):
        raise ValueError("requires the original checksum-verified project/story corpus")
    if type(bootstrap_replicates) is not int or not 100 <= bootstrap_replicates <= 10000:
        raise ValueError("bootstrap_replicates must be between 100 and 10000")
    records = imported.get("records")
    if not isinstance(records, list) or len(records) < MIN_STORIES:
        raise ValueError("incomplete original story corpus")
    grouped = defaultdict(list)
    for r in records:
        grouped[r["project_id"]].append(r)
    if len(grouped) != EXPECTED_PROJECTS:
        raise ValueError("require all ten original industrial projects")
    per_project = {
        project: {method: _project_metrics(rows, method) for method in METHODS}
        for project, rows in sorted(grouped.items())
    }
    global_scores = {method: _project_metrics(records,method) for method in METHODS}
    # Equal project weighting avoids rewarding the model that does best
    # on a single project with many stories.
    equal_project = {
        method: {
            "mean_project_mae_person_hours": statistics.mean(
                per_project[p][method]["mae"] for p in grouped
            ),
            "mean_project_log_rmse": statistics.mean(
                per_project[p][method]["log_rmse"] for p in grouped
            ),
            "mean_project_absolute_total_error_person_hours": statistics.mean(
                per_project[p][method]["total_absolute_error_person_hours"] for p in grouped
            ),
        }
        for method in METHODS
    }
    rng = random.Random(seed)
    project_ids = sorted(grouped)
    intervals = {}
    for challenger in METHODS:
        if challenger == "human_expert":
            continue
        differences = []
        for _ in range(bootstrap_replicates):
            sampled_projects = rng.choices(project_ids,k=len(project_ids))
            differences.append(statistics.mean(
                per_project[project]["human_expert"]["mae"]
                - per_project[project][challenger]["mae"]
                for project in sampled_projects
            ))
        differences.sort()
        lo = differences[int(.025*len(differences))]
        hi = differences[min(len(differences)-1,math.ceil(.975*len(differences))-1)]
        intervals[challenger] = {
            "estimator": challenger,
            "reference": "human_expert",
            "mean_project_mae_reduction_person_hours": statistics.mean(
                per_project[p]["human_expert"]["mae"] - per_project[p][challenger]["mae"]
                for p in project_ids
            ),
            "paired_project_cluster_bootstrap_95pct": [lo,hi],
            "contains_zero":lo <= 0 <= hi,
            "replicates": bootstrap_replicates,
        }
    return {
        "status": "retrospective_original_estimate_accuracy_not_ai_coding_productivity",
        "source_doi":DOI,
        "source_sha256":imported["source_sha256"],
        "sample_unit":"user_story_clustered_in_original_project",
        "projects":len(grouped), "stories":len(records),
        "effort_unit":"person_hours",
        "aggregated_story_weighted":global_scores,
        "per_project":per_project,
        "equal_project_weighted":equal_project,
        "paired_bootstrap_reference_human_expert":intervals,
        "bootstrap_seed":seed,
        "project_identity_held_out_when_model_is_fitted":True,
        "current_comparison_refits_no_models":True,
        "independent_prospective_estimates_authenticated":False,
        "ai_development_acceleration_identified":False,
        "calibrated_full_project_ai_cost":False,
        "warnings":[
            "Original study estimates, not new independently registered prospective model forecasts.",
            "Projects, not user stories, are the independent bootstrap units; n=10 is still small.",
            "Do not decide a new predictor by selecting its best result on these same ten projects.",
            "All negative/null differences and source expert baseline must remain visible.",
            "AI estimators did not necessarily write software; no causal productivity effect can be computed.",
            "No independent audit of original timesheets or original prediction timing has been performed.",
        ],
    }
