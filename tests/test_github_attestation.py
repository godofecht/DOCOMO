import base64
import copy
import hashlib
import json
import unittest
from pathlib import Path

from docomo.github_attestation import (
    _blob_sha,
    verify_github_actions_registration,
)
from docomo.prospective import freeze_protocol

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "examples" / "prospective-protocol.json").read_text())
REPOSITORY = "example/protocol-registry"
RUN_ID = 123456789
COMMIT = "a" * 40


def fake_attestation():
    protocol = copy.deepcopy(PROTOCOL)
    body = json.dumps(protocol, sort_keys=True, indent=2).encode("utf-8")
    doc = {
        "schema_version": "1.0",
        "repository": REPOSITORY,
        "workflow_run_id": RUN_ID,
        "head_commit": COMMIT,
        "protocol_path": "studies/protocol-v1.json",
        "expected_protocol_sha256": freeze_protocol(protocol)["protocol_sha256"],
        "protocol": protocol,
    }
    run = {
        "id": RUN_ID,
        "head_sha": COMMIT,
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "created_at": "2026-11-21T12:00:00Z",
        "repository": {"full_name": REPOSITORY, "private": False},
        "head_commit": {"timestamp": "1990-01-01T00:00:00Z"},
    }
    source = {
        "type": "file",
        "encoding": "base64",
        "content": base64.b64encode(body).decode(),
        "size": len(body),
        "sha": _blob_sha(body),
    }
    return doc, run, source


def perform(doc, run, source):
    urls = []

    def fetch(url):
        urls.append(url)
        if "/actions/runs/" in url:
            return run
        if "/contents/" in url:
            return source
        raise AssertionError(f"unexpected API URL: {url}")

    result = verify_github_actions_registration(doc, fetch_json=fetch)
    return result, urls


class GithubAttestationTests(unittest.TestCase):
    def test_exact_commit_and_server_timestamp_without_provenance_overclaim(self):
        doc, run, source = fake_attestation()
        result, urls = perform(doc, run, source)
        self.assertEqual(result["status"], "github_server_timestamp_and_pinned_content_verified")
        self.assertEqual(result["source"]["created_at_server_reported"],
                         "2026-11-21T12:00:00Z")
        self.assertEqual(result["registration_sha256"], doc["expected_protocol_sha256"])
        self.assertEqual(result["source"]["protocol_git_blob_sha1"], source["sha"])
        self.assertEqual(result["source"]["protocol_file_sha256"],
                         hashlib.sha256(base64.b64decode(source["content"])).hexdigest())
        self.assertFalse(result["externally_audited_project_census"])
        self.assertFalse(result["externally_audited_time_and_invoices"])
        self.assertFalse(result["externally_audited_acceptance"])
        self.assertEqual(len(urls), 2)
        self.assertTrue(urls[0].endswith(f"/actions/runs/{RUN_ID}"))
        self.assertIn(f"ref={COMMIT}", urls[1])
        self.assertNotIn("1990", result["source"]["created_at_server_reported"])

    def test_server_time_after_registration_rejected_despite_backdated_commit(self):
        doc, run, source = fake_attestation()
        run["created_at"] = "2026-11-23T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "timestamp"):
            perform(doc, run, source)

    def test_run_must_match_immutable_commit(self):
        doc, run, source = fake_attestation()
        run["head_sha"] = "b" * 40
        with self.assertRaisesRegex(ValueError, "head commit"):
            perform(doc, run, source)

    def test_private_repository_not_claimed_public(self):
        doc, run, source = fake_attestation()
        run["repository"]["private"] = True
        with self.assertRaisesRegex(ValueError, "public"):
            perform(doc, run, source)

    def test_non_push_or_unfinished_event_rejected(self):
        doc, run, source = fake_attestation()
        run["event"] = "pull_request"
        with self.assertRaisesRegex(ValueError, "push run"):
            perform(doc, run, source)
        run["event"] = "push"
        run["status"] = "in_progress"
        with self.assertRaisesRegex(ValueError, "push run"):
            perform(doc, run, source)

    def test_modified_content_rejected_even_with_forged_blob_sha(self):
        doc, run, source = fake_attestation()
        new_protocol = copy.deepcopy(PROTOCOL)
        new_protocol["selected_model"] = "size_only"
        blob = json.dumps(new_protocol).encode()
        source["content"] = base64.b64encode(blob).decode()
        source["sha"] = _blob_sha(blob)
        source["size"] = len(blob)
        with self.assertRaisesRegex(ValueError, "differs"):
            perform(doc, run, source)

    def test_corrupt_git_blob_refused(self):
        doc, run, source = fake_attestation()
        source["sha"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "checksum"):
            perform(doc, run, source)

    def test_duplicate_remote_json_keys_refused(self):
        doc, run, source = fake_attestation()
        blob = b'{"schema_version":"1.0","schema_version":"1.0"}'
        source["content"] = base64.b64encode(blob).decode()
        source["sha"] = _blob_sha(blob)
        source["size"] = len(blob)
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            perform(doc, run, source)

    def test_malformed_base64_refused(self):
        doc, run, source = fake_attestation()
        source["content"] = "***"
        with self.assertRaisesRegex(ValueError, "base64"):
            perform(doc, run, source)

    def test_path_traversal_and_invalid_run_id_refused_without_network(self):
        doc, run, source = fake_attestation()
        doc["protocol_path"] = "../secret.json"
        with self.assertRaisesRegex(ValueError, "traversal"):
            perform(doc, run, source)
        doc["protocol_path"] = "studies/protocol-v1.json"
        doc["workflow_run_id"] = True
        with self.assertRaisesRegex(ValueError, "positive integer"):
            perform(doc, run, source)

    def test_unregistered_protocol_tampering_refused_before_fetch(self):
        doc, run, source = fake_attestation()
        doc["protocol"]["cohorts"]["test"]["enrollment_end"] = "2027-02-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "digest"):
            perform(doc, run, source)

    def test_readme_path_is_only_immutable_sha_ref(self):
        doc, run, source = fake_attestation()
        doc["protocol_path"] = "studies/protocol-v1.json"
        _, urls = perform(doc, run, source)
        self.assertNotIn("ref=main", urls[1])
        self.assertEqual(
            urls[1],
            f"https://api.github.com/repos/{REPOSITORY}/contents/studies/protocol-v1.json?ref={COMMIT}",
        )


if __name__ == "__main__":
    unittest.main()
