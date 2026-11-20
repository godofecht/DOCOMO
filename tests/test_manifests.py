import copy
import json
import unittest
from pathlib import Path

from docomo.manifests import validate_project, assess_readiness

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] / 'examples' / 'project-manifest.json').read_text())


class ProjectManifestTests(unittest.TestCase):
    def test_valid_manifest_separates_accounting_and_verification(self):
        result = validate_project(EXAMPLE)
        self.assertEqual(result['outcome']['total_human_minutes'], 260)
        self.assertEqual(result['outcome']['machine_cost'], 4.3)
        self.assertEqual(result['evidence_status'], 'self_attested_links_need_independent_audit')

    def test_conflict_reviewer_and_author_rejected(self):
        invalid = copy.deepcopy(EXAMPLE)
        invalid['acceptance']['reviewer_is_author'] = True
        with self.assertRaises(ValueError):
            validate_project(invalid)

    def test_missing_cost_categories_rejected(self):
        invalid = copy.deepcopy(EXAMPLE)
        del invalid['outcome']['human_minutes']['verification']
        with self.assertRaises(ValueError):
            validate_project(invalid)

    def test_invalid_evidence_and_future_leakage_risk(self):
        invalid = copy.deepcopy(EXAMPLE)
        invalid['acceptance']['evidence_url'] = 'not a URL'
        with self.assertRaises(ValueError):
            validate_project(invalid)
        invalid = copy.deepcopy(EXAMPLE)
        invalid['planning_features']['accepted'] = True
        # Unknown fields are not used as predictors; future feature schema must remain predeclared.
        normalized = validate_project(invalid)
        self.assertNotIn('accepted', normalized['planning_features'])

    def test_readiness_is_not_a_calibration_certificate(self):
        result = assess_readiness([EXAMPLE])
        self.assertFalse(result['structurally_ready_for_external_calibration_review'])
        self.assertEqual(result['calibration_status'], 'not_externally_validated')
        invalid = copy.deepcopy(EXAMPLE)
        with self.assertRaises(ValueError):
            assess_readiness([EXAMPLE, invalid])

    def test_workflow_requires_model_id_when_ai(self):
        invalid = copy.deepcopy(EXAMPLE)
        del invalid['runtime']['model_id']
        with self.assertRaises(ValueError):
            validate_project(invalid)

    def test_rejects_unaccounted_failed_attempts(self):
        invalid = copy.deepcopy(EXAMPLE)
        invalid['outcome']['failed_attempts_included'] = False
        with self.assertRaises(ValueError):
            validate_project(invalid)


if __name__ == '__main__':
    unittest.main()
