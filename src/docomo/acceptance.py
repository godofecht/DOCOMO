"""Acceptance-probability component for disjoint project-cohort evaluation.

Trains solely on complete training projects, calibrates intercept solely on
calibration projects, and scores held-out test projects once. These estimates
are observational, conditional on protocol and study population, not causal.
"""
from __future__ import annotations

import math
import statistics
from typing import Any

from .calibration import _solve
from .complexity import _wilson_interval


def _sigmoid(z: float) -> float:
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def _features(record: dict) -> list[float]:
    f = record["planning_features"]
    return [
        math.log1p(f["functional_units"]),
        math.log1p(f["dependency_edges"]),
        math.log1p(f["verification_obligations"]),
        math.log1p(f["ambiguous_requirements"]),
        float(record["workflow"] == "ai_assisted"),
        float(record["workflow"] == "agent_delegated"),
    ]


def _dataset(rows: list[dict]) -> tuple[list[list[float]], list[int]]:
    return [_features(row) for row in rows], [int(row["acceptance"]["accepted"]) for row in rows]


def _standardize(raw: list[list[float]]) -> tuple[list[float], list[float], list[list[float]]]:
    if not raw:
        raise ValueError("empty acceptance training set")
    means = [statistics.mean(row[j] for row in raw) for j in range(len(raw[0]))]
    scales = [statistics.pstdev(row[j] for row in raw) or 1.0 for j in range(len(raw[0]))]
    design = [[1.0] + [(row[j] - means[j]) / scales[j] for j in range(len(means))]
              for row in raw]
    return means, scales, design


def _loss(design: list[list[float]], labels: list[int],
          beta: list[float], ridge: float) -> float:
    outcome = 0.5 * ridge * math.fsum(v*v for v in beta[1:])
    for x, y in zip(design, labels):
        z = math.fsum(v*b for v,b in zip(x,beta))
        outcome += max(z, 0.0) + math.log1p(math.exp(-abs(z))) - y*z
    return outcome


def _fit(train: list[dict]) -> dict:
    raw, labels = _dataset(train)
    means, scales, x = _standardize(raw)
    dimension = len(x[0])
    beta = [0.0] * dimension
    count = len(labels)
    beta[0] = math.log(sum(labels) / (count - sum(labels)))
    ridge = 2.0
    for iteration in range(80):
        probs = [_sigmoid(math.fsum(v*b for v,b in zip(row,beta))) for row in x]
        weights = [p*(1-p) for p in probs]
        matrix = [[math.fsum(w*row[i]*row[j] for w,row in zip(weights,x))
                   + (ridge if i == j and i > 0 else 0.0)
                   for j in range(dimension)] for i in range(dimension)]
        gradient = [math.fsum(row[j]*(y-p) for row,y,p in zip(x,labels,probs))
                    - (ridge*beta[j] if j > 0 else 0.0)
                    for j in range(dimension)]
        delta = _solve(matrix, gradient)
        old_loss = _loss(x, labels, beta, ridge)
        scale = 1.0
        for _ in range(30):
            candidate = [b + scale*d for b,d in zip(beta,delta)]
            if _loss(x, labels, candidate, ridge) <= old_loss + 1e-10:
                beta = candidate
                break
            scale /= 2.0
        else:
            raise ValueError("acceptance logistic Newton step failed to descend")
        if max(abs(scale*d) for d in delta) < 1e-7:
            break
    else:
        raise ValueError("acceptance logistic regression failed to converge")
    return {"coefficients": beta, "means": means, "scales": scales, "ridge_penalty": ridge,
            "training_acceptance_rate": sum(labels)/len(labels)}


def _score(row: dict, fit: dict, offset: float = 0.0) -> float:
    values = _features(row)
    z = fit["coefficients"][0] + offset + math.fsum(
        (v-m)/s*b
        for v,m,s,b in zip(values, fit["means"], fit["scales"],
                           fit["coefficients"][1:])
    )
    return _sigmoid(z)


