import copy
import json
import unittest
from pathlib import Path

from docomo.holdout import evaluate_holdout

BASE = json.loads((Path(__file__).resolve().parents[1] / "examples" /
                   "project-manifest.json").read_text())


def make_experiment():
    result = {
        "schema_version": "1.0",
        "selected_model": "docomo_scope",
        "registered_at": "2026-11-22T00:00:00Z",
        "registration_uri": "https://example.org/synthetic-preregistration",
        "target_repository_coverage": 0.9,
        "train": [], "calibration": [], "test": [],
    }
    configurations = (("train", 10, 4), ("calibration", 12, 2), ("test", 5, 2))
    for role, repos, repeats in configurations:
        for r in range(repos):
            for i in range(repeats):
                item = copy.deepcopy(BASE)
                item["project_id"] = f"synthetic-{role}-{r}-{i}"
                item["synthetic"] = True
                item["snapshot"]["repository"] = f"example/{role}-{r}"
                item["snapshot"]["planning_recorded_at"] = (
                    "2026-11-24T00:00:00Z" if role == "test" else "2026-11-20T00:00:00Z"
                )
                index = (r+1)*repeats + i
                item["planning_features"].update({
                    "functional_units": 10 + index,
                    "dependency_edges": index // 2 + r % 3,
                    "verification_obligations": index // 3 + i,
                    "ambiguous_requirements": (index + r) % 7,
                })
                item["workflow"] = ("human_only", "ai_assisted", "agent_delegated")[(r+i)%3]
                item["runtime"]["model_id"] = (
                    None if item["workflow"] == "human_only" else "synthetic-model"
                )
                item["acceptance"]["accepted"] = not (role == "test" and r == 4 and i == 1)
                item["outcome"]["human_minutes"]["implementation"] = 20 + 5*index
                result[role].append(item)
    return result


class HoldoutTests(unittest.TestCase):
    def test_explicit_synthetic_opt_in_only(self):
        with self.assertRaisesRegex(ValueError, "synthetic"):
            evaluate_holdout(make_experiment())

    def test_group_conformal_finite_interval_and_outcome_accounting(self):
        result = evaluate_holdout(make_experiment(), allow_synthetic=True)
        self.assertEqual(result["status"], "synthetic_holdout_algorithm_test_only")
        self.assertEqual(result["calibration_status"], "not_certified")
        self.assertFalse(result["experiment_registration"]["independently_verified"])
        self.assertEqual(result["repository_counts"], {"train":10,"calibration":12,"test":5})
        self.assertEqual(result["split_counts"]["test"]["unaccepted_projects"], 1)
        self.assertEqual(result["test_metrics_conditional_on_acceptance"]["n"], 9)
        interval = result["test_interval_evaluation"]
        self.assertEqual(interval["status"], "finite_interval_available")
        self.assertEqual(len(interval["bounds"]), 9)
        self.assertGreaterEqual(interval["test_repository_coverage"], 0)
        self.assertLessEqual(interval["test_repository_coverage"], 1)
        self.assertLessEqual(interval["test_accepted_project_coverage"], 1)
        self.assertGreater(result["split_counts"]["test"]["observed_human_minutes_per_accepted_deliverable_across_all_attempts"], 0)

    def test_no_repo_overlap(self):
        exp = make_experiment()
        exp["calibration"][0]["snapshot"]["repository"] = exp["train"][0]["snapshot"]["repository"]
        with self.assertRaisesRegex(ValueError,"disjoint repositories"):
            evaluate_holdout(exp, allow_synthetic=True)

    def test_no_project_id_overlap(self):
        exp = make_experiment()
        exp["test"][0]["project_id"] = exp["train"][0]["project_id"]
        with self.assertRaisesRegex(ValueError,"project_id"):
            evaluate_holdout(exp, allow_synthetic=True)

    def test_date_leakage(self):
        exp = make_experiment()
        exp["test"][0]["snapshot"]["planning_recorded_at"] = "2026-11-19T00:00:00Z"
        with self.assertRaisesRegex(ValueError,"prospective"):
            evaluate_holdout(exp, allow_synthetic=True)

    def test_insufficient_groups_cannot_claim_interval(self):
        exp = make_experiment()
        exp["calibration"] = exp["calibration"][:10]
        result = evaluate_holdout(exp, allow_synthetic=True)
        self.assertEqual(
            result["test_interval_evaluation"]["status"],
            "insufficient_calibration_repositories_for_finite_interval",
        )
        self.assertIsNone(result["test_interval_evaluation"]["bounds"])

    def test_rating_data_not_required_for_scope_only_model(self):
        exp = make_experiment()
        for role in ("train","calibration","test"):
            for item in exp[role]:
                del item["planning_features"]["equivalent_ksloc"]
        result = evaluate_holdout(exp, allow_synthetic=True)
        self.assertEqual(result["model"], "docomo_scope")

    def test_size_model_requires_size_for_all_projects(self):
        exp = make_experiment()
        exp["selected_model"] = "size_only"
        del exp["test"][0]["planning_features"]["equivalent_ksloc"]
        with self.assertRaisesRegex(ValueError,"equivalent_ksloc"):
            evaluate_holdout(exp, allow_synthetic=True)

    def test_failure_accounting_is_not_omitted(self):
        exp = make_experiment()
        exp["test"][0]["acceptance"]["accepted"] = False
        result = evaluate_holdout(exp, allow_synthetic=True)
        self.assertEqual(result["split_counts"]["test"]["unaccepted_projects"], 2)
        self.assertEqual(result["test_metrics_conditional_on_acceptance"]["n"], 8)
        self.assertEqual(result["split_counts"]["test"]["total_attempted_projects"], 10)


if __name__ == "__main__":
    unittest.main()
