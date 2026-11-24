import copy
import json
import unittest
from pathlib import Path

from docomo.study_audit import audit_study_bundle

EXAMPLE = json.loads(
    (Path(__file__).resolve().parents[1] / "examples" / "study-bundle.json").read_text()
)


class StudyAuditTests(unittest.TestCase):
    def test_requires_explicit_synthetic_test_opt_in(self):
        with self.assertRaisesRegex(ValueError, "synthetic"):
            audit_study_bundle(EXAMPLE)

    def test_reconciles_study_and_produces_planning_only_digest(self):
        result = audit_study_bundle(EXAMPLE, allow_synthetic=True)
        self.assertEqual(result["project_count"], 3)
        self.assertEqual(result["partition_counts"], {"train": 1, "calibration": 1, "test": 1})
        self.assertEqual(len(result["protocol_sha256"]), 64)
        self.assertFalse(result["external_preregistration_audited"])
        self.assertFalse(result["external_invoice_and_timer_evidence_audited"])
        self.assertFalse(result["protocol_digest_supplied_and_matched"])

        anchored = copy.deepcopy(EXAMPLE)
        anchored["expected_protocol_sha256"] = result["protocol_sha256"]
        again = audit_study_bundle(anchored, allow_synthetic=True)
        self.assertTrue(again["protocol_digest_supplied_and_matched"])
        self.assertFalse(again["external_preregistration_audited"])

    def test_planning_changes_digest_but_outcome_changes_do_not(self):
        original = audit_study_bundle(EXAMPLE, allow_synthetic=True)["protocol_sha256"]
        changed = copy.deepcopy(EXAMPLE)
        changed["experiment"]["test"][0]["outcome"]["elapsed_minutes"] += 7
        changed["ledgers"][2]["manifest"]["outcome"]["elapsed_minutes"] += 7
        self.assertEqual(audit_study_bundle(changed, allow_synthetic=True)["protocol_sha256"], original)
        changed["experiment"]["test"][0]["planning_features"]["functional_units"] += 1
        changed["ledgers"][2]["manifest"]["planning_features"]["functional_units"] += 1
        self.assertNotEqual(audit_study_bundle(changed, allow_synthetic=True)["protocol_sha256"], original)

    def test_manifest_mismatch_not_silently_accepted(self):
        changed = copy.deepcopy(EXAMPLE)
        changed["experiment"]["test"][0]["outcome"]["machine_cost"] += 1
        with self.assertRaisesRegex(ValueError, "manifest differs"):
            audit_study_bundle(changed, allow_synthetic=True)

    def test_missing_ledger_prevents_claiming_study_completion(self):
        changed = copy.deepcopy(EXAMPLE)
        changed["ledgers"].pop()
        with self.assertRaisesRegex(ValueError, "missing original activity ledgers"):
            audit_study_bundle(changed, allow_synthetic=True)

    def test_duplicate_global_event_id_refused(self):
        changed = copy.deepcopy(EXAMPLE)
        changed["ledgers"][1]["human_events"][0]["id"] = (
            changed["ledgers"][0]["human_events"][0]["id"]
        )
        with self.assertRaisesRegex(ValueError, "duplicate source event"):
            audit_study_bundle(changed, allow_synthetic=True)

    def test_overlapping_actor_sessions_across_projects_refused(self):
        changed = copy.deepcopy(EXAMPLE)
        for event in changed["ledgers"][1]["human_events"]:
            event["actor_id"] = "train-developer"
        with self.assertRaisesRegex(ValueError, "overlapping events across projects"):
            audit_study_bundle(changed, allow_synthetic=True)

    def test_experiment_group_leakage_refused(self):
        changed = copy.deepcopy(EXAMPLE)
        changed["experiment"]["test"][0]["snapshot"]["repository"] = "example/train-repo"
        changed["ledgers"][2]["manifest"]["snapshot"]["repository"] = "example/train-repo"
        with self.assertRaisesRegex(ValueError, "multiple study partitions"):
            audit_study_bundle(changed, allow_synthetic=True)

    def test_wrong_anchor_hash_refused(self):
        changed = copy.deepcopy(EXAMPLE)
        changed["expected_protocol_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not match"):
            audit_study_bundle(changed, allow_synthetic=True)

    def test_no_unknown_ledger_project(self):
        changed = copy.deepcopy(EXAMPLE)
        changed["ledgers"][2]["manifest"]["project_id"] = "different-project"
        with self.assertRaisesRegex(ValueError, "unknown project"):
            audit_study_bundle(changed, allow_synthetic=True)

    def test_outcome_cannot_relabel_an_unreviewed_ledger(self):
        changed = copy.deepcopy(EXAMPLE)
        changed["ledgers"][2]["manifest"]["acceptance"]["accepted"] = False
        with self.assertRaisesRegex(ValueError, "manifest differs"):
            audit_study_bundle(changed, allow_synthetic=True)


if __name__ == "__main__":
    unittest.main()
