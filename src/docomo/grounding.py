"""Decision-theoretic grounding assessment, with explicit priors and loss units.

For each possible interpretation theta, an action incurs a given loss.
Evidence is represented as a conditional probability distribution P(observation | theta).
The reduction in minimum expected loss (EVSI) determines the value of the evidence.
No textual similarity or model confidence is treated as a probability.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

TOLERANCE = 1e-9


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _nonnegative(value: Any, name: str) -> float:
    number = _number(value, name)
    if number < 0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{name} must be a non-empty object")
    if not all(isinstance(key, str) and key for key in value):
        raise ValueError(f"{name} must have non-empty string keys")
    return value


def _distribution(value: Any, name: str) -> dict[str, float]:
    entries = _mapping(value, name)
    result = {key: _nonnegative(v, f"{name}.{key}") for key, v in entries.items()}
    if abs(math.fsum(result.values()) - 1) > TOLERANCE:
        raise ValueError(f"{name} probabilities must sum to 1")
    return result


def assess_grounding(spec: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate expected value of resolving ambiguity for a given decision.

    Requires user-supplied interpretations/prior probabilities, action-by-scenario
    losses, and optionally tests with likelihood P(observation | interpretation).
    Losses and evidence cost MUST use the same user-defined cost units.
    Does not infer probabilities or causal correctness from natural language.
    """
    if not isinstance(spec, Mapping):
        raise ValueError("assessment must be an object")
    priors = _distribution(spec.get("interpretations"), "interpretations")
    decisions = _mapping(spec.get("decisions"), "decisions")
    losses: dict[str, dict[str, float]] = {}
    for action, raw_losses in decisions.items():
        row = _mapping(raw_losses, f"decisions.{action}")
        if set(row) != set(priors):
            raise ValueError(f"decisions.{action} must contain exactly the interpretation keys")
        losses[action] = {
            theta: _nonnegative(row[theta], f"decisions.{action}.{theta}") for theta in priors
        }

    def risk(action: str) -> float:
        return math.fsum(priors[t] * losses[action][t] for t in priors)

    prior_action = min(losses, key=lambda action: (risk(action), action))
    prior_risk = risk(prior_action)
    perfect_info_risk = math.fsum(
        priors[theta] * min(losses[action][theta] for action in losses) for theta in priors
    )
    evpi = max(0.0, prior_risk - perfect_info_risk)

    evidence_specs = spec.get("evidence", [])
    if not isinstance(evidence_specs, list):
        raise ValueError("evidence must be an array")
    evidence: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, entry in enumerate(evidence_specs):
        if not isinstance(entry, Mapping):
            raise ValueError(f"evidence[{index}] must be an object")
        name = entry.get("id")
        if not isinstance(name, str) or not name or name in ids:
            raise ValueError("evidence IDs must be non-empty and unique")
        ids.add(name)
        cost = _nonnegative(entry.get("cost"), f"evidence.{name}.cost")
        raw_observations = _mapping(entry.get("observations"), f"evidence.{name}.observations")
        observation_distribution: dict[str, dict[str, float]] = {}
        for observation, raw_likelihoods in raw_observations.items():
            likelihoods = _mapping(raw_likelihoods, f"evidence.{name}.{observation}")
            if set(likelihoods) != set(priors):
                raise ValueError(f"evidence.{name}.{observation} must include all interpretations")
            observation_distribution[observation] = {
                theta: _nonnegative(likelihoods[theta], f"evidence.{name}.{observation}.{theta}")
                for theta in priors
            }
        for theta in priors:
            mass = math.fsum(observation_distribution[o][theta] for o in observation_distribution)
            if abs(mass - 1) > TOLERANCE:
                raise ValueError(f"P(observation | {theta}) must sum to 1 for evidence {name}")

        posterior_risk = 0.0
        policies: dict[str, dict[str, Any]] = {}
        for observation, likelihoods in observation_distribution.items():
            probability = math.fsum(priors[theta] * likelihoods[theta] for theta in priors)
            if probability <= TOLERANCE:
                continue
            # Unnormalised posterior risk, weighted by observation probability.
            action_losses = {
                action: math.fsum(
                    priors[theta] * likelihoods[theta] * losses[action][theta]
                    for theta in priors
                )
                for action in losses
            }
            best_action = min(action_losses, key=lambda action: (action_losses[action], action))
            posterior_risk += action_losses[best_action]
            policies[observation] = {
                "probability": probability,
                "action": best_action,
            }

        evsi = max(0.0, prior_risk - posterior_risk)
        # Round-off tolerance only; EVSI cannot exceed EVPI in a coherent decision table.
        if evsi > evpi + 1e-7:
            raise ValueError("evidence value exceeds perfect-information bound; check inputs")
        evidence.append({
            "id": name,
            "cost": cost,
            "evsi": evsi,
            "net_value": evsi - cost,
            "expected_risk_after_observation": posterior_risk,
            "optimal_actions_by_observation": policies,
        })

    evidence.sort(key=lambda item: (-item["net_value"], item["id"]))
    preferred = evidence[0] if evidence and evidence[0]["net_value"] > TOLERANCE else None
    if evpi <= TOLERANCE:
        status = "not_decision_relevant"
    elif preferred is not None:
        status = "additional_grounding_worthwhile"
    elif not evidence:
        status = "unresolved_no_evidence_proposed"
    else:
        status = "unresolved_or_not_cost_effective_with_proposed_evidence"

    return {
        "task": spec.get("task"),
        "status": status,
        "loss_units": spec.get("loss_units", "unspecified"),
        "decision_relevant_ambiguity": evpi > TOLERANCE,
        "baseline_action": prior_action,
        "baseline_expected_loss": prior_risk,
        "perfect_information_expected_loss": perfect_info_risk,
        "evpi": evpi,
        "recommended_evidence": preferred["id"] if preferred else None,
        "evidence": evidence,
        "assumptions": [
            "User-provided prior probabilities and loss matrix are decision assumptions, not model estimates.",
            "Evidence observation likelihoods are user-provided and must be independently calibrated.",
            "Recommendations consider one evidence acquisition at a time, not sequential test policies.",
        ],
    }
