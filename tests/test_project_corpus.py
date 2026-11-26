import csv
import tempfile
import unittest
from pathlib import Path

from docomo.project_benchmarks import evaluate_legacy_domain
from docomo.project_corpus import _arff, _record, PROJECT_SOURCES
from docomo.datasets import SOURCES


class RealProjectCorpusTests(unittest.TestCase):
    def test_six_real_sources_are_git_blob_pinned(self):
        self.assertEqual(set(PROJECT_SOURCES), {"cocomo81", "nasa93", "china", "desharnais", "kitchenham", "maxwell"})
        for name in PROJECT_SOURCES:
            self.assertEqual(len(SOURCES[name]["commit"]), 40)
            self.assertEqual(len(SOURCES[name]["git_blob_sha1"]), 40)
        self.assertEqual(SOURCES["nasa93"]["git_blob_sha1"],
                         "cf677e462edbe7623a5707c341c22569816aa566")
        self.assertEqual(SOURCES["kitchenham"]["git_blob_sha1"],
                         "3dfa1089cc4ecba24089f1b788dea98668f22a04")
        self.assertEqual(SOURCES["maxwell"]["git_blob_sha1"],
                         "429f136d7a177dcf3bc72943579ae47e50af71d8")

    def test_arff_parser_fails_closed_on_mismatched_column_count(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "data.arff"
            file.write_text("@relation x\n@attribute ID numeric\n@attribute Effort numeric\n@data\n1,120\n2,400\n")
            self.assertEqual(_arff(file), [
                {"id": "1", "effort": "120"}, {"id": "2", "effort": "400"},
            ])
            file.write_text("@relation x\n@attribute ID numeric\n@attribute Effort numeric\n@data\n1,120,300\n")
            with self.assertRaisesRegex(ValueError, "width"):
                _arff(file)

    def test_real_project_units_not_conflated(self):
        a = _record("china", 1, 500, "person_hours", 80, "AFP_function_points",
                    {}, "id_mod5:1", {})
        b = _record("nasa93", 1, 500, "person_months", 80, "KSLOC",
                    {}, "year:1979", {})
        self.assertNotEqual(a["effort_unit"], b["effort_unit"])
        with self.assertRaisesRegex(ValueError, "pool"):
            evaluate_legacy_domain("china", [a, b])

    def test_historical_driver_hypothesis_and_paired_heldout(self):
        observations = []
        for i in range(1, 61):
            size = 5 + i / 3
            driver = float(i % 5) / 5
            effort = (size**1.15) * (1.1 + driver) * (1 + i % 3 * .01)
            observations.append(_record(
                "china", i, effort, "person_hours", size,
                "AFP_function_points", {"driver": driver},
                f"id_mod5:{i % 5}", {"fold_policy": "retrospective"},
            ))
        result = evaluate_legacy_domain("china", observations)
        self.assertEqual(result["n"], 60)
        self.assertEqual(result["metrics"]["size_only"]["n"], 60)
        self.assertEqual(result["metrics"]["size_and_observed_drivers"]["n"], 60)
        self.assertEqual(result["completion_years_or_id_groups"], 5)
        self.assertFalse(result["candidate_amendment"]["eligible_for_ai_native_release"])
        self.assertIn("project_id_modulo_five_retrospective", result["evaluation"])

    def test_domain_with_nonuniform_cost_units_is_rejected(self):
        rows = []
        for i in range(1, 61):
            rows.append(_record("nasa93", i, 10 + i, "person_hours" if i == 1 else "person_months",
                                2.5 + i, "KSLOC", {"rating": 2.0},
                                f"year:{1971+i%8}", {}))
        with self.assertRaisesRegex(ValueError, "inconsistent effort"):
            evaluate_legacy_domain("nasa93", rows)

    def test_inconsistent_feature_schema_rejected(self):
        rows = []
        for i in range(1, 61):
            rows.append(_record("china", i, 100.0+i, "person_hours", i + 1,
                                "AFP_function_points", {"driver": 1.0},
                                f"id_mod5:{i%5}", {}))
        rows[4]["planning_proxy_features"] = {}
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            evaluate_legacy_domain("china", rows)


if __name__ == "__main__":
    unittest.main()
