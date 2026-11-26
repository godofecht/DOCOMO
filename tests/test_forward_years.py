import copy
import math
import unittest

from docomo.forward_years import evaluate_forward_years, evaluate_all_forward
from docomo.project_corpus import _record


def synthetic_year_project_data(name="desharnais", years=9, per_year=9):
    rows = []
    for year in range(2000,2000+years):
        for i in range(per_year):
            identity = (year-1999)*100 + i
            size = 10 + 3*i + (year-2000)
            driver = 0.05*((year+i)%5)
            row = _record(
                name,identity,25+2*size+10*driver,
                "person_hours","" if False else size,"adjusted_function_points",
                {"assurance_driver":driver}, f"year:{year}",
                {"completion_year_code":year} if name == "desharnais"
                else {"year":year},
            )
            rows.append(row)
    return rows


class ForwardYearTests(unittest.TestCase):
    def test_only_earlier_years_are_training_for_each_record(self):
        records=synthetic_year_project_data()
        result=evaluate_forward_years("desharnais",records)
        self.assertEqual(result["status"],
                         "strict_earlier_to_later_historical_backtest_not_prospective")
        self.assertGreater(result["scored_future_year_projects"],0)
        self.assertGreater(result["unscored_early_projects"],0)
        self.assertEqual(result["total_project_observations"],len(records))
        self.assertEqual(
            result["scored_future_year_projects"]+result["unscored_early_projects"],
            len(records),
        )
        self.assertEqual(
            result["metrics"]["size_only"]["n"],
            result["scored_future_year_projects"],
        )
        for entry in result["evaluated_test_years"]:
            self.assertTrue(all(y < entry["year_code"] for y in entry["train_years"]))
            self.assertEqual(
                entry["training_count"],
                sum(r["holdout_group"] in {f"year:{y}" for y in entry["train_years"]}
                    for r in records)
            )
        for case in result["test_predictions"]:
            self.assertEqual(case["effort_unit"],"person_hours")
            self.assertEqual(set(case["predictions"]),{
                "training_median", "size_only","size_and_observed_drivers",
            })

    def test_future_outcomes_cannot_change_prior_year_forecast(self):
        rows=synthetic_year_project_data()
        base=evaluate_forward_years("desharnais",rows)
        changed=copy.deepcopy(rows)
        future_year=max(int(r["holdout_group"].partition(":")[2]) for r in changed)
        for row in changed:
            if row["holdout_group"]==f"year:{future_year}":
                row["effort"]*=100.0
        updated=evaluate_forward_years("desharnais",changed)
        old_predictions={
            r["record_id"]:r["predictions"]
            for r in base["test_predictions"] if r["test_completion_year_code"] < future_year
        }
        new_predictions={
            r["record_id"]:r["predictions"]
            for r in updated["test_predictions"] if r["test_completion_year_code"] < future_year
        }
        self.assertEqual(old_predictions,new_predictions)
        # The later test year itself also cannot be fitted on its own outcomes.
        old_year={
            r["record_id"]:r["predictions"]
            for r in base["test_predictions"] if r["test_completion_year_code"] == future_year
        }
        newer_year={
            r["record_id"]:r["predictions"]
            for r in updated["test_predictions"] if r["test_completion_year_code"] == future_year
        }
        self.assertEqual(old_year,newer_year)

    def test_refuse_training_on_yearless_china_rows(self):
        rows=synthetic_year_project_data()
        with self.assertRaisesRegex(ValueError,"only for NASA93"):
            evaluate_forward_years("china",rows)
        rows[10]["holdout_group"]="id_mod5:0"
        with self.assertRaisesRegex(ValueError,"completion-year"):
            evaluate_forward_years("desharnais",rows)

    def test_refuse_fabricated_year_descriptor(self):
        rows=synthetic_year_project_data()
        rows[5]["descriptors"]["completion_year_code"]=2099
        with self.assertRaisesRegex(ValueError,"does not match"):
            evaluate_forward_years("desharnais",rows)

    def test_duplicate_identifiers_prevent_test_leakage(self):
        rows=synthetic_year_project_data()
        rows[9]["record_id"]=rows[0]["record_id"]
        with self.assertRaisesRegex(ValueError,"duplicate historical"):
            evaluate_forward_years("desharnais",rows)

    def test_early_years_are_explicit_and_not_padded_from_future(self):
        records=synthetic_year_project_data(years=5,per_year=6)
        result=evaluate_forward_years("desharnais",records)
        self.assertGreaterEqual(result["unscored_early_projects"],6)
        self.assertTrue(all(
            row["training_count"]>=result["minimum_training_projects"]
            for row in result["evaluated_test_years"]
        ))

    def test_no_eligible_year_fails_without_invented_error(self):
        records=synthetic_year_project_data(years=3,per_year=11)
        # Add numerous predictors so a 33-project dataset cannot train.
        for row in records:
            row["planning_proxy_features"]={
                f"feature_{i}": 0.3*i for i in range(20)
            }
        result=evaluate_forward_years("desharnais",records)
        self.assertEqual(result["status"],"insufficient_early_year_history_for_fixed_model")
        self.assertEqual(result["test_predictions"],[])
        self.assertEqual(result["unscored_early_projects"],33)


if __name__=="__main__":
    unittest.main()
