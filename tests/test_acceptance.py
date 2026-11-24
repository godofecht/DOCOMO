import copy
import math
import unittest

from docomo.acceptance import evaluate_acceptance
from docomo.holdout import evaluate_holdout
from docomo.manifests import validate_project
from test_holdout import make_experiment


def mixed_cohort():
    example = make_experiment()
    duplicated = []
    for record in example["train"]:
        clone = copy.deepcopy(record)
        clone["project_id"] += "-another-attempt"
        duplicated.append(clone)
    example["train"].extend(duplicated)
    for role in ("train", "calibration"):
        for i, record in enumerate(example[role]):
            record["acceptance"]["accepted"] = i % 4 != 0
    return example


class AcceptanceTests(unittest.TestCase):
    def test_accepted_only_cohort_refuses_to_fit_failure_risk(self):
        original = make_experiment()
        result = evaluate_holdout(original, allow_synthetic=True)
        acceptance = result["acceptance_evaluation"]
        self.assertEqual(acceptance["status"], "insufficient_acceptance_evidence")
        self.assertIsNone(acceptance["coefficients"])

    def test_full_three_way_training_without_test_leakage(self):
        example = mixed_cohort()
        output = evaluate_holdout(example, allow_synthetic=True)
        result = output["acceptance_evaluation"]
        self.assertEqual(result["status"], "held_out_acceptance_evaluated_not_certified")
        self.assertEqual(result["train_attempts"], 80)
        self.assertEqual(result["calibration_attempts"], 24)
        self.assertEqual(result["test_attempts"], 10)
        self.assertEqual(set(result["test_metrics"]), {
            "train_only_prevalence", "train_only_logistic",
            "calibration_intercept_adjusted_logistic",
        })
        for name, metrics in result["test_metrics"].items():
            self.assertEqual(metrics["n"], 10)
            self.assertGreaterEqual(metrics["brier_score"], 0)
            self.assertLessEqual(metrics["brier_score"], 1)
            self.assertGreaterEqual(metrics["mean_log_loss"], 0)
            self.assertEqual(len(result["forecast_probabilities"][name]), 10)
            self.assertTrue(all(0 < p < 1 for p in result["forecast_probabilities"][name]))

        altered = copy.deepcopy(example)
        for project in altered["test"]:
            project["acceptance"]["accepted"] = not project["acceptance"]["accepted"]
        changed = evaluate_holdout(altered, allow_synthetic=True)["acceptance_evaluation"]
        self.assertEqual(result["forecast_probabilities"], changed["forecast_probabilities"])
        self.assertNotEqual(
            result["test_metrics"]["train_only_logistic"]["brier_score"],
            changed["test_metrics"]["train_only_logistic"]["brier_score"],
        )

    def test_calibration_labels_adjust_intercept_only(self):
        original = mixed_cohort()
        base = evaluate_holdout(original, allow_synthetic=True)["acceptance_evaluation"]
        changed = copy.deepcopy(original)
        changed["calibration"][0]["acceptance"]["accepted"] = True
        changed["calibration"][1]["acceptance"]["accepted"] = False
        # Deliberately alter calibration prevalence without touching training labels.
        for i in range(10):
            changed["calibration"][i]["acceptance"]["accepted"] = False
        modified = evaluate_holdout(changed, allow_synthetic=True)["acceptance_evaluation"]
        self.assertEqual(base["train_coefficients"], modified["train_coefficients"])
        self.assertNotEqual(base["calibration_only_intercept_shift"],
                            modified["calibration_only_intercept_shift"])
        self.assertEqual(base["forecast_probabilities"]["train_only_logistic"],
                         modified["forecast_probabilities"]["train_only_logistic"])
        self.assertNotEqual(
            base["forecast_probabilities"]["calibration_intercept_adjusted_logistic"],
            modified["forecast_probabilities"]["calibration_intercept_adjusted_logistic"],
        )

    def test_reject_all_accepted_or_all_failed_calibration(self):
        example = mixed_cohort()
        for record in example["calibration"]:
            record["acceptance"]["accepted"] = True
        result = evaluate_holdout(example, allow_synthetic=True)["acceptance_evaluation"]
        self.assertEqual(result["status"], "insufficient_acceptance_evidence")

    def test_all_test_failures_cannot_create_conditional_effort_model(self):
        example = mixed_cohort()
        for record in example["test"]:
            record["acceptance"]["accepted"] = False
        result = evaluate_holdout(example, allow_synthetic=True)
        self.assertEqual(result["status"], "no_test_accepted_deliveries")
        self.assertEqual(result["acceptance_evaluation"]["status"],
                         "held_out_acceptance_evaluated_not_certified")
        self.assertEqual(
            result["acceptance_evaluation"]["test_metrics"]["train_only_prevalence"]["empirical_acceptance_rate"],
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
