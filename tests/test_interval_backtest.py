import copy
import unittest

from docomo.forward_years import evaluate_forward_years
from docomo.interval_backtest import audit_forward_intervals, audit_all_forward_intervals
from docomo.project_corpus import _record


def original_fixture(years=12, per_year=10):
    rows=[]
    for t in range(years):
        for i in range(per_year):
            year=1985+t
            number=1+t*per_year+i
            size=9+i*3+t
            driver=.25*(i%4)
            effort=24+(size**1.05)*2.6*(1+driver/5)
            rows.append(_record(
                "desharnais",number,effort,"person_hours",size,"adjusted_function_points",
                {"dependency":driver},f"year:{year}",{"completion_year_code":year},
            ))
    return rows


class StrictIntervalTests(unittest.TestCase):
    def test_no_unavailable_early_interval_is_fabricated(self):
        forward=evaluate_forward_years("desharnais",original_fixture())
        result=audit_forward_intervals(forward)
        self.assertEqual(result["forward_test_project_count"],
                         forward["scored_future_year_projects"])
        self.assertGreater(result["projects_without_finite_intervals"],0)
        self.assertGreater(result["projects_with_all_finite_intervals"],0)
        self.assertEqual(
            result["projects_with_all_finite_intervals"]+
            result["projects_without_finite_intervals"],
            result["forward_test_project_count"],
        )
        self.assertFalse(result["model_results"]["size_only"]["coverage_theorem_claimed"])
        for record in result["case_intervals"]:
            for model,interval in record["intervals"].items():
                if interval["covered"] is None:
                    self.assertIsNone(interval["lower"])
                    self.assertIsNone(interval["upper"])
                else:
                    self.assertGreater(interval["lower"],0)
                    self.assertGreater(interval["upper"],interval["lower"])
                    self.assertIsInstance(interval["covered"],bool)
                    self.assertEqual(interval["covered"],
                                     interval["lower"]<=record["actual_effort"]<=interval["upper"])

    def test_current_and_prior_year_bounds_cannot_use_current_year_outcome(self):
        forward=evaluate_forward_years("desharnais",original_fixture())
        before=audit_forward_intervals(forward)
        changed=copy.deepcopy(forward)
        target=sorted({r["test_completion_year_code"] for r in forward["test_predictions"]})[-2]
        for case in changed["test_predictions"]:
            if case["test_completion_year_code"]==target:
                case["actual_effort"]*=9.0
        after=audit_forward_intervals(changed)
        for a,b in zip(before["case_intervals"],after["case_intervals"]):
            if a["test_completion_year_code"]<=target:
                for model in a["intervals"]:
                    self.assertEqual(a["intervals"][model]["lower"],
                                     b["intervals"][model]["lower"])
                    self.assertEqual(a["intervals"][model]["upper"],
                                     b["intervals"][model]["upper"])

    def test_same_year_projects_cannot_calibrate_one_another(self):
        forward=evaluate_forward_years("desharnais",original_fixture())
        before=audit_forward_intervals(forward)
        changed=copy.deepcopy(forward)
        year=max(r["test_completion_year_code"] for r in forward["test_predictions"])
        changed["test_predictions"][-1]["actual_effort"]*=30
        after=audit_forward_intervals(changed)
        current=lambda result:[r for r in result["case_intervals"]
                               if r["test_completion_year_code"]==year]
        for original,altered in zip(current(before),current(after)):
            self.assertEqual({k:(v["lower"],v["upper"]) for k,v in original["intervals"].items()},
                             {k:(v["lower"],v["upper"]) for k,v in altered["intervals"].items()})

    def test_missing_earlier_prediction_years_refuses_intervals(self):
        forward=evaluate_forward_years("desharnais",original_fixture(years=5,per_year=10))
        report=audit_forward_intervals(forward,min_prior_years=4)
        self.assertEqual(report["projects_with_all_finite_intervals"],0)
        self.assertTrue(all(not r["finite_interval_available"]
                            for r in report["model_results"].values()))

    def test_invalid_coverage_and_model_denominator_refused(self):
        forward=evaluate_forward_years("desharnais",original_fixture())
        with self.assertRaisesRegex(ValueError,"target coverage"):
            audit_forward_intervals(forward,target_coverage=.999999999999999999)
        invalid=copy.deepcopy(forward)
        invalid["test_predictions"][0]["actual_effort"]=-1
        with self.assertRaisesRegex(ValueError,"observed"):
            audit_forward_intervals(invalid)
        invalid=copy.deepcopy(forward)
        invalid["test_predictions"][0]["predictions"].pop("size_only")
        with self.assertRaisesRegex(ValueError,"three fixed"):
            audit_forward_intervals(invalid)
        invalid=copy.deepcopy(forward)
        invalid["test_predictions"].append(copy.deepcopy(invalid["test_predictions"][0]))
        with self.assertRaisesRegex(ValueError,"duplicate"):
            audit_forward_intervals(invalid)

    def test_no_extrapolated_generic_ai_coverage_claim(self):
        forward=evaluate_forward_years("desharnais",original_fixture())
        fake={"status":"retrospective_strict_forward_year_project_effort_validation",
              "domains":{"desharnais":forward,"nasa93":copy.deepcopy(forward)}}
        fake["domains"]["nasa93"]["source_id"]="nasa93"
        result=audit_all_forward_intervals(fake)
        self.assertFalse(result["future_unseen_project_coverage_certified"])
        self.assertEqual(result["target_coverage"],.8)


if __name__=="__main__":
    unittest.main()
