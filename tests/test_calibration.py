import tempfile
import unittest
from pathlib import Path

from docomo.calibration import (_metrics, _ols, calibrate_projects, calibrate_ai_tasks)
from docomo.datasets import _sha_blob, fetch_dataset


class CalibrationTests(unittest.TestCase):
    def test_exact_linear_model(self):
        x = [[1, i] for i in range(10)]
        beta = _ols(x, [3+2*i for i in range(10)])
        self.assertAlmostEqual(beta[0], 3)
        self.assertAlmostEqual(beta[1], 2)

    def test_metrics_known(self):
        m = _metrics([10, 20], [10, 30])
        self.assertEqual(m['n'], 2)
        self.assertAlmostEqual(m['mae'], 5)
        self.assertAlmostEqual(m['pred25'], .5)

    def test_positive_and_distinct_validation(self):
        with self.assertRaises(ValueError):
            _ols([[1, 1]], [1])
        with self.assertRaises(ValueError):
            _metrics([1], [0])

    def test_project_calibration(self):
        rows = []
        modes = ['organic', 'semidetached', 'embedded']
        for i in range(1, 61):
            rows.append({'id': i, 'mode': modes[i%3], 'kloc': i*3+5,
                         'person_months': 3.5*(i*3+5)**1.12, 'eaf': 1.0})
        result = calibrate_projects(rows)
        self.assertEqual(result['samples'], 60)
        self.assertLess(result['model_metrics']['size_only']['log_rmse'], 1e-8)

    def test_task_calibration_is_not_global_coefficient(self):
        rows=[]
        for dev in range(1, 13):
            for issue in range(12):
                ai = (issue + dev) % 2
                base = 20+issue*5
                rows.append({'id': dev*100+issue, 'developer': dev, 'ai': ai,
                             'estimated_no_ai': base, 'initial': base*(1.2 if ai else 1),
                             'post': None if issue==0 else 0.0})
        result = calibrate_ai_tasks(rows, replicates=50)
        self.assertGreater(result['ai_time_ratio_minus_one'], .1)
        self.assertLess(result['ai_time_ratio_minus_one'], .3)
        self.assertEqual(result['developers'], 12)
        self.assertTrue(result['cluster_bootstrap_95pct'][0] <= result['ai_time_ratio_minus_one'] <= result['cluster_bootstrap_95pct'][1])

    def test_pinned_source_corruption_fails_closed(self):
        self.assertEqual(_sha_blob(b'hello'), 'b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'cocomo81.csv'
            path.write_bytes(b'altered')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                fetch_dataset('cocomo81', Path(directory), offline=True)
            path.unlink()
            with self.assertRaises(FileNotFoundError):
                fetch_dataset('cocomo81', Path(directory), offline=True)


if __name__ == '__main__':
    unittest.main()
