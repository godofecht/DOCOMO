import copy
import json
import unittest
from pathlib import Path

from docomo import assess_grounding

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] / "examples" / "scheduler.json").read_text())


class GroundingTests(unittest.TestCase):
    def test_decision_value_and_optimal_policy(self):
        result = assess_grounding(EXAMPLE)
        self.assertEqual(result["status"], "additional_grounding_worthwhile")
        self.assertEqual(result["baseline_action"], "weighted_fair_queueing")
        self.assertAlmostEqual(result["baseline_expected_loss"], 3.5)
        self.assertAlmostEqual(result["evpi"], 3.5)
        self.assertEqual(result["recommended_evidence"], "stakeholder_clarification")
        test = next(x for x in result["evidence"] if x["id"] == "stakeholder_clarification")
        self.assertAlmostEqual(test["evsi"], 2.65)
        self.assertAlmostEqual(test["net_value"], 2.25)
        self.assertEqual(test["optimal_actions_by_observation"]["requests_equal_cpu"]["action"], "round_robin")
        self.assertEqual(test["optimal_actions_by_observation"]["requests_weighted_entitlement"]["action"], "weighted_fair_queueing")

    def test_no_value_when_actions_indistinguishable(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["decisions"] = {"a": {"equal_cpu_time": 1, "weighted_entitlement": 1}}
        result = assess_grounding(spec)
        self.assertEqual(result["status"], "not_decision_relevant")
        self.assertEqual(result["evpi"], 0)
        self.assertIsNone(result["recommended_evidence"])

    def test_uninformative_observation(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["evidence"] = [spec["evidence"][1]]
        result = assess_grounding(spec)
        self.assertEqual(result["status"], "unresolved_or_not_cost_effective_with_proposed_evidence")
        self.assertAlmostEqual(result["evidence"][0]["evsi"], 0)

    def test_missing_evidence_remains_unresolved(self):
        spec = copy.deepcopy(EXAMPLE)
        spec.pop("evidence")
        self.assertEqual(assess_grounding(spec)["status"], "unresolved_no_evidence_proposed")

    def test_rejects_inconsistent_probability_tables(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["evidence"][0]["observations"]["requests_equal_cpu"]["equal_cpu_time"] = 0.8
        with self.assertRaisesRegex(ValueError, "sum to 1"):
            assess_grounding(spec)

    def test_rejects_invalid_inputs(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["interpretations"]["equal_cpu_time"] = 0.3
        with self.assertRaises(ValueError):
            assess_grounding(spec)
        spec = copy.deepcopy(EXAMPLE)
        spec["decisions"]["round_robin"]["equal_cpu_time"] = -1
        with self.assertRaises(ValueError):
            assess_grounding(spec)
        spec = copy.deepcopy(EXAMPLE)
        spec["evidence"][0]["cost"] = True
        with self.assertRaises(ValueError):
            assess_grounding(spec)

    def test_deterministic_evidence_reaches_perfect_info(self):
        spec = copy.deepcopy(EXAMPLE)
        spec["evidence"] = [{
            "id": "perfect", "cost": 0,
            "observations": {
                "equal": {"equal_cpu_time": 1, "weighted_entitlement": 0},
                "weighted": {"equal_cpu_time": 0, "weighted_entitlement": 1},
            }
        }]
        result = assess_grounding(spec)
        self.assertAlmostEqual(result["evidence"][0]["evsi"], result["evpi"])


if __name__ == "__main__":
    unittest.main()
