"""Source-pinned real historical project observations, never pooled across units.

Every row is from published datasets containing completed projects and measured
effort, not a fabricated synthetic example. Whole-project effort is not the same
label as task acceptance, human-AI acceleration, or independently audited cost.
"""
from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

from .calibration import DRIVERS, read_cocomo81
from .datasets import SOURCES, fetch_dataset

PROJECT_SOURCES = ("cocomo81", "nasa93", "china", "desharnais")
EXPECTED_ROWS = {"cocomo81": 63, "nasa93": 93, "china": 499, "desharnais": 81}
RATING_ORDER = ("vl", "l", "n", "h", "vh", "xh")
NASA_DRIVERS = tuple(DRIVERS)


def _positive(value: Any, label: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label}: requires numerical value") from error
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{label}: requires positive finite value")
    return numeric


def _nonnegative(value: Any, label: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label}: requires numerical value") from error
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{label}: requires nonnegative finite value")
    return numeric


def _arff(path: Path) -> list[dict[str, str]]:
    attributes: list[str] = []
    data = []
    is_data = False
    with path.open(encoding="utf-8-sig") as file:
        for raw in file:
            line = raw.strip()
            if not line or line.startswith("%"):
                continue
            if not is_data:
                if line.lower().startswith("@attribute"):
                    attributes.append(line.split(None, 2)[1].lower())
                elif line.lower() == "@data":
                    is_data = True
            else:
                values = next(csv.reader([line]))
                if len(values) != len(attributes):
                    raise ValueError("ARFF data row width differs from @attribute count")
                data.append(dict(zip(attributes, values)))
    if not is_data or not attributes or not data:
        raise ValueError("ARFF dataset lacks attributes or data")
    return data


def _record(source: str, identifier: int, effort: float, unit: str,
            size: float, size_unit: str, features: dict[str, float],
            split_group: str, descriptor: dict[str, Any]) -> dict:
    return {
        "record_id": f"{source}:{identifier}",
        "source_id": source,
        "source_project_identifier": identifier,
        "observation_type": "completed_historical_project",
        "cost_label": "observed_human_effort",
        "effort": effort, "effort_unit": unit,
        "size": size, "size_unit": size_unit,
        "planning_proxy_features": features,
        "holdout_group": split_group,
        "descriptors": descriptor,
        "independent_acceptance_verified": False,
        "ai_use_measured": False,
        "external_cost_ledger_audited": False,
    }


