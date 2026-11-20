import copy
import json
import unittest
from pathlib import Path

from docomo.native import calibrate_native

EXAMPLE = json.loads((Path(__file__).resolve().parents[1] /
                      'examples' / 'project-manifest.json').read_text())


def synthetic_cohort(n: int = 80):
    records = []
    for i in range(n):
        record = copy.deepcopy(EXAMPLE)
        record['project_id'] = f'example-synthetic-{i:03d}'
        record['synthetic'] = True
        record['snapshot']['repository'] = f'example/repo-{i%10:02d}'
        record['workflow'] = ('human_only', 'ai_assisted', 'agent_delegated')[i%3]
        record['runtime']['model_id'] = None if record['workflow'] == 'human_only' else 'fictional-model'
        record['planning_features']['functional_units'] = 4+i
        record['planning_features']['dependency_edges'] = i//2
        record['planning_features']['verification_obligations'] = i//3
        record['planning_features']['ambiguous_requirements'] = i%7
        record['planning_features']['equivalent_ksloc'] = .5+i*.1
        record['outcome']['human_minutes']['implementation'] = 30+i*10
        record['acceptance']['accepted'] = i%10 != 0
        records.append(record)
    return records


class NativeCalibrationTests(unittest.TestCase):
    def test_insufficient_evidence_fails_closed(self):
        result = calibrate_native([])
        self.assertEqual(result['status'], 'insufficient_project_evidence')
        self.assertIsNone(result['coefficients'])

    def test_synthetic_data_cannot_calibrate_as_real(self):
        with self.assertRaisesRegex(ValueError, 'synthetic'):
            calibrate_native(synthetic_cohort())

    def test_synthetic_algorithm_exercises_group_holdout(self):
        result = calibrate_native(synthetic_cohort(),allow_synthetic=True)
        self.assertEqual(result['status'],'synthetic_algorithm_test_only')
        self.assertEqual(result['independent_repositories'], 9)
        self.assertEqual(result['accepted_projects'], 72)
        self.assertIn('docomo_scope', result['cross_validated_metrics'])
        self.assertEqual(result['cross_validated_metrics']['docomo_scope']['n'],72)
        self.assertIn('size_only',result['full_sample_coefficients'])

    def test_zero_human_effort_does_not_enter_log_model(self):
        rows=synthetic_cohort()
        for name in rows[1]['outcome']['human_minutes']:
            rows[1]['outcome']['human_minutes'][name]=0
        rows[1]['outcome']['machine_cost']=7.0
        result=calibrate_native(rows,allow_synthetic=True)
        self.assertEqual(result['status'],'zero_human_effort_requires_hurdle_model')


if __name__ == '__main__':
    unittest.main()
