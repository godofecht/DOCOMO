"""Prospective, outcome-independent project population selection.

A protocol can be sealed before ANY test projects exist. It fixes repository
allowlists, enrollment windows, model choice, acceptance oracle and accounting
policy. A supplied population inventory is checked against all recorded
project outcomes. Source completeness and registration chronology require
independent external attestation; no self-issued hash proves them.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .manifests import STAGES, validate_project

PARTITIONS = ("train", "calibration", "test")
MODELS = ("docomo_scope", "size_only", "cocomo2_nominal_assumptions")
HEX40 = re.compile(r"[0-9a-fA-F]{40}\Z")
HEX64 = re.compile(r"[0-9a-fA-F]{64}\Z")
EXACT_FIELDS = {
    "schema_version", "protocol_id", "registered_at", "registration_uri",
    "domain", "currency", "acceptance_oracle_commit", "acceptance_owner",
    "selected_model", "target_repository_coverage", "cohorts", "measurement_policy",
}
COHORT_FIELDS = {"repositories", "enrollment_start", "enrollment_end"}
MEASUREMENT_FIELDS = {"human_effort_stages", "human_time_unit", "machine_cost_currency",
                      "all_failed_attempts_included", "source_ledger_required"}


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _exact(obj: Mapping, names: set[str], label: str) -> None:
    if set(obj) != names:
        raise ValueError(f"{label} must have exactly {sorted(names)} (missing={sorted(names-set(obj))}, extra={sorted(set(obj)-names)})")


def _str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a nonempty trimmed string")
    return value


def _time(raw: Any, label: str) -> datetime:
    value = _str(raw, label)
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label}: invalid ISO 8601 time") from error
    if timestamp.tzinfo is None:
        raise ValueError(f"{label}: timezone offset required")
    return timestamp.astimezone(timezone.utc)


def _utc(value: Any, label: str) -> str:
    return _time(value, label).isoformat().replace("+00:00", "Z")


def _sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           allow_nan=False, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_protocol(protocol: Mapping[str, Any]) -> dict:
    """Normalize and reject any ambiguous or unregistered selection instructions."""
    p = _object(protocol, "protocol")
    _exact(p, EXACT_FIELDS, "protocol")
    if p["schema_version"] != "1.0":
        raise ValueError("protocol schema_version must equal 1.0")
    protocol_id = _str(p["protocol_id"], "protocol_id")
    domain = _str(p["domain"], "domain")
    currency = _str(p["currency"], "currency")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("currency must be an uppercase ISO currency code")
    oracle = _str(p["acceptance_oracle_commit"], "acceptance_oracle_commit")
    if not HEX40.fullmatch(oracle):
        raise ValueError("acceptance_oracle_commit requires a full 40-character Git commit")
    owner = _str(p["acceptance_owner"], "acceptance_owner")
    if p["selected_model"] not in MODELS:
        raise ValueError("selected_model is not an available DOCOMO estimator")
    q = p["target_repository_coverage"]
    if type(q) not in (int, float) or not math.isfinite(float(q)) or not .5 <= q < 1:
        raise ValueError("target_repository_coverage must be finite and in [0.5, 1)")
    registered = _utc(p["registered_at"], "registered_at")
    uri = _str(p["registration_uri"], "registration_uri")
    if not uri.startswith("https://"):
        raise ValueError("registration_uri must point to an external HTTPS record")
    policy = _object(p["measurement_policy"], "measurement_policy")
    _exact(policy, MEASUREMENT_FIELDS, "measurement_policy")
    if (policy["human_effort_stages"] != list(STAGES) or
            policy["human_time_unit"] != "minutes" or
            policy["machine_cost_currency"] != currency or
            policy["all_failed_attempts_included"] is not True or
            policy["source_ledger_required"] is not True):
        raise ValueError("measurement policy must capture all seven human stages, minutes, machine currency, all failures and ledgers")

    cohorts = _object(p["cohorts"], "cohorts")
    _exact(cohorts, set(PARTITIONS), "cohorts")
    registered_time = _time(registered, "registered_at")
    observed_repositories: set[str] = set()
    selected: dict[str, dict] = {}
    for role in PARTITIONS:
        rule = _object(cohorts[role], f"cohorts.{role}")
        _exact(rule, COHORT_FIELDS, f"cohorts.{role}")
        raw = rule["repositories"]
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"cohorts.{role}.repositories must be a nonempty array")
        repos = [_str(repo, f"cohorts.{role}.repository") for repo in raw]
        if len(set(repos)) != len(repos) or any(not re.fullmatch(r"[^/\s]+/[^/\s]+", repo) for repo in repos):
            raise ValueError(f"cohorts.{role}.repositories must contain unique owner/name repositories")
        if observed_repositories & set(repos):
            raise ValueError("repositories cannot appear in multiple enrollment cohorts")
        observed_repositories.update(repos)
        start = _utc(rule["enrollment_start"], f"cohorts.{role}.enrollment_start")
        end = _utc(rule["enrollment_end"], f"cohorts.{role}.enrollment_end")
        if _time(start, "start") >= _time(end, "end"):
            raise ValueError(f"cohorts.{role}: enrollment window must have positive duration")
        if role != "test" and _time(end, "end") > registered_time:
            raise ValueError("training and calibration windows must end by registration")
        if role == "test" and _time(start, "start") < registered_time:
            raise ValueError("prospective test window must start at or after registration")
        selected[role] = {
            "repositories": sorted(repos),
            "enrollment_start": start, "enrollment_end": end,
        }
    return {
        "schema_version": "1.0", "protocol_id": protocol_id,
        "registered_at": registered, "registration_uri": uri,
        "domain": domain, "currency": currency,
        "acceptance_oracle_commit": oracle.lower(),
        "acceptance_owner": owner, "selected_model": p["selected_model"],
        "target_repository_coverage": float(q), "cohorts": selected,
        "measurement_policy": dict(policy),
    }


def freeze_protocol(protocol: Mapping[str, Any]) -> dict:
    """Compute a fingerprint without observing or enumerating future outcomes."""
    p = validate_protocol(protocol)
    return {
        "status": "pre_outcome_selection_rule_fingerprinted_not_externally_attested",
        "protocol_sha256": _sha256(p),
        "normalized_protocol": p,
        "external_registration_verified": False,
        "warnings": [
            "A user-computed SHA256 does not prove prior external publication.",
            "The repository allowlist and enrollment windows must be preregistered externally.",
            "Task inventory completeness and original evidence must be externally audited.",
        ],
    }


def _partition(p: dict, repository: str, when: str) -> str | None:
    timestamp = _time(when, "inventory.planning_recorded_at")
    for role in PARTITIONS:
        rule = p["cohorts"][role]
        if (repository in rule["repositories"] and
                _time(rule["enrollment_start"], "start") <= timestamp <
                _time(rule["enrollment_end"], "end")):
            return role
    return None


def check_protocol_population(document: Mapping[str, Any],
                              *, allow_synthetic: bool = False) -> dict:
    """Check whether every eligible inventoried attempt appears in the study.

    The inventory is self-attested. A missing project *from that inventory*
    is detectable, but missing projects from the underlying true population
    require an external acquisition audit.
    """
    doc = _object(document, "document")
    if set(doc) != {"protocol", "expected_protocol_sha256", "inventory", "experiment"}:
        raise ValueError("population check requires exactly protocol, expected_protocol_sha256, inventory, experiment")
    p = validate_protocol(doc["protocol"])
    declared = _str(doc["expected_protocol_sha256"], "expected_protocol_sha256")
    if not HEX64.fullmatch(declared):
        raise ValueError("expected_protocol_sha256 must be a 64-character hex digest")
    digest = _sha256(p)
    if declared.lower() != digest:
        raise ValueError("frozen protocol digest differs from submitted selection rules")
    inventory = doc["inventory"]
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("population inventory must be a nonempty list")
    eligible: dict[str, str] = {}
    pending = []
    all_ids: set[str] = set()
    not_in_cohort = 0
    for raw in inventory:
        entry = _object(raw, "inventory entry")
        _exact(entry, {"project_id", "repository", "planning_recorded_at", "state"}, "inventory entry")
        identity = _str(entry["project_id"], "inventory.project_id")
        if identity in all_ids:
            raise ValueError(f"duplicate inventory project_id {identity}")
        all_ids.add(identity)
        repo = _str(entry["repository"], "inventory.repository")
        when = _utc(entry["planning_recorded_at"], "inventory.planning_recorded_at")
        role = _partition(p, repo, when)
        if role is None:
            not_in_cohort += 1
            continue
        if entry["state"] not in ("finalized", "pending"):
            raise ValueError("state must be finalized or pending")
        if entry["state"] == "pending":
            pending.append(identity)
        eligible[identity] = role

    experiment = _object(doc["experiment"], "experiment")
    if set(experiment) != {"schema_version", "selected_model", "registered_at",
                           "registration_uri", "target_repository_coverage",
                           *PARTITIONS}:
        raise ValueError("experiment must have exactly the registered model and cohorts")
    if (experiment["schema_version"] != "1.0" or
            experiment["selected_model"] != p["selected_model"] or
            _utc(experiment["registered_at"], "experiment.registered_at") != p["registered_at"] or
            experiment["registration_uri"] != p["registration_uri"] or
            type(experiment["target_repository_coverage"]) not in (float,int) or
            float(experiment["target_repository_coverage"]) != p["target_repository_coverage"]):
        raise ValueError("experiment hyperparameters must match frozen protocol")
    observed: dict[str, str] = {}
    for role in PARTITIONS:
        rows = experiment[role]
        if not isinstance(rows, list):
            raise ValueError(f"experiment.{role} must be an array")
        for raw in rows:
            record = _object(raw, f"experiment.{role} project")
            if not allow_synthetic and record.get("synthetic") is True:
                raise ValueError("synthetic project outcomes may not pass production selection")
            normalized = validate_project(record)
            identity = normalized["project_id"]
            if identity in observed:
                raise ValueError(f"duplicate observed project {identity}")
            observed[identity] = role
            if eligible.get(identity) != role:
                raise ValueError(f"unregistered project {identity} or wrong cohort {role}")
            entry = next(e for e in inventory if e["project_id"] == identity)
            if (normalized["snapshot"]["repository"] != entry["repository"] or
                    _utc(normalized["snapshot"]["planning_recorded_at"], "planning date") !=
                    _utc(entry["planning_recorded_at"], "inventory date")):
                raise ValueError(f"project {identity} differs from original inventory")
            if normalized["domain"] != p["domain"] or normalized["outcome"]["currency"] != p["currency"]:
                raise ValueError(f"project {identity} violates registered domain or currency")
            if normalized["acceptance"]["oracle_commit"] != p["acceptance_oracle_commit"]:
                raise ValueError(f"project {identity} used an unregistered acceptance oracle")

    excluded = sorted(set(eligible) - set(observed))
    if any(project in observed for project in pending):
        raise ValueError("pending project cannot have finalized outcome manifest")
    return {
        "status": ("structurally_complete_pending_external_inventory_and_protocol_audit"
                   if not excluded else "incomplete_eligible_project_census"),
        "protocol_sha256": digest,
        "total_inventory": len(inventory),
        "eligible_projects": len(eligible),
        "included_projects": len(observed),
        "outstanding_projects": excluded,
        "pending_eligible_projects": sorted(pending),
        "out_of_cohort_inventory": not_in_cohort,
        "selection_reproducible_from_supplied_inventory": True,
        "external_registration_verified": False,
        "external_population_census_verified": False,
        "external_acceptance_verified": False,
        "ready_for_independently_audited_holdout": not excluded,
        "warnings": [
            "All selection checks use supplied inventory; completeness against the true population is not externally established.",
            "The fingerprint is not an independently timestamped registration.",
            "A completed study should also pass study-audit for source-ledger consistency.",
            "The holdout test may be evaluated only after cohort completeness and independent audit.",
        ],
    }
