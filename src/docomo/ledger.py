"""Reconcile project cost manifests with underlying time and billing events.

This is arithmetic and referential integrity validation, NOT authentication of
timesheet links, invoices, projects or the alleged independence of a reviewer.
Source attestations and signatures require separate external verification.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .manifests import STAGES, validate_project


def _obj(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a nonempty string")
    return value.strip()


def _url(value: Any, label: str) -> str:
    result = _string(value, label)
    if not result.startswith("https://") or result.count("/") < 3:
        raise ValueError(f"{label} must be an HTTPS evidence URL")
    return result


def _time(value: Any, label: str) -> datetime:
    raw = _string(value, label)
    try:
        instant = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label}: invalid ISO 8601 timestamp") from error
    if instant.tzinfo is None:
        raise ValueError(f"{label}: timezone offset required")
    return instant.astimezone(timezone.utc)


def _amount(value: Any, label: str) -> float:
    if type(value) not in (float, int) or not math.isfinite(float(value)) or value < 0:
        raise ValueError(f"{label} must be a finite nonnegative number")
    return float(value)


def reconcile_ledger(document: Mapping[str, Any]) -> dict:
    """Validate detailed cost accounting against an independently versioned manifest.

    Each human event is a measured, timezone-qualified interval attributed to
    one actor and one effort category. Overlapping intervals for an actor are
    forbidden; different actors may work simultaneously.
    Machine charges are captured independently and cannot become person-hours.
    """
    doc = _obj(document, "ledger")
    if doc.get("schema_version") != "1.0":
        raise ValueError("unsupported ledger schema_version")
    manifest = validate_project(_obj(doc.get("manifest"), "manifest"))
    raw_events = doc.get("human_events")
    raw_charges = doc.get("machine_charges")
    if not isinstance(raw_events, list) or not isinstance(raw_charges, list):
        raise ValueError("human_events and machine_charges must be arrays")
    if not raw_events and not raw_charges:
        raise ValueError("a project ledger must contain actual measurement events")
    seen: set[str] = set()
    actors: dict[str, list[tuple[datetime,datetime,str]]] = defaultdict(list)
    minutes = {stage: 0.0 for stage in STAGES}
    normalized_events = []
    for index, raw in enumerate(raw_events):
        e = _obj(raw, f"human_events[{index}]")
        uid = _string(e.get("id"), f"human_events[{index}].id")
        if uid in seen:
            raise ValueError(f"duplicate accounting event ID {uid}")
        seen.add(uid)
        actor = _string(e.get("actor_id"), f"human_events[{index}].actor_id")
        stage = e.get("stage")
        if stage not in STAGES:
            raise ValueError(f"human_events[{index}].stage must be one of {STAGES}")
        start = _time(e.get("started_at"), f"human_events[{index}].started_at")
        end = _time(e.get("ended_at"), f"human_events[{index}].ended_at")
        if end <= start:
            raise ValueError(f"human_events[{index}]: end must follow start")
        evidence = _url(e.get("evidence_url"), f"human_events[{index}].evidence_url")
        source = e.get("source")
        if source not in ("timer", "signed_timesheet", "instrumented_work_session"):
            raise ValueError(f"human_events[{index}].source must identify a measurable time record")
        duration = (end - start).total_seconds() / 60
        if duration > 16*60:
            raise ValueError(f"human_events[{index}]: unreasonable single work session over 16 hours")
        minutes[stage] += duration
        actors[actor].append((start, end, uid))
        normalized_events.append({
            "id": uid, "actor_id": actor, "stage": stage,
            "started_at": start.isoformat(), "ended_at": end.isoformat(),
            "duration_minutes": duration, "source": source,
            "evidence_url": evidence,
        })

    for actor, intervals in actors.items():
        intervals.sort()
        for earlier, later in zip(intervals, intervals[1:]):
            if later[0] < earlier[1]:
                raise ValueError(
                    f"overlapping work sessions for actor {actor}: {earlier[2]} and {later[2]}"
                )

    expected = manifest["outcome"]["human_minutes"]
    for stage in STAGES:
        if abs(minutes[stage] - expected[stage]) > 1e-3:
            raise ValueError(
                f"human-minute reconciliation failed for {stage}: events={minutes[stage]:.5f}, "
                f"manifest={expected[stage]:.5f}"
            )

    currency = manifest["outcome"]["currency"]
    charges = []
    machine_total = 0.0
    for index, raw in enumerate(raw_charges):
        charge = _obj(raw, f"machine_charges[{index}]")
        uid = _string(charge.get("id"), f"machine_charges[{index}].id")
        if uid in seen:
            raise ValueError(f"duplicate accounting event ID {uid}")
        seen.add(uid)
        amount = _amount(charge.get("amount"), f"machine_charges[{index}].amount")
        charged_currency = _string(charge.get("currency"), f"machine_charges[{index}].currency").upper()
        if charged_currency != currency:
            raise ValueError("machine charges must use the manifest currency; conversion requires recorded source")
        evidence = _url(charge.get("billing_evidence_url"), f"machine_charges[{index}].billing_evidence_url")
        meter = _string(charge.get("meter"), f"machine_charges[{index}].meter")
        machine_total += amount
        charges.append({"id": uid, "amount": amount, "currency": currency,
                        "billing_evidence_url": evidence, "meter": meter})
    if abs(machine_total - manifest["outcome"]["machine_cost"]) > 1e-3:
        raise ValueError("machine expenditure ledger does not match manifest.machine_cost")

    audit = doc.get("review")
    if not isinstance(audit, Mapping):
        raise ValueError("review must document an explicitly identified reviewer")
    reviewer_id = _string(audit.get("reviewer_id"), "review.reviewer_id")
    if reviewer_id in actors:
        raise ValueError("ledger reviewer may not also be a contributor to the recorded work")
    _url(audit.get("review_record_url"), "review.review_record_url")
    reviewed_at = _time(audit.get("reviewed_at"), "review.reviewed_at")
    if raw_events and reviewed_at < max(_time(e["ended_at"], "ended_at") for e in normalized_events):
        raise ValueError("ledger review cannot precede the latest recorded work session")
    if audit.get("reviewer_is_author") is not False:
        raise ValueError("ledger review must explicitly attest reviewer is independent")

    return {
        "status": "reconciled_not_independently_verified",
        "project_id": manifest["project_id"],
        "normalized_manifest": manifest,
        "recorded_human_minutes": minutes,
        "recorded_machine_cost": machine_total,
        "human_events": normalized_events,
        "machine_charges": charges,
        "review": {"reviewer_id": reviewer_id, "reviewed_at": reviewed_at.isoformat(),
                   "review_record_url": audit["review_record_url"]},
        "validation": {
            "reconciled_cost_totals": True, "nonoverlapping_same_actor_sessions": True,
            "distinct_human_and_machine_costs": True,
            "acceptance_evidence_cryptographically_verified": False,
            "timesheets_or_invoices_externally_authenticated": False,
            "reviewer_independence_externally_verified": False,
        },
        "limitations": [
            "Linked timesheets, billing documents, and acceptance evidence are unverified statements until independently audited.",
            "Matching totals cannot establish that all abandoned work, rework, or relevant project activity was captured.",
            "Interval provenance does not prove productive time or task quality.",
            "Narrative identifiers and HTTPS links are not cryptographic evidence of authorship.",
        ],
    }
