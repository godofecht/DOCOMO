import copy
import json
import unittest
from pathlib import Path

from docomo.project_corpus import EXPECTED_ROWS, PROJECT_SOURCES
from docomo.scrutiny import scrutinize_amendment, validate_proposal

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "catalog" / "evidence_registry.json").read_text())
PROPOSAL = json.loads((ROOT / "catalog" / "driver_amendment.json").read_text())
UNITS = {"cocomo81": "person_months", "nasa93": "person_months",
         "china": "person_hours", "desharnais": "person_hours"}


def toy_report(ratio_by_domain=None):
    """Test-only fake scores, not scientific results."""
    if ratio_by_domain is None:
        ratio_by_domain = {name:.9 for name in PROJECT_SOURCES}
    datasets = []
    outcomes = {}
    for name in PROJECT_SOURCES:
        datasets.append({"source_id":name,"project_observations":EXPECTED_ROWS[name],
                         "effort_unit":UNITS[name]})
        metrics = {"size_only":{"log_rmse":1.0},
                   "size_and_observed_drivers":{"log_rmse":ratio_by_domain[name]},
                   "training_median":{"log_rmse":1.5}}
        outcomes[name] = {"n":EXPECTED_ROWS[name], "metrics":metrics,
                          "unit":UNITS[name], "evaluation":"toy_group_holdout"}
    return {
        "calibration_status": "historical_real_effort_retrospective_not_ai_native",
        "source_data":{"datasets":datasets},
        "evaluations":{"status":"retrospective_legacy_benchmarks_not_ai_native_calibration",
                       "cohort_results":outcomes},
    }


class ScrutinyTests(unittest.TestCase):
    def test_every_project_domain_required_no_cherrypicking(self):
        altered = copy.deepcopy(PROPOSAL)
        altered["domains"] = ["china", "desharnais"]
        with self.assertRaisesRegex(ValueError, "four historical"):
            validate_proposal(altered)

    def test_observed_improvement_cannot_crown_ai_native_model(self):
        report = toy_report()
        reviewed = scrutinize_amendment(PROPOSAL, report, CATALOG)
        self.assertTrue(reviewed["historical_performance_screen_passed"])
        self.assertEqual(reviewed["positive_domains"], 4)
        self.assertFalse(reviewed["requested_model_upgrade_automatically_authorized"])
        self.assertEqual(reviewed["release_status"],
                         "research_candidate_not_eligible_for_ai_native_release")
        self.assertFalse(reviewed["release_gates"]["prospective_unseen_project_holdout_passed"])
        self.assertEqual(reviewed["evidence_integrity"]["historical_project_records"], 736)

    def test_negative_results_and_counterexamples_remain_visible(self):
        report = toy_report({"cocomo81":.9, "nasa93":.94,
                             "china":1.25, "desharnais":.91})
        reviewed = scrutinize_amendment(PROPOSAL, report, CATALOG)
        self.assertFalse(reviewed["historical_performance_screen_passed"])
        self.assertIn("china", reviewed["substantial_regressions"])
        self.assertTrue(next(x for x in reviewed["datasets_scrutinized"]
                             if x["dataset"] == "china")["negative_result"])
        self.assertEqual(len(reviewed["datasets_scrutinized"]), 4)

    def test_rejects_unsupported_planning_time_availability_claim(self):
        altered = copy.deepcopy(PROPOSAL)
        altered["proposed_feature_timing"] = "planning_time_independently_verified"
        with self.assertRaisesRegex(ValueError, "historical sources"):
            scrutinize_amendment(altered, toy_report(), CATALOG)

    def test_rejects_overstated_empirical_source_count(self):
        altered = copy.deepcopy(CATALOG)
        next(d for d in altered["domains"] if d["id"] == "china")["observed"] = 999
        with self.assertRaisesRegex(ValueError, "mismatched empirical source count"):
            scrutinize_amendment(PROPOSAL, toy_report(), altered)

    def test_rejects_pooled_or_missing_benchmark_domain(self):
        report = toy_report()
        del report["evaluations"]["cohort_results"]["nasa93"]
        with self.assertRaisesRegex(ValueError, "domains"):
            scrutinize_amendment(PROPOSAL, report, CATALOG)

    def test_rejects_unverified_made_up_numeric_evidence(self):
        report = toy_report()
        report["evaluations"]["cohort_results"]["nasa93"]["metrics"]["size_only"]["log_rmse"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            scrutinize_amendment(PROPOSAL, report, CATALOG)

    def test_rejects_nonhistorical_calibration_claim(self):
        report = toy_report()
        report["calibration_status"] = "calibrated_ai_native"
        with self.assertRaisesRegex(ValueError, "non-historical"):
            scrutinize_amendment(PROPOSAL, report, CATALOG)

    def test_requires_independent_status_registry(self):
        altered = copy.deepcopy(CATALOG)
        next(d for d in altered["domains"] if d["id"] == "cocomo81")["data_status"] = "identified_source_not_ingested"
        with self.assertRaisesRegex(ValueError, "non-ingested"):
            scrutinize_amendment(PROPOSAL, toy_report(), altered)


    def test_strict_forward_year_regression_remains_visible(self):
        report = toy_report()
        report["strict_forward_year_validation"] = {
            "status": "retrospective_strict_forward_year_project_effort_validation",
            "domains": {
                "nasa93": {
                    "status": "strict_earlier_to_later_historical_backtest_not_prospective",
                    "total_project_observations": 93, "scored_future_year_projects": 30,
                    "unscored_early_projects": 63,
                    "metrics": {
                        "size_only": {"log_rmse": .7},
                        "size_and_observed_drivers": {"log_rmse": .72},
                        "training_median": {"log_rmse": .9},
                    },
                },
                "desharnais": {
                    "status": "strict_earlier_to_later_historical_backtest_not_prospective",
                    "total_project_observations": 81, "scored_future_year_projects": 49,
                    "unscored_early_projects": 32,
                    "metrics": {
                        "size_only": {"log_rmse": .6},
                        "size_and_observed_drivers": {"log_rmse": .42},
                        "training_median": {"log_rmse": .9},
                    },
                },
            },
        }
        result = scrutinize_amendment(PROPOSAL, report, CATALOG)
        self.assertTrue(result["strict_forward_year_screen_passed"])
        self.assertTrue(result["strict_forward_year_challenges"][0]["negative_result"])
        self.assertFalse(result["strict_forward_year_challenges"][1]["negative_result"])
        self.assertIn("REGRESSED", result["forward_falsification_findings"][0])
        self.assertFalse(result["requested_model_upgrade_automatically_authorized"])
        report["strict_forward_year_validation"]["domains"]["nasa93"]["metrics"]["size_and_observed_drivers"]["log_rmse"] = .8
        failed = scrutinize_amendment(PROPOSAL, report, CATALOG)
        self.assertFalse(failed["strict_forward_year_screen_passed"])
        self.assertTrue(failed["strict_forward_year_challenges"][0]["regression_exceeds_budget"])

    def test_rejects_unfrozen_amendment_changes(self):
        altered = copy.deepcopy(PROPOSAL)
        altered["minimum_improving_domains"] = True
        with self.assertRaisesRegex(ValueError, "1..4"):
            validate_proposal(altered)
        altered = copy.deepcopy(PROPOSAL)
        altered["outcome_after_test"] = 1
        with self.assertRaisesRegex(ValueError, "every required"):
            validate_proposal(altered)


if __name__ == "__main__":
    unittest.main()
