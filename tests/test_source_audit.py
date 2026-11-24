import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from docomo.source_audit import audit_primary_sources

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = json.loads((ROOT / "examples" / "effort-ledger.json").read_text())


def evidence_document(root: Path):
    ledger = copy.deepcopy(EXAMPLE)
    sources = {}
    for item in ledger["human_events"]:
        sources[f"human:{item['id']}"] = item["evidence_url"]
    for item in ledger["machine_charges"]:
        sources[f"machine:{item['id']}"] = item["billing_evidence_url"]
    sources["review"] = ledger["review"]["review_record_url"]
    sources["acceptance"] = ledger["manifest"]["acceptance"]["evidence_url"]
    artifacts = []
    for i, (event_id, source_url) in enumerate(sorted(sources.items())):
        bytes_value = f"illustrative unsigned source evidence for {event_id}".encode("utf-8")
        filename = f"source-{i}.txt"
        (root / filename).write_bytes(bytes_value)
        artifacts.append({
            "event_id": event_id,
            "relative_path": filename,
            "sha256": hashlib.sha256(bytes_value).hexdigest(),
            "source_url": source_url,
        })
    return {"schema_version": "1.0", "ledger": ledger, "artifacts": artifacts}


class PrimarySourceTests(unittest.TestCase):
    def test_all_original_copies_hashed_not_origin_certified(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            result = audit_primary_sources(doc, base, allow_synthetic=True)
            self.assertEqual(result["matched_source_files"], 11)
            self.assertTrue(result["source_file_integrity_checked"])
            self.assertFalse(result["source_origin_independently_authenticated"])
            self.assertFalse(result["reviewer_independence_verified"])
            self.assertFalse(result["acceptance_oracle_independently_audited"])
            self.assertEqual(result["same_bytes_used_for_multiple_evidence_entries"], [])

    def test_synthetic_originals_cannot_be_promoted_to_real(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            with self.assertRaisesRegex(ValueError, "synthetic"):
                audit_primary_sources(doc, base)

    def test_tampered_file_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            (Path(base) / doc["artifacts"][0]["relative_path"]).write_text("altered")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                audit_primary_sources(doc, base, allow_synthetic=True)

    def test_missing_review_source_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            doc["artifacts"] = [x for x in doc["artifacts"] if x["event_id"] != "review"]
            with self.assertRaisesRegex(ValueError, "source evidence mismatch"):
                audit_primary_sources(doc, base, allow_synthetic=True)

    def test_acceptance_source_url_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            next(item for item in doc["artifacts"] if item["event_id"] == "acceptance")["source_url"] = "https://evil.invalid/fake"
            with self.assertRaisesRegex(ValueError, "source_url"):
                audit_primary_sources(doc, base, allow_synthetic=True)

    def test_duplicate_source_id_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            doc["artifacts"].append(copy.deepcopy(doc["artifacts"][0]))
            with self.assertRaisesRegex(ValueError, "duplicate evidence"):
                audit_primary_sources(doc, base, allow_synthetic=True)

    def test_directory_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            doc["artifacts"][0]["relative_path"] = "../outside.txt"
            with self.assertRaisesRegex(ValueError, "traversal"):
                audit_primary_sources(doc, base, allow_synthetic=True)

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as base, tempfile.TemporaryDirectory() as outside:
            doc = evidence_document(Path(base))
            secret = Path(outside) / "secret.txt"
            secret.write_text("secret")
            link = Path(base) / "link.txt"
            link.symlink_to(secret)
            doc["artifacts"][0]["relative_path"] = "link.txt"
            with self.assertRaisesRegex(ValueError, "escapes source_root"):
                audit_primary_sources(doc, base, allow_synthetic=True)

    def test_evidence_reuse_is_reported_not_automatically_condemned(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            first, second = doc["artifacts"][0], doc["artifacts"][1]
            payload = (Path(base) / first["relative_path"]).read_bytes()
            (Path(base) / second["relative_path"]).write_bytes(payload)
            second["sha256"] = first["sha256"]
            result = audit_primary_sources(doc, base, allow_synthetic=True)
            self.assertEqual(len(result["same_bytes_used_for_multiple_evidence_entries"]), 1)
            self.assertEqual(len(result["same_bytes_used_for_multiple_evidence_entries"][0]["event_ids"]), 2)

    def test_empty_source_file_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            (Path(base) / doc["artifacts"][0]["relative_path"]).write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "empty"):
                audit_primary_sources(doc, base, allow_synthetic=True)

    def test_ledger_accounting_mismatch_rejected_first(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            doc["ledger"]["manifest"]["outcome"]["machine_cost"] += 1.0
            with self.assertRaisesRegex(ValueError, "expenditure"):
                audit_primary_sources(doc, base, allow_synthetic=True)

    def test_missing_local_root_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            doc = evidence_document(Path(base))
            with self.assertRaisesRegex(ValueError, "source_root"):
                audit_primary_sources(doc, Path(base) / "missing", allow_synthetic=True)


if __name__ == "__main__":
    unittest.main()
