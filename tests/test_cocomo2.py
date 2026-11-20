import math
import unittest

from docomo.cocomo2 import estimate_cocomo_ii, SCALE, EFFORT


class CocomoIITests(unittest.TestCase):
    def test_historical_nominal_reference_values(self):
        result = estimate_cocomo_ii({'equivalent_ksloc': 100.0})
        self.assertAlmostEqual(result['exponent'], 1.0997, places=6)
        self.assertAlmostEqual(result['person_months'], 465.3152974687253, places=6)
        self.assertAlmostEqual(result['calendar_months'], 25.873170501888215, places=6)
        self.assertEqual(len(result['assumed_nominal_effort_multipliers']), 17)
        self.assertEqual(len(result['assumed_nominal_scale_factors']), 5)

    def test_adjustments_have_correct_direction(self):
        low_uncertainty = estimate_cocomo_ii({
            'equivalent_ksloc': 100.0, 'scale_factors': {'PREC': 'VH'},
            'effort_multipliers': {'ACAP': 'VH', 'CPLX': 'VL'},
        })
        nominal = estimate_cocomo_ii({'equivalent_ksloc': 100.0})
        self.assertLess(low_uncertainty['person_months'], nominal['person_months'])
        self.assertEqual(low_uncertainty['assumed_nominal_effort_multipliers'].count('ACAP'), 0)

    def test_schedule_excludes_sced_effort_multiplier(self):
        plain = estimate_cocomo_ii({'equivalent_ksloc': 20})
        compressed = estimate_cocomo_ii({'equivalent_ksloc': 20,
                                         'effort_multipliers': {'SCED':'VL'}, 'schedule_percent': 80})
        self.assertAlmostEqual(plain['nominal_schedule_person_months'],
                               compressed['nominal_schedule_person_months'])
        self.assertAlmostEqual(compressed['person_months'] / plain['person_months'], 1.43)
        self.assertAlmostEqual(compressed['calendar_months'] / plain['calendar_months'], .8)

    def test_undefined_ratings_are_rejected(self):
        for spec in (
            {'equivalent_ksloc': 10, 'effort_multipliers': {'TIME':'VL'}},
            {'equivalent_ksloc': 10, 'effort_multipliers': {'SCED':'VL'}},
            {'equivalent_ksloc': 10, 'scale_factors': {'PREC':'INVALID'}},
            {'equivalent_ksloc': 10, 'effort_multipliers': {'IMAGINARY':1.0}},
            {'equivalent_ksloc': 0},
            {'equivalent_ksloc': 10, 'scale_factors': {'RESL': -1}},
            {'equivalent_ksloc': 10, 'effort_multipliers': {'ACAP': float('nan')}},
        ):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                estimate_cocomo_ii(spec)

    def test_full_rating_tables_have_nominal_values(self):
        self.assertEqual(len(SCALE), 5)
        self.assertEqual(len(EFFORT), 17)
        for values in SCALE.values():
            self.assertGreaterEqual(values[2], 0)
        for values in EFFORT.values():
            self.assertEqual(values[2], 1.0)


if __name__ == '__main__':
    unittest.main()
