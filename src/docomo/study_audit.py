"""Audit complete project-study bundles before prospective model validation.

The bundle binds full project outcomes to detailed activity ledgers and
computes a canonical preregistration fingerprint from ONLY planning-time
inputs. An in-band hash is not proof of externally timestamped registration.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from .holdout import _timestamp
from .ledger import reconcile_ledger
from .manifests import validate_project

PARTITIONS = ("train", "calibration", "test")


def _object(value: Any, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _protocol_record(record: dict) -> dict:
    return {
        "project_id": record["project_id"],
        "domain": record["domain"],
        "workflow": record["workflow"],
        "snapshot": record["snapshot"],
        "planning_features": record["planning_features"],
        "runtime": record["runtime"],
        "oracle_commit": record["acceptance"]["oracle_commit"],
    }


def audit_study_bundle(bundle: Mapping[str, Any], *,
                       allow_synthetic: bool = False) -> dict:
    """Validate accounting consistency and plan fingerprint without trust claims.

    The bundle must not be used as proof of an independently audited study.
    Synthetic fixture evaluation is available only by explicit library opt-in.
    """
    data = _object(bundle, "bundle")
    if data.get("schema_version") != "1.0":
        raise ValueError("bundle.schema_version must be 1.0")
    experiment = _object(data.get("experiment"), "experiment")
    if experiment.get("schema_version") != "1.0":
        raise ValueError("experiment schema_version must be 1.0")
    plan_time = _timestamp(experiment.get("registered_at"), "registered_at")
    uri = experiment.get("registration_uri")
    if not isinstance(uri, str) or not uri.startswith("https://"):
        raise ValueError("registration_uri must be an HTTPS link")
    model = experiment.get("selected_model")
    if model not in ("docomo_scope", "size_only", "cocomo2_nominal_assumptions"):
        raise ValueError("unknown preselected model")
    q = experiment.get("target_repository_coverage")
    if type(q) not in (float, int) or not .5 <= q < 1:
        raise ValueError("target_repository_coverage must be between 0.5 and 1")
    normalized: dict[str, list[dict]] = {}
    project_index: dict[str, dict] = {}
    project_partition: dict[str, str] = {}
    repo_partition: dict[str, str] = {}
    for partition in PARTITIONS:
        raw = experiment.get(partition)
        if not isinstance(raw, list) or not raw:
            raise ValueError(f"experiment.{partition} must contain projects")
        normalized[partition] = []
        for candidate in raw:
            original = _object(candidate, f"experiment.{partition} project")
            if not allow_synthetic and original.get("synthetic") is True:
                raise ValueError("synthetic project observations cannot pass production study audit")
            record = validate_project(original)
            identity = record["project_id"]
            if identity in project_index:
                raise ValueError(f"duplicate project_id {identity}")
            repo = record["snapshot"]["repository"]
            if repo in repo_partition and repo_partition[repo] != partition:
                raise ValueError(f"repository appears in multiple study partitions: {repo}")
            repo_partition[repo] = partition
            timestamp = _timestamp(record["snapshot"]["planning_recorded_at"], "planning_recorded_at")
            if partition != "test" and timestamp > plan_time:
                raise ValueError("training or calibration planning must predate registration")
            if partition == "test" and timestamp < plan_time:
                raise ValueError("test planning predates registration")
            normalized[partition].append(record)
            project_index[identity] = record
            project_partition[identity] = partition
    if len({p["domain"] for p in project_index.values()}) != 1:
        raise ValueError("mixed study domains are not comparable")
    if len({p["outcome"]["currency"] for p in project_index.values()}) != 1:
        raise ValueError("mixed study currencies require separately documented conversion")

    ledger_entries = data.get("ledgers")
    if not isinstance(ledger_entries, list):
        raise ValueError("ledgers must be a list")
    found: set[str] = set()
    actor_intervals: dict[str, list[tuple[str,str,str]]] = defaultdict(list)
    event_ids: set[str] = set()
    sources: dict[str,str] = {}
    for index, original in enumerate(ledger_entries):
        ledger = _object(original, f"ledgers[{index}]")
        if not allow_synthetic and ledger.get("synthetic") is True:
            raise ValueError("synthetic ledgers cannot pass production study audit")
        audit = reconcile_ledger(ledger)
        project_id = audit["project_id"]
        if project_id not in project_index:
            raise ValueError(f"ledger for unknown project {project_id}")
        if project_id in found:
            raise ValueError(f"duplicate ledger for {project_id}")
        if audit["normalized_manifest"] != project_index[project_id]:
            raise ValueError(f"manifest differs from ledger for {project_id}")
        found.add(project_id)
        for event in audit["human_events"]:
            if event["id"] in event_ids:
                raise ValueError(f"duplicate source event ID across projects: {event['id']}")
            event_ids.add(event["id"])
            actor_intervals[event["actor_id"]].append(
                (event["started_at"], event["ended_at"], project_id)
            )
        for charge in audit["machine_charges"]:
            if charge["id"] in event_ids:
                raise ValueError(f"duplicate source event ID across projects: {charge['id']}")
            event_ids.add(charge["id"])
        sources[project_id] = _digest(ledger)
    if set(project_index) != found:
        missing = sorted(set(project_index) - found)
        raise ValueError(f"missing original activity ledgers for projects: {missing}")
    for actor, raw in actor_intervals.items():
        intervals = sorted(raw)
        for first, second in zip(intervals, intervals[1:]):
            if second[0] < first[1]:
                raise ValueError(
                    f"contributor {actor} has overlapping events across projects {first[2]} and {second[2]}"
                )
    plan = {
        "schema_version": "1.0",
        "registered_at": plan_time.isoformat(),
        "registration_uri": uri,
        "selected_model": model,
        "target_repository_coverage": float(q),
        "planned_projects": {
            role: sorted((_protocol_record(r) for r in normalized[role]),
                         key=lambda r: r["project_id"])
            for role in PARTITIONS
        },
    }
    digest = _digest(plan)
    expected = data.get("expected_protocol_sha256")
    if expected is not None and (not isinstance(expected,str)
                                 or not re.fullmatch(r"[a-fA-F0-9]{64}",expected)):
        raise ValueError("expected_protocol_sha256 must be a valid SHA256 hex digest")
    if expected is not None and expected.lower() != digest:
        raise ValueError("declared protocol SHA256 does not match the planning snapshot")
    return {
        "status": "cost_ledgers_and_planning_reconciled_not_authenticated",
        "project_count": len(project_index),
        "repository_count": len(repo_partition),
        "partition_counts": {role:len(normalized[role]) for role in PARTITIONS},
        "domain": next(iter({p["domain"] for p in project_index.values()})),
        "protocol_sha256": digest,
        "protocol_digest_supplied_and_matched": expected is not None,
        "outcome_ledger_sha256": sources,
        "external_preregistration_audited": False,
        "external_invoice_and_timer_evidence_audited": False,
        "independent_acceptance_evidence_audited": False,
        "warnings": [
            "Digest equality alone does not prove that a plan was committed before outcomes existed.",
            "Source URLs and reviewer declarations are not independently authenticated.",
            "The planning digest intentionally excludes acceptance outcomes and observed costs.",
            "All event IDs must be globally unique and work sessions may not overlap for the same actor, even across projects.",
            "This report is an evidence integrity preflight, not a calibrated model or accepted-system certification.",
        ],
    }
