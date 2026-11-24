"""Read a GitHub-managed server timestamp and immutable commit-bound protocol bytes.

A successful result establishes that the referenced protocol existed at a
GitHub Actions run's server-reported creation time, not that the repository
was publicly visible then, or that source observations and reviewer
independence are authentic.

Never use authored/committer Git dates as registration timestamps.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any, Callable

from .prospective import _sha256, _time, freeze_protocol, validate_protocol

REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")
COMMIT = re.compile(r"[a-fA-F0-9]{40}\Z")
DIGEST = re.compile(r"[a-fA-F0-9]{64}\Z")


def _object(data: Any, name: str) -> Mapping:
    if not isinstance(data, Mapping):
        raise ValueError(f"{name} must be a JSON object")
    return data


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key in downloaded JSON: {key}")
        result[key] = value
    return result


def _get_json(url: str) -> Any:
    """Get GitHub API JSON over HTTPS; no user-specified host or redirect target."""
    if not url.startswith("https://api.github.com/"):
        raise ValueError("attestation API requests must use api.github.com")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "DOCOMO-Research-Attestation/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.geturl().split("/")[2].lower() != "api.github.com":
            raise ValueError("GitHub API request redirected to a different host")
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("GitHub API response exceeds size limit")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)


def _file_path(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith(".json"):
        raise ValueError("path must be a .json file in a repository")
    components = value.split("/")
    if (not components or any(part in ("", ".", "..") for part in components)
            or any("\\" in part or "?" in part or "#" in part or "%" in part
                   for part in components)):
        raise ValueError("path must not contain traversal or URI-control characters")
    if len(value) > 512:
        raise ValueError("path exceeds size limit")
    return value


def _blob_sha(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def verify_github_actions_registration(
    attestation: Mapping[str, Any],
    *,
    fetch_json: Callable[[str], Any] | None = None,
) -> dict:
    """Check pinned GitHub Actions run, commit and protocol contents.

    fetch_json is replaceable for deterministic unit tests; default reads
    only constructed public GitHub REST API URLs. Never accepts arbitrary
    network URLs as an attestation request.
    """
    doc = _object(attestation, "attestation")
    keys = {
        "schema_version", "repository", "workflow_run_id",
        "head_commit", "protocol_path", "expected_protocol_sha256", "protocol",
    }
    if set(doc) != keys or doc["schema_version"] != "1.0":
        raise ValueError("attestation must have exactly the versioned GitHub Actions fields")
    repository = doc["repository"]
    if not isinstance(repository, str) or not REPOSITORY.fullmatch(repository):
        raise ValueError("repository must be owner/name")
    owner, name = repository.split("/")
    if owner in (".", "..") or name in (".", ".."):
        raise ValueError("invalid GitHub repository path")
    run_id = doc["workflow_run_id"]
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("workflow_run_id must be a positive integer")
    commit = doc["head_commit"]
    if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
        raise ValueError("head_commit must be a full Git SHA")
    path = _file_path(doc["protocol_path"])
    expected = doc["expected_protocol_sha256"]
    if not isinstance(expected, str) or not DIGEST.fullmatch(expected):
        raise ValueError("expected_protocol_sha256 must be a full SHA256 digest")
    protocol = validate_protocol(_object(doc["protocol"], "protocol"))
    if _sha256(protocol) != expected.lower():
        raise ValueError("declared protocol content disagrees with expected digest")

    fetch = fetch_json if fetch_json is not None else _get_json
    api_prefix = f"https://api.github.com/repos/{owner}/{name}"
    run_url = f"{api_prefix}/actions/runs/{run_id}"
    run = _object(fetch(run_url), "GitHub workflow run")
    repo_record = _object(run.get("repository"), "GitHub run repository")
    if repo_record.get("full_name", "").lower() != repository.lower():
        raise ValueError("workflow run belongs to another repository")
    if repo_record.get("private") is not False:
        raise ValueError("repository must be currently public for external verification")
    if run.get("id") != run_id or run.get("head_sha", "").lower() != commit.lower():
        raise ValueError("workflow run ID or head commit does not match pinned source")
    if run.get("event") != "push" or run.get("status") != "completed" or run.get("conclusion") != "success":
        raise ValueError("require a completed, successful GitHub Actions push run")
    created = _time(run.get("created_at"), "run.created_at")
    registration = _time(protocol["registered_at"], "protocol.registered_at")
    test_start = _time(protocol["cohorts"]["test"]["enrollment_start"],
                       "test enrollment start")
    if created > registration or created > test_start:
        raise ValueError("GitHub server run timestamp is later than registered cutoff/test enrollment")

    file_url = (
        f"{api_prefix}/contents/{urllib.parse.quote(path, safe='/')}?"
        f"ref={commit.lower()}"
    )
    file_data = _object(fetch(file_url), "GitHub content")
    if file_data.get("type") != "file" or file_data.get("encoding") != "base64":
        raise ValueError("expected a GitHub base64-encoded repository file")
    encoded = file_data.get("content")
    if not isinstance(encoded, str):
        raise ValueError("GitHub file response is missing base64 contents")
    try:
        payload = base64.b64decode("".join(encoded.split()), validate=True)
    except (ValueError, base64.binascii.Error) as error:
        raise ValueError("invalid GitHub base64 file content") from error
    if len(payload) > 1_000_000 or file_data.get("size") != len(payload):
        raise ValueError("GitHub returned inconsistent/oversized protocol content")
    if file_data.get("sha", "").lower() != _blob_sha(payload):
        raise ValueError("GitHub content blob checksum does not match returned bytes")
    try:
        remote_raw = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("downloaded protocol is not valid UTF-8 JSON") from error
    remote = validate_protocol(_object(remote_raw, "downloaded protocol"))
    if remote != protocol or _sha256(remote) != expected.lower():
        raise ValueError("GitHub pinned protocol differs from submitted registered protocol")

    return {
        "status": "github_server_timestamp_and_pinned_content_verified",
        "registration_sha256": expected.lower(),
        "source": {
            "repository": repository,
            "workflow_run_id": run_id,
            "head_commit": commit.lower(),
            "protocol_path": path,
            "created_at_server_reported": created.isoformat().replace("+00:00", "Z"),
            "protocol_file_sha256": hashlib.sha256(payload).hexdigest(),
            "protocol_git_blob_sha1": _blob_sha(payload),
            "workflow_url": f"https://github.com/{repository}/actions/runs/{run_id}",
            "commit_url": f"https://github.com/{repository}/commit/{commit.lower()}",
        },
        "provider_timestamp_verified_by_api": True,
        "protocol_bytes_verified_at_run_commit": True,
        "externally_audited_project_census": False,
        "externally_audited_time_and_invoices": False,
        "externally_audited_acceptance": False,
        "warnings": [
            "The GitHub API run creation timestamp is server-reported, not a user-supplied Git author/committer date.",
            "Current public visibility does not prove this repository was publicly accessible when the run was created.",
            "GitHub Actions success does not prove independent review, software correctness, or truthful project accounting.",
            "This check does not authenticate developer start times or independently prove the future-project inventory is complete.",
            "Only the exact commit bytes are pinned; branch names and later file changes are irrelevant to this verification.",
        ],
    }
