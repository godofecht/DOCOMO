"""Strict three-way, repository-disjoint evaluation of accepted project effort.

No inference about causality, proof of true acceptance, or unconditional project cost.
Split conformal intervals are calibrated using per-repository *maximum* residuals:
under exchangeable independent repositories, this targets coverage for a new
repository as a unit, conditional on the fixed trained model.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .calibration import _metrics, _ols
from .manifests import validate_project
from .native import _vector, _prediction
from .acceptance import evaluate_acceptance

MODELS = ("docomo_scope", "size_only", "cocomo2_nominal_assumptions")


def _timestamp(raw: Any, label: str) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label} must be ISO 8601") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _rate(records: list[dict]) -> dict:
    count = len(records)
    successes = sum(record["acceptance"]["accepted"] for record in records)
    if not count:
        raise ValueError("empty project split")
    return {"total_attempted_projects": count, "accepted_projects": successes,
            "unaccepted_projects": count - successes, "empirical_acceptance_rate": successes / count,
            "total_human_minutes_including_unaccepted": math.fsum(
                r["outcome"]["total_human_minutes"] for r in records),
            "total_machine_cost_including_unaccepted": math.fsum(
                r["outcome"]["machine_cost"] for r in records),
            "observed_human_minutes_per_accepted_deliverable_across_all_attempts": (
                math.fsum(r["outcome"]["total_human_minutes"] for r in records) / successes
                if successes else None),
            "observed_machine_cost_per_accepted_deliverable_across_all_attempts": (
                math.fsum(r["outcome"]["machine_cost"] for r in records) / successes
                if successes else None)}


def _fit(records: list[dict], model: str) -> list[float] | None:
    if model == "cocomo2_nominal_assumptions":
        return None
    accepted = [r for r in records if r["acceptance"]["accepted"]]
    x = [_vector(r, model) for r in accepted]
    y = [math.log(r["outcome"]["total_human_minutes"]) for r in accepted]
    return _ols(x, y)


def _group_quantile(calibration: list[dict], name: str, beta: list[float] | None,
                    target: float) -> dict:
    by_repo = defaultdict(list)
    for row in calibration:
        if not row["acceptance"]["accepted"]:
            continue
        prediction = _prediction(row, name, beta)
        actual = row["outcome"]["total_human_minutes"]
        by_repo[row["snapshot"]["repository"]].append(abs(math.log(actual/prediction)))
    if not by_repo:
        raise ValueError("no accepted calibration projects")
    residuals = sorted(max(values) for values in by_repo.values())
    k = math.ceil((len(residuals) + 1) * target - 1e-12)
    if k > len(residuals):
        return {"status": "insufficient_calibration_repositories_for_finite_interval",
                "accepted_calibration_repositories": len(residuals),
                "required_repository_groups": math.ceil(target/(1-target) - 1e-9),
                "nominal_repository_coverage": target, "log_radius": None}
    return {"status": "finite_interval_available", "accepted_calibration_repositories": len(residuals),
            "nominal_repository_coverage": target,
            "residual_rank": k,
            "log_radius": residuals[k-1],
            "method": "split_conformal_repository_max_absolute_log_error"}


def evaluate_holdout(experiment: Mapping[str, Any], *, allow_synthetic: bool = False) -> dict:
    """Evaluate a *preselected* effort model on untouched, repository-disjoint projects.

    Accepted-conditional human effort and a separate, optional observed
    acceptance probability model. No unconditional project cost or schedule.
    Caller assertions about independent acceptance/preregistration are NOT audited.
    """
    if not isinstance(experiment, Mapping) or experiment.get("schema_version") != "1.0":
        raise ValueError("experiment must be a versioned object")
    model = experiment.get("selected_model")
    if model not in MODELS:
        raise ValueError(f"selected_model must be one of {MODELS}")
    confidence = experiment.get("target_repository_coverage", 0.9)
    if type(confidence) not in (int, float) or not math.isfinite(float(confidence)) or not .5 <= confidence < 1:
        raise ValueError("target_repository_coverage must be in [0.5, 1)")
    confidence = float(confidence)
    registered_at = _timestamp(experiment.get("registered_at"), "registered_at")
    registration_uri = experiment.get("registration_uri")
    if not isinstance(registration_uri, str) or not registration_uri.startswith("https://"):
        raise ValueError("registration_uri must be an explicit HTTPS link to the protocol")
    splits: dict[str, list[dict]] = {}
    for role in ("train", "calibration", "test"):
        raw = experiment.get(role)
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"{role} must be a non-empty project manifest list")
        if not allow_synthetic and any(
            isinstance(r, Mapping) and r.get("synthetic") is True for r in raw
        ):
            raise ValueError("synthetic projects cannot support production holdout evaluation")
        splits[role] = [validate_project(r) for r in raw]

    grouped = {role: {r["snapshot"]["repository"] for r in rows} for role, rows in splits.items()}
    if any(grouped[a] & grouped[b] for a, b in (
        ("train", "calibration"), ("train", "test"), ("calibration", "test")
    )):
        raise ValueError("train, calibration and test must have disjoint repositories")
    all_rows = [r for rows in splits.values() for r in rows]
    ids = [r["project_id"] for r in all_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("a project_id appears in multiple observations or splits")
    if len({r["domain"] for r in all_rows}) != 1:
        raise ValueError("all projects must have a shared declared domain")
    if len({r["outcome"]["currency"] for r in all_rows}) != 1:
        raise ValueError("currency must be common and explicit")
    for role, rows in splits.items():
        for row in rows:
            timestamp = _timestamp(row["snapshot"]["planning_recorded_at"], "planning_recorded_at")
            if timestamp > registered_at and role != "test":
                raise ValueError("training and calibration planning dates must precede preregistration")
            if role == "test" and timestamp < registered_at:
                raise ValueError("test planning date precedes claimed preregistration; prospective status unsubstantiated")
            if row["acceptance"]["accepted"] and row["outcome"]["total_human_minutes"] <= 0:
                raise ValueError("accepted zero-human-time projects require a different outcome model")
            if model != "docomo_scope" and "equivalent_ksloc" not in row["planning_features"]:
                raise ValueError(f"{model} requires equivalent_ksloc in all project records")
    train, calibration, test = (splits[k] for k in ("train", "calibration", "test"))
    if len(grouped["train"]) < 8 or sum(r["acceptance"]["accepted"] for r in train) < 30:
        raise ValueError("training requires at least 8 repositories and 30 accepted projects")
    if len(grouped["test"]) < 4:
        raise ValueError("test requires at least 4 independent repositories")
    if sum(r["acceptance"]["accepted"] for r in calibration) < 10:
        raise ValueError("calibration requires at least 10 accepted projects")
    acceptance_evaluation = evaluate_acceptance(train, calibration, test)
    if not any(r["acceptance"]["accepted"] for r in test):
        return {"status": "no_test_accepted_deliveries", "test_outcomes": _rate(test),
                "model": model, "coefficients": None, "independent_audit": False,
                "acceptance_evaluation": acceptance_evaluation}
    fitted = _fit(train, model)
    quantile = _group_quantile(calibration, model, fitted, confidence)
    actual, forecasts = [], []
    observed_by_repo = defaultdict(list)
    for row in test:
        if not row["acceptance"]["accepted"]:
            continue
        prediction = _prediction(row, model, fitted)
        real = row["outcome"]["total_human_minutes"]
        actual.append(real)
        forecasts.append(prediction)
        observed_by_repo[row["snapshot"]["repository"]].append((real, prediction))
    intervals = {
        "status": quantile["status"],
        "calibration": quantile,
        "test_repository_coverage": None,
        "test_accepted_project_coverage": None,
        "bounds": None,
    }
    radius = quantile["log_radius"]
    if radius is not None:
        # The maximum residual of each held-out repository is the evaluation unit.
        groups = list(observed_by_repo.values())
        intervals["test_repository_coverage"] = sum(
            all(abs(math.log(y/p)) <= radius+1e-12 for y,p in pairs) for pairs in groups
        ) / len(groups)
        intervals["test_accepted_project_coverage"] = sum(
            abs(math.log(y/p)) <= radius+1e-12 for y,p in zip(actual, forecasts)
        ) / len(actual)
        intervals["bounds"] = [[p*math.exp(-radius), p*math.exp(radius)] for p in forecasts]
    return {
        "status": "synthetic_holdout_algorithm_test_only" if allow_synthetic
                  else "external_holdout_evaluated_pending_independent_audit",
        "calibration_status": "not_certified",
        "model": model, "coefficient_units": "log(human_minutes)",
        "training_only_coefficients": fitted,
        "experiment_registration": {"url": registration_uri, "claimed_registration_time": registered_at.isoformat(),
                                    "independently_verified": False},
        "repository_counts": {k: len(grouped[k]) for k in grouped},
        "split_counts": {k: _rate(rows) for k, rows in splits.items()},
        "test_metrics_conditional_on_acceptance": _metrics(actual, forecasts),
        "test_interval_evaluation": intervals,
        "test_accepted_repositories": len(observed_by_repo),
        "acceptance_evaluation": acceptance_evaluation,
        "domain": all_rows[0]["domain"],
        "warnings": [
            "Only the preselected model is evaluated. Choose all hyperparameters before looking at the test set.",
            "Split-conformal coverage assumes exchangeable repository groups; the data do not verify this assumption.",
            "Test coverage from few independent repositories has substantial statistical uncertainty.",
            "Intervals describe human effort CONDITIONAL ON acceptance, not unconditional delivery cost.",
            "Costs on unaccepted projects are reported, but no unconditional future project forecast is produced.",
            "Acceptance probabilities, when estimable, come from separately trained and calibrated observational labels.",
            "Registration and independent acceptance are self-attested and require external audit.",
            "Changing acceptance criteria, model versions, or project populations invalidates transportability.",
        ],
    }
