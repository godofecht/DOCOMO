import copy
import json
import unittest
from pathlib import Path

from docomo.prospective import (
    check_protocol_population,
    freeze_protocol,
    validate_protocol,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "examples" / "prospective-protocol.json").read_text())
BUNDLE = json.loads((ROOT / "examples" / "study-bundle.json").read_text())


def example_population():
    protocol = copy.deepcopy(PROTOCOL)
    experiment = copy.deepcopy(BUNDLE["experiment"])
    inventory = []
    for part in ("train", "calibration", "test"):
        for manifest in experiment[part]:
            inventory.append({
                "project_id": manifest["project_id"],
                "repository": manifest["snapshot"]["repository"],
                "planning_recorded_at": manifest["snapshot"]["planning_recorded_at"],
                "state": "finalized",
            })
    return {
        "protocol": protocol,
        "expected_protocol_sha256": freeze_protocol(protocol)["protocol_sha256"],
        "inventory": inventory,
        "experiment": experiment,
    }


class ProspectiveTests(unittest.TestCase):
    def test_can_seal_without_any_project_outcomes(self):
        sealed = freeze_protocol(PROTOCOL)
        self.assertEqual(len(sealed["protocol_sha256"]), 64)
        self.assertFalse(sealed["external_registration_verified"])
        self.assertEqual(freeze_protocol(sealed["normalized_protocol"])["protocol_sha256"],
                         sealed["protocol_sha256"])
        self.assertEqual(sealed["normalized_protocol"]["cohorts"]["test"]["repositories"],
                         ["example/test-repo"])

    def test_synthetic_population_rejected_by_production(self):
        with self.assertRaisesRegex(ValueError, "synthetic"):
            check_protocol_population(example_population())

    def test_complete_selection_from_registered_inventory(self):
        result = check_protocol_population(example_population(), allow_synthetic=True)
        self.assertEqual(result["status"],
                         "structurally_complete_pending_external_inventory_and_protocol_audit")
        self.assertEqual(result["eligible_projects"], 3)
        self.assertEqual(result["included_projects"], 3)
        self.assertEqual(result["outstanding_projects"], [])
        self.assertFalse(result["external_population_census_verified"])
        self.assertFalse(result["external_registration_verified"])

    def test_posthoc_exclusion_is_detected(self):
        population = example_population()
        population["experiment"]["test"] = []
        result = check_protocol_population(population, allow_synthetic=True)
        self.assertEqual(result["status"], "incomplete_eligible_project_census")
        self.assertEqual(result["outstanding_projects"], ["synthetic-test-1"])

    def test_pending_attempt_cannot_disappear_from_population(self):
        population = example_population()
        population["inventory"][2]["state"] = "pending"
        population["experiment"]["test"] = []
        result = check_protocol_population(population, allow_synthetic=True)
        self.assertEqual(result["pending_eligible_projects"], ["synthetic-test-1"])
        self.assertFalse(result["ready_for_independently_audited_holdout"])
        population["experiment"]["test"] = copy.deepcopy(BUNDLE["experiment"]["test"])
        with self.assertRaisesRegex(ValueError, "pending"):
            check_protocol_population(population, allow_synthetic=True)

    def test_protocol_change_fails_against_pinned_digest(self):
        population = example_population()
        population["protocol"]["selected_model"] = "size_only"
        with self.assertRaisesRegex(ValueError, "digest differs"):
            check_protocol_population(population, allow_synthetic=True)

    def test_unregistered_model_and_coverage_refused(self):
        population = example_population()
        population["experiment"]["target_repository_coverage"] = 0.8
        with self.assertRaisesRegex(ValueError, "hyperparameters"):
            check_protocol_population(population, allow_synthetic=True)

    def test_unregistered_acceptance_oracle_refused(self):
        population = example_population()
        population["experiment"]["test"][0]["acceptance"]["oracle_commit"] = "1" * 40
        with self.assertRaisesRegex(ValueError, "unregistered acceptance oracle"):
            check_protocol_population(population, allow_synthetic=True)

    def test_unregistered_repository_refused(self):
        population = example_population()
        population["experiment"]["test"][0]["snapshot"]["repository"] = "example/sneaked"
        with self.assertRaisesRegex(ValueError, "differs from original inventory"):
            check_protocol_population(population, allow_synthetic=True)

    def test_planning_time_backdated_into_training_rejected(self):
        protocol = copy.deepcopy(PROTOCOL)
        protocol["cohorts"]["test"]["enrollment_start"] = "2026-11-20T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "prospective test"):
            freeze_protocol(protocol)

    def test_duplicate_repositories_across_cohorts_rejected(self):
        protocol = copy.deepcopy(PROTOCOL)
        protocol["cohorts"]["test"]["repositories"].append("example/train-repo")
        with self.assertRaisesRegex(ValueError, "multiple enrollment cohorts"):
            freeze_protocol(protocol)

    def test_extraneous_protocol_keys_rejected(self):
        protocol = copy.deepcopy(PROTOCOL)
        protocol["choose_test_if_success"] = True
        with self.assertRaisesRegex(ValueError, "exactly"):
            validate_protocol(protocol)

    def test_corrupted_inventory_rejected(self):
        population = example_population()
        population["inventory"].append(copy.deepcopy(population["inventory"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate inventory"):
            check_protocol_population(population, allow_synthetic=True)

    def test_extra_synthetic_outcome_cannot_be_added(self):
        population = example_population()
        extra = copy.deepcopy(population["experiment"]["test"][0])
        extra["project_id"] = "unlisted-new-project"
        population["experiment"]["test"].append(extra)
        with self.assertRaisesRegex(ValueError, "unregistered project"):
            check_protocol_population(population, allow_synthetic=True)

    def test_outside_cohort_inventory_not_automatically_counted(self):
        population = example_population()
        population["inventory"].append({
            "project_id": "not-a-study",
            "repository": "unrelated/repo",
            "planning_recorded_at": "2026-11-23T00:00:00Z",
            "state": "finalized",
        })
        result = check_protocol_population(population, allow_synthetic=True)
        self.assertEqual(result["out_of_cohort_inventory"], 1)


if __name__ == "__main__":
    unittest.main()
