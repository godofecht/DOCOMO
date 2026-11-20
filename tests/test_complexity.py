import copy
import json
import unittest
from pathlib import Path

from docomo import assess_complexity

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] / "examples" / "strategies.json").read_text())


class ComplexityTests(unittest.TestCase):
    def test_small_samples_do_not_overclaim_reliability(self):
        result = assess_complexity(EXAMPLE)
        self.assertEqual(result["status"], "insufficient_evidence_for_target")
        self.assertIsNone(result["preferred_qualified_strategy"])
        human = result["strategies"][0]
        self.assertEqual(human["acceptance_rate"], 1)
        self.assertLess(human["acceptance_wilson_interval"][0], 0.8)
        agent = result["strategies"][1]
        self.assertEqual(agent["acceptance_rate"], 0.75)
        self.assertAlmostEqual(agent["estimated_cost_per_accepted_outcome"], (78 * 100 / 60 + 7.5) / 3)

    def test_wilson_with_more_successes(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["strategies"] = [{
            "id": "verified", "trials": [
                {"accepted": True, "human_minutes": 1, "machine_cost": 0, "elapsed_minutes": 1}
                for _ in range(30)
            ]
        }]
        result = assess_complexity(spec)
        self.assertEqual(result["preferred_qualified_strategy"], "verified")
        self.assertTrue(result["strategies"][0]["meets_target_with_confidence"])

    def test_all_failures_cannot_estimate_cost_per_success(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["strategies"] = [{
            "id": "failed", "trials": [{"accepted": False, "human_minutes": 10, "machine_cost": 1, "elapsed_minutes": 20}]
        }]
        result = assess_complexity(spec)
        self.assertIsNone(result["strategies"][0]["estimated_cost_per_accepted_outcome"])

    def test_invalid_trial_and_probability_rejected(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["strategies"][0]["trials"][0]["accepted"] = "true"
        with self.assertRaises(ValueError):
            assess_complexity(spec)
        spec = copy.deepcopy(EXAMPLE)
        spec["strategies"][0]["trials"][0]["machine_cost"] = float("nan")
        with self.assertRaises(ValueError):
            assess_complexity(spec)
        spec = copy.deepcopy(EXAMPLE)
        spec["target_acceptance_probability"] = 1.5
        with self.assertRaises(ValueError):
            assess_complexity(spec)


if __name__ == "__main__":
    unittest.main()
