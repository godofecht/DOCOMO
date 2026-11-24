import copy
import json
import unittest
from pathlib import Path

from docomo.ledger import reconcile_ledger

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] /
                      "examples" / "effort-ledger.json").read_text())


class EffortLedgerTests(unittest.TestCase):
    def test_synthetic_fixture_reconciles_without_external_verification_claim(self):
        result = reconcile_ledger(EXAMPLE)
        self.assertEqual(result["status"], "reconciled_not_independently_verified")
        self.assertEqual(len(result["human_events"]), 7)
        self.assertAlmostEqual(sum(result["recorded_human_minutes"].values()), 260)
        self.assertAlmostEqual(result["recorded_machine_cost"], 4.3)
        self.assertFalse(result["validation"]["timesheets_or_invoices_externally_authenticated"])
        self.assertFalse(result["validation"]["reviewer_independence_externally_verified"])

    def test_changed_summary_time_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["manifest"]["outcome"]["human_minutes"]["implementation"] += 1
        with self.assertRaisesRegex(ValueError, "reconciliation failed"):
            reconcile_ledger(sample)

    def test_duplicate_event_id_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["machine_charges"][0]["id"] = sample["human_events"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            reconcile_ledger(sample)

    def test_overlapping_intervals_per_actor_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["human_events"][1]["started_at"] = sample["human_events"][0]["started_at"]
        sample["human_events"][1]["ended_at"] = sample["human_events"][0]["ended_at"]
        with self.assertRaisesRegex(ValueError, "overlapping"):
            reconcile_ledger(sample)

    def test_overlapping_work_by_different_actors_is_possible(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["human_events"][1]["actor_id"] = "synthetic-other-dev"
        sample["human_events"][1]["started_at"] = sample["human_events"][0]["started_at"]
        sample["human_events"][1]["ended_at"] = "2026-11-20T09:20:00Z"
        result = reconcile_ledger(sample)
        self.assertEqual(len(result["human_events"]), 7)

    def test_machine_charge_discrepancy_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["machine_charges"][0]["amount"] += 1
        with self.assertRaisesRegex(ValueError, "expenditure"):
            reconcile_ledger(sample)

    def test_currency_mismatch_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["machine_charges"][0]["currency"] = "USD"
        with self.assertRaisesRegex(ValueError, "currency"):
            reconcile_ledger(sample)

    def test_reviewer_contributor_conflict_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["review"]["reviewer_id"] = "synthetic-dev"
        with self.assertRaisesRegex(ValueError, "contributor"):
            reconcile_ledger(sample)

    def test_earlier_review_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["review"]["reviewed_at"] = "2026-11-19T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "cannot precede"):
            reconcile_ledger(sample)

    def test_missing_timezone_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["human_events"][0]["started_at"] = "2026-11-20T09:00:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            reconcile_ledger(sample)

    def test_unrecorded_work_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["human_events"].pop()
        with self.assertRaisesRegex(ValueError, "reconciliation failed"):
            reconcile_ledger(sample)

    def test_negative_machine_charge_rejected(self):
        sample = copy.deepcopy(EXAMPLE)
        sample["machine_charges"][0]["amount"] = -2
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            reconcile_ledger(sample)


if __name__ == "__main__":
    unittest.main()
