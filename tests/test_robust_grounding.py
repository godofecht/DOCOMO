import copy
import json
import unittest
from pathlib import Path

from docomo.robust_grounding import assess_robust_grounding

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] / 'examples' / 'robust-scheduler.json').read_text())


class RobustGroundingTests(unittest.TestCase):
    def test_minimax_and_robust_evidence(self):
        result = assess_robust_grounding(EXAMPLE)
        self.assertEqual(result['no_prior_minimax_regret_action'], 'weighted_fair_queueing')
        self.assertAlmostEqual(result['no_prior_minimax_regret'], 7)
        self.assertFalse(result['no_prior_common_optimal_action'])
        self.assertEqual(result['scenarios_compared'], 2)
        self.assertFalse(result['optimal_action_stable_across_listed_priors'])
        self.assertEqual(result['recommended_evidence_stable_across_listed_priors'], 'stakeholder_clarification')
        self.assertEqual(result['evidence_worthwhile_across_all_listed_priors'], ['stakeholder_clarification'])

    def test_no_priors_no_silent_uniform_assumption(self):
        data = copy.deepcopy(EXAMPLE)
        del data['prior_scenarios']
        result = assess_robust_grounding(data)
        self.assertEqual(result['status'], 'no_prior_minimax_regret_only')
        self.assertIsNone(result['evpi_range_over_listed_priors'])

    def test_common_optimal_action_even_with_dominated_alternatives(self):
        data = copy.deepcopy(EXAMPLE)
        data['decisions'] = {
            'good': {'equal_cpu_time': 1, 'weighted_entitlement': 1},
            'dominated': {'equal_cpu_time': 2, 'weighted_entitlement': 3},
        }
        result = assess_robust_grounding(data)
        self.assertTrue(result['no_prior_common_optimal_action'])
        self.assertEqual(result['no_prior_minimax_regret'], 0)

    def test_reject_inconsistent_prior(self):
        data = copy.deepcopy(EXAMPLE)
        data['prior_scenarios'][0]['probabilities']['equal_cpu_time'] = .8
        with self.assertRaises(ValueError):
            assess_robust_grounding(data)

    def test_reject_duplicate_prior_scenarios(self):
        data = copy.deepcopy(EXAMPLE)
        data['prior_scenarios'][1]['id'] = data['prior_scenarios'][0]['id']
        with self.assertRaises(ValueError):
            assess_robust_grounding(data)


if __name__ == '__main__':
    unittest.main()