def _offset(calibration: list[dict], fit: dict) -> float:
    # Intercept-only calibration by maximizing calibration-sample Bernoulli likelihood.
    labels = [int(r["acceptance"]["accepted"]) for r in calibration]
    lo, hi = -40.0, 40.0
    base = [_score(r, fit) for r in calibration]
    logits = [math.log(p/(1-p)) for p in base]
    target = sum(labels)
    for _ in range(100):
        middle = (lo+hi)/2
        expected = math.fsum(_sigmoid(z+middle) for z in logits)
        if expected < target:
            lo = middle
        else:
            hi = middle
    return (lo+hi)/2


def _metrics(rows: list[dict], forecast: list[float]) -> dict:
    labels = [int(r["acceptance"]["accepted"]) for r in rows]
    if len(labels) != len(forecast) or not labels:
        raise ValueError("invalid acceptance comparison data")
    clipped = [min(max(float(p), 1e-12), 1-1e-12) for p in forecast]
    n = len(labels)
    return {
        "n": n,
        "empirical_acceptance_rate": math.fsum(labels)/n,
        "mean_forecast_acceptance_probability": math.fsum(forecast)/n,
        "brier_score": math.fsum((y-p)**2 for y,p in zip(labels,forecast))/n,
        "mean_log_loss": -math.fsum(
            y*math.log(p)+(1-y)*math.log1p(-p)
            for y,p in zip(labels,clipped)
        )/n,
        "observed_acceptance_wilson_95pct": list(_wilson_interval(sum(labels), n, .95)),
    }


def evaluate_acceptance(train: list[dict], calibration: list[dict],
                        test: list[dict]) -> dict[str, Any]:
    """Internal post-split estimator; caller must validate independent repositories.

    Small cohorts and class imbalance fail closed: no fictional confidence.
    """
    labels_train = [int(r["acceptance"]["accepted"]) for r in train]
    labels_cal = [int(r["acceptance"]["accepted"]) for r in calibration]
    base = {"status": "insufficient_acceptance_evidence",
            "calibration_status": "not_externally_validated",
            "train_attempts": len(train), "calibration_attempts": len(calibration),
            "test_attempts": len(test),
            "warnings": [
                "Observed acceptance labels must be externally audited.",
                "Acceptance depends on local protocol, distribution and project selection.",
                "No causal AI productivity claim or unconditional completion-cost prediction.",
            ]}
    if (len(train) < 50 or sum(labels_train) < 8 or len(train)-sum(labels_train) < 8
            or len(calibration) < 20 or sum(labels_cal) < 4
            or len(calibration)-sum(labels_cal) < 4):
        base["reason"] = "Requires >=50 train observations with >=8 of each outcome and >=20 calibration observations with >=4 of each outcome."
        base["coefficients"] = None
        return base
    fit = _fit(train)
    intercept_shift = _offset(calibration, fit)
    pooled = sum(labels_train)/len(train)
    models = {
        "train_only_prevalence": [pooled]*len(test),
        "train_only_logistic": [_score(r,fit) for r in test],
        "calibration_intercept_adjusted_logistic": [_score(r,fit,intercept_shift) for r in test],
    }
    return {
        "status": "held_out_acceptance_evaluated_not_certified",
        "calibration_status": "not_externally_validated",
        "train_attempts": len(train), "calibration_attempts": len(calibration),
        "test_attempts": len(test),
        "train_coefficients": fit["coefficients"],
        "train_standardization": {"means":fit["means"],"scales":fit["scales"]},
        "train_only_base_rate": pooled,
        "calibration_only_intercept_shift": intercept_shift,
        "test_metrics": {name:_metrics(test,probabilities) for name,probabilities in models.items()},
        "forecast_probabilities": models,
        "warnings": [
            "All outcome labels are self-attested until independently audited.",
            "Train/calibrate/test group independence must be established by parent holdout validator.",
            "Adjustment uses the calibration set only, never the test outcomes.",
            "Models describe observed acceptance under a fixed protocol, not causal AI productivity.",
            "These probability scores do not establish unconditional future project cost.",
            "Repeated task and organization dependencies or changed model versions may break transportability.",
            "Test metrics are descriptive and not sufficient certification of probability calibration.",
        ],
    }
