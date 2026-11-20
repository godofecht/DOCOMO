"""Empirical complexity as observed cost to accepted software behaviour.

Estimates are conditional on the acceptance protocol, task, participants, tools,
model versions and trial environment. These are not intrinsic task scores.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from statistics import NormalDist
from typing import Any


def _finite_nonnegative(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a nonnegative finite number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a nonnegative finite number")
    return number


def _probability(value: Any, name: str) -> float:
    number = _finite_nonnegative(value, name)
    if not 0 < number < 1:
        raise ValueError(f"{name} must be strictly between 0 and 1")
    return number


def _wilson_interval(successes: int, count: int, confidence: float) -> tuple[float, float]:
    z = NormalDist().inv_cdf((1.0 + confidence) / 2.0)
    p = successes / count
    denominator = 1.0 + z * z / count
    centre = (p + z * z / (2 * count)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * count)) / count) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def assess_complexity(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Compare observed strategies without fabricating an intrinsic complexity score.

    Mean total attempt cost / empirical success rate estimates cost per accepted
    outcome only under stationary, independent attempts with repeat-until-success.
    Qualification uses the Wilson binomial lower confidence bound. The latter
    describes uncertainty under independent Bernoulli trials, not guarantees.
    """
    if not isinstance(spec, Mapping):
        raise ValueError("assessment must be an object")
    target = _probability(spec.get("target_acceptance_probability"), "target_acceptance_probability")
    confidence = _probability(spec.get("confidence_level", 0.95), "confidence_level")
    hourly_rate = _finite_nonnegative(spec.get("human_hourly_rate"), "human_hourly_rate")
    strategies = spec.get("strategies")
    if not isinstance(strategies, list) or not strategies:
        raise ValueError("strategies must be a non-empty array")
    observations = []
    seen: set[str] = set()
    for strategy in strategies:
        if not isinstance(strategy, Mapping):
            raise ValueError("strategy must be an object")
        name = strategy.get("id")
        if not isinstance(name, str) or not name or name in seen:
            raise ValueError("strategy IDs must be non-empty and unique")
        seen.add(name)
        trials = strategy.get("trials")
        if not isinstance(trials, list) or not trials:
            raise ValueError(f"strategy {name} requires non-empty trials")
        success_count = 0
        human_minutes = 0.0
        machine_cost = 0.0
        elapsed_minutes = 0.0
        for i, trial in enumerate(trials):
            if not isinstance(trial, Mapping) or type(trial.get("accepted")) is not bool:
                raise ValueError(f"{name}.trials[{i}].accepted must be boolean")
            success_count += int(trial["accepted"])
            human_minutes += _finite_nonnegative(trial.get("human_minutes"), f"{name}.trials[{i}].human_minutes")
            machine_cost += _finite_nonnegative(trial.get("machine_cost"), f"{name}.trials[{i}].machine_cost")
            elapsed_minutes += _finite_nonnegative(trial.get("elapsed_minutes"), f"{name}.trials[{i}].elapsed_minutes")
        count = len(trials)
        total_cost = human_minutes * hourly_rate / 60.0 + machine_cost
        lower, upper = _wilson_interval(success_count, count, confidence)
        observations.append({
            "id": name,
            "trials": count,
            "accepted": success_count,
            "acceptance_rate": success_count / count,
            "acceptance_wilson_interval": [lower, upper],
            "meets_target_with_confidence": lower >= target,
            "average_human_minutes_per_trial": human_minutes / count,
            "average_machine_cost_per_trial": machine_cost / count,
            "average_elapsed_minutes_per_trial": elapsed_minutes / count,
            "average_combined_cost_per_trial": total_cost / count,
            "estimated_cost_per_accepted_outcome": (
                total_cost / success_count if success_count else None
            ),
        })
    qualified = [x for x in observations if x["meets_target_with_confidence"]]
    # Do not rank a strategy as eligible based solely on point-estimated acceptance.
    preferred = min(qualified, key=lambda x: (
        x["estimated_cost_per_accepted_outcome"], x["id"]
    )) if qualified else None
    return {
        "task": spec.get("task"),
        "acceptance_protocol": spec.get("acceptance_protocol"),
        "target_acceptance_probability": target,
        "confidence_level": confidence,
        "human_hourly_rate": hourly_rate,
        "strategies": observations,
        "preferred_qualified_strategy": preferred["id"] if preferred else None,
        "status": "qualified_strategy_found" if preferred else "insufficient_evidence_for_target",
        "assumptions": [
            "All strategies must use the same fixed task scope and independent acceptance protocol.",
            "Wilson intervals assume independent Bernoulli trials; correlated runs invalidate the confidence interpretation.",
            "Cost per accepted outcome assumes stationary independent repeat-until-success attempts; report it as descriptive otherwise.",
            "Observed costs do not identify intrinsic semantic complexity or causal AI productivity effects.",
        ],
    }
