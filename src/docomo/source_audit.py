"""Read and checksum original local evidence files for a project's accounting.

Binding a source URL to locally supplied bytes verifies *integrity of a supplied
copy*, not authenticity of that document, signer, publisher, reviewer or bill.
No network requests or opaque content extraction are performed.
"""
from __future__ import annotations

import hashlib
import os
import re
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .ledger import reconcile_ledger

SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
MAX_SOURCE_BYTES = 25_000_000


def _object(value: Any, label: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _local_evidence_path(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or len(relative) > 512:
        raise ValueError("relative_path must be a short nonempty string")
    if (relative.startswith("/") or "\\" in relative or
            any(piece in ("", ".", "..") for piece in relative.split("/"))):
        raise ValueError("relative_path may not escape source_root or contain traversal")
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("evidence path escapes source_root, possibly through a symlink")
    if not resolved.is_file():
        raise ValueError(f"missing original evidence file: {relative}")
    return resolved


def _hash_source(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as source:
        while True:
            piece = source.read(262144)
            if not piece:
                break
            count += len(piece)
            if count > MAX_SOURCE_BYTES:
                raise ValueError(f"original evidence exceeds {MAX_SOURCE_BYTES} bytes")
            digest.update(piece)
    if not count:
        raise ValueError("original evidence is empty")
    return digest.hexdigest(), count


def audit_primary_sources(document: Mapping[str, Any], source_root: str | Path,
                          *, allow_synthetic: bool = False) -> dict:
    """Require a real byte copy for every time, billing, review and acceptance URL.

    The auditor/owner must independently establish that copies originate from
    their claimed provider; hashes alone prove no such connection.
    """
    doc = _object(document, "document")
    if set(doc) != {"schema_version", "ledger", "artifacts"} or doc["schema_version"] != "1.0":
        raise ValueError("source evidence document requires schema_version, ledger and artifacts")
    ledger_raw = _object(doc["ledger"], "ledger")
    if not allow_synthetic and (ledger_raw.get("synthetic") is True or
                                _object(ledger_raw.get("manifest"), "ledger.manifest").get("synthetic") is True):
        raise ValueError("synthetic project evidence cannot be treated as production source verification")
    audited = reconcile_ledger(ledger_raw)
    expected: dict[str, str] = {}
    for event in audited["human_events"]:
        expected[f"human:{event['id']}"] = event["evidence_url"]
    for charge in audited["machine_charges"]:
        expected[f"machine:{charge['id']}"] = charge["billing_evidence_url"]
    expected["review"] = audited["review"]["review_record_url"]
    expected["acceptance"] = audited["normalized_manifest"]["acceptance"]["evidence_url"]

    rows = doc["artifacts"]
    if not isinstance(rows, list):
        raise ValueError("artifacts must be an array")
    provided = {}
    for i, raw in enumerate(rows):
        item = _object(raw, f"artifacts[{i}]")
        if set(item) != {"event_id", "relative_path", "sha256", "source_url"}:
            raise ValueError(f"artifacts[{i}] must have exactly event_id, relative_path, sha256, source_url")
        identity = item["event_id"]
        if not isinstance(identity, str) or not identity:
            raise ValueError("every artifact requires a nonempty event_id")
        if identity in provided:
            raise ValueError(f"duplicate evidence artifact ID: {identity}")
        provided[identity] = item
    if set(provided) != set(expected):
        raise ValueError(f"source evidence mismatch: missing={sorted(set(expected)-set(provided))}, "
                         f"extra={sorted(set(provided)-set(expected))}")
    root = Path(source_root).resolve()
    if not root.is_dir():
        raise ValueError("source_root must be an existing local directory")
    reports = []
    hash_groups: dict[str, list[str]] = defaultdict(list)
    for identity in sorted(expected):
        item = provided[identity]
        if item["source_url"] != expected[identity]:
            raise ValueError(f"source_url for {identity} does not match recorded activity/acceptance evidence")
        claimed = item["sha256"]
        if not isinstance(claimed, str) or not SHA256.fullmatch(claimed):
            raise ValueError(f"source SHA256 for {identity} must be 64 hex characters")
        path = _local_evidence_path(root, item["relative_path"])
        actual, nbytes = _hash_source(path)
        if claimed.lower() != actual:
            raise ValueError(f"original file SHA256 mismatch for {identity}")
        reports.append({"event_id": identity, "relative_path": item["relative_path"],
                        "source_url": item["source_url"], "sha256": actual, "bytes": nbytes})
        hash_groups[actual].append(identity)
    duplicated = [{"sha256": hash_value, "event_ids": ids}
                  for hash_value, ids in sorted(hash_groups.items()) if len(ids) > 1]
    return {
        "status": "source_file_bytes_matched_origin_not_authenticated",
        "project_id": audited["project_id"],
        "matched_source_files": len(reports),
        "matched_bytes_including_reused_sources": sum(item["bytes"] for item in reports),
        "content_sha256": reports,
        "same_bytes_used_for_multiple_evidence_entries": duplicated,
        "source_file_integrity_checked": True,
        "source_origin_independently_authenticated": False,
        "signatures_independently_verified": False,
        "reviewer_independence_verified": False,
        "acceptance_oracle_independently_audited": False,
        "limitations": [
            "A matching checksum authenticates the supplied copy against its declared digest, not the producer or source URL.",
            "Manual external authentication must compare original invoices, source logs, timesheets and reviewer identities.",
            "The same legitimate source document may cover multiple events; duplicate hashes require audit but are not automatically fraudulent.",
            "This check does not prove the population includes every attempted or abandoned project.",
            "Only source bytes are hashed; no OCR, PDF content interpretation or legal signature verification occurs.",
        ],
    }