def read_historical_projects(name: str, path: Path) -> list[dict]:
    if name not in PROJECT_SOURCES:
        raise ValueError(f"{name} is not a historical project effort dataset")
    rows = []
    if name == "cocomo81":
        for entry in read_cocomo81(path):
            rows.append(_record(
                name, entry["id"], entry["person_months"], "person_months",
                entry["kloc"], "KSLOC",
                {"log_effort_adjustment_factor": math.log(entry["eaf"]),
                 "embedded_mode": float(entry["mode"] == "embedded"),
                 "semidetached_mode": float(entry["mode"] == "semidetached")},
                f"id_mod5:{entry['id'] % 5}",
                {"mode": entry["mode"], "fold_policy": "id_mod5_not_prospective"},
            ))
    elif name == "nasa93":
        raw = _arff(path)
        required = {"recordnumber", "year", "mode", "equivphyskloc",
                    "act_effort", *NASA_DRIVERS}
        if any(not required.issubset(row) for row in raw):
            raise ValueError("NASA93 required COCOMO cost-driver ratings missing")
        for row in raw:
            mode = row["mode"].lower()
            if mode not in ("organic", "semidetached", "embedded"):
                raise ValueError(f"NASA93 invalid development mode: {mode}")
            ordinal = {}
            for driver in NASA_DRIVERS:
                value = row[driver].lower()
                if value not in RATING_ORDER:
                    raise ValueError(f"NASA93 driver {driver} has invalid rating {value}")
                ordinal[f"driver_{driver}"] = float(RATING_ORDER.index(value))
            features = {**ordinal, "embedded_mode": float(mode == "embedded"),
                        "semidetached_mode": float(mode == "semidetached")}
            year = int(row["year"])
            rows.append(_record(
                name, int(row["recordnumber"]), _positive(row["act_effort"], "act_effort"),
                "person_months", _positive(row["equivphyskloc"], "equivphyskloc"), "KSLOC",
                features, f"year:{year}", {"year": year, "mode": mode,
                                           "fold_policy": "leave_one_completion_year_out"},
            ))
    elif name == "china":
        raw = _arff(path)
        required = {"id", "afp", "effort", "n_effort", "input", "output",
                    "enquiry", "file", "interface"}
        if any(not required.issubset(row) for row in raw):
            raise ValueError("China project data lack required AFP / Effort columns")
        for row in raw:
            identifier = int(row["id"])
            # Actual Effort is the observed label, NEVER normalised N_effort.
            features = {field: math.log1p(_nonnegative(row[field], field))
                        for field in ("input", "output", "enquiry", "file", "interface")}
            rows.append(_record(
                name, identifier, _positive(row["effort"], "Effort"), "person_hours",
                _positive(row["afp"], "AFP"), "AFP_function_points",
                features, f"id_mod5:{identifier % 5}",
                {"fold_policy": "id_mod5_not_prospective",
                 "n_effort_excluded": True, "project_dates_unavailable": True},
            ))
    elif name == "desharnais":
        with path.open(newline="", encoding="utf-8-sig") as file:
            raw = list(csv.DictReader(file))
        required = {"Project", "Effort", "PointsAjust", "YearEnd", "TeamExp",
                    "ManagerExp", "Transactions", "Entities", "Language"}
        if any(not required.issubset(row) for row in raw):
            raise ValueError("Desharnais missing project/effort/points fields")
        for row in raw:
            team = int(row["TeamExp"])
            manager = int(row["ManagerExp"])
            if team < -1 or manager < -1:
                raise ValueError("unexpected Desharnais experience sentinel")
            features = {
                "team_exp": float(max(0, team)), "manager_exp": float(max(0, manager)),
                "team_exp_missing": float(team == -1),
                "manager_exp_missing": float(manager == -1),
                "transactions": math.log1p(_nonnegative(row["Transactions"], "Transactions")),
                "entities": math.log1p(_nonnegative(row["Entities"], "Entities")),
                "language_two": float(row["Language"] == "2"),
                "language_three": float(row["Language"] == "3"),
            }
            if row["Language"] not in ("1", "2", "3"):
                raise ValueError("Desharnais unexpected programming language")
            year = int(row["YearEnd"])
            rows.append(_record(
                name, int(row["Project"]), _positive(row["Effort"], "Effort"), "person_hours",
                _positive(row["PointsAjust"], "PointsAjust"), "adjusted_function_points",
                features, f"year:{year}", {"completion_year_code": year,
                                           "fold_policy": "leave_one_completion_year_out",
                                           "project_length_excluded": True},
            ))
    if len(rows) != EXPECTED_ROWS[name]:
        raise ValueError(f"{name} expected {EXPECTED_ROWS[name]} records, got {len(rows)}")
    ids = [r["record_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{name} contains duplicate project identifiers")
    return rows


def load_project_corpus(directory: Path, *, offline: bool = False) -> dict:
    projects: list[dict] = []
    catalog = []
    for name in PROJECT_SOURCES:
        source = SOURCES[name]
        records = read_historical_projects(name, fetch_dataset(name, directory, offline))
        projects.extend(records)
        catalog.append({
            "source_id": name,
            "project_observations": len(records),
            "effort_unit": records[0]["effort_unit"],
            "size_unit": records[0]["size_unit"],
            "pinned_commit": source["commit"],
            "pinned_git_blob_sha1": source["git_blob_sha1"],
            "url": f"https://github.com/{source['repository']}/blob/{source['commit']}/{source['path']}",
            "level": "observed_historical_project_effort",
            "accepted_output_oracle": "not_reported",
        })
    return {
        "schema_version": "1.0",
        "status": "actual_published_historical_cost_observations",
        "project_observations": len(projects),
        "distinct_independent_projects_claimed": None,
        "possible_overlaps_between_datasets": ["cocomo81", "nasa93"],
        "datasets": catalog,
        "records": projects,
        "limitations": [
            "These are real historical completed-project effort observations, not AI-native cost labels.",
            "Project-unit labels must never be pooled without a justified model and provenance deduplication.",
            "Some historical sizing/complexity features are retrospective and not verified as available at project planning.",
            "COCOMO81 and NASA93 may share projects; record identifiers cannot prove cross-dataset independence.",
            "No independent software-acceptance, review, machine spend, original labour ledgers or modern agent outcomes are supplied.",
        ],
    }
