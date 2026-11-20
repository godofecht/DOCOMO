import unittest

from docomo.calibration import DRIVERS
from docomo.forecast import forecast

REPORT = {
    'schema_version':'1.0',
    'calibration_status':'partial_domain_specific',
    'historical_effort': {
        'samples':63,
        'cross_validated_best':'cocomo81_recalibrated',
        'full_data_coefficients':{'cocomo81_recalibrated':[0.0]},
        'observed_kloc_range':[2,1000],
    },
    'early_ai_task_time': {
        'samples':246,
        'coefficients':{
            'intercept':.4842343282,
            'log_pre_randomization_estimate':.851330804,
            'ai_allowed':.172607815,
        },
        'observed_estimate_range':[10,1000],
    },
}


class ForecastTests(unittest.TestCase):
    def test_cocomo81_recalibrated_base(self):
        result = forecast(REPORT, {
            'domain':'historical_cocomo81',
            'equivalent_kloc':100,
            'development_mode':'organic',
            'cocomo81_multipliers':{key:1.0 for key in DRIVERS},
        })
        self.assertAlmostEqual(result['point_prediction_person_months'], 3.2*100**1.05)
        self.assertFalse(result['outside_training_size_range'])
        self.assertEqual(result['calibration_status'], 'historical_only')

    def test_rejects_missing_historical_multipliers(self):
        with self.assertRaises(ValueError):
            forecast(REPORT, {'domain':'historical_cocomo81',
                              'equivalent_kloc':100,'development_mode':'embedded'})

    def test_task_model_geometric_duration(self):
        spec = {'domain':'metr_early_2025_tasks','estimated_minutes_without_ai':90,'ai_allowed':True}
        with_ai = forecast(REPORT, spec)
        without_ai = forecast(REPORT, dict(spec,ai_allowed=False))
        self.assertAlmostEqual(with_ai['conditional_geometric_mean_minutes'] /
                               without_ai['conditional_geometric_mean_minutes'], 1.18839994, places=6)

    def test_outside_domain_flag(self):
        result = forecast(REPORT, {'domain':'metr_early_2025_tasks',
                                  'estimated_minutes_without_ai':3000,'ai_allowed':False})
        self.assertTrue(result['outside_training_estimate_range'])

    def test_refuse_unsupported_domain_and_report(self):
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            forecast(REPORT, {'domain':'modern_ai_project_cost'})
        with self.assertRaises(ValueError):
            forecast({'schema_version':'1.0','calibration_status':'fully_calibrated'}, {
                'domain':'metr_early_2025_tasks','estimated_minutes_without_ai':100,'ai_allowed':True})


if __name__ == '__main__':
    unittest.main()
