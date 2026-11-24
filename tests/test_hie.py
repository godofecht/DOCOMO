import csv
import tempfile
import unittest
from pathlib import Path

from docomo.hie import read_hie_tasks, benchmark_hie_tasks, PROCESS


def synthetic_rows(developers=12, tasks_per_developer=8):
    rows = []
    models = ("L1", "L2", "L3")
    for developer in range(developers):
        for task in range(tasks_per_developer):
            size = 1 + task % 5
            rows.append({
                "id": developer*tasks_per_developer + task + 1,
                "developer": f"D{developer:02d}",
                "llm": models[task % 3],
                "story_points": size,
                "actual_minutes": 20 + 8*size + developer%3 + task%2,
                "process": {name: task + 1 for name in PROCESS},
            })
    return rows


class HieTests(unittest.TestCase):
    def test_group_held_out_pre_and_post_execution_models(self):
        data = benchmark_hie_tasks(synthetic_rows(), folds=4)
        self.assertEqual(data["tasks"], 96)
        self.assertEqual(data["developers"], 12)
        self.assertEqual(data["status"], "exploratory_domain_specific_task_benchmark")
        self.assertEqual(set(data["metrics"]), {
            "training_median", "story_points", "story_points_llm",
            "post_execution_diagnostic",
        })
        for model in data["metrics"]:
            self.assertEqual(data["metrics"][model]["n"], 96)
            self.assertGreater(data["metrics"][model]["log_rmse"], 0)
        self.assertEqual(sum(x["held_out_tasks"] for x in data["fold_details"]), 96)
        self.assertIn("RETROSPECTIVE ONLY", data["predictor_timing"]["post_execution_diagnostic"])

    def test_no_global_ai_productivity_estimate(self):
        result = benchmark_hie_tasks(synthetic_rows())
        self.assertNotIn("ai_productivity_multiplier", result)
        self.assertNotIn("calibrated_project_cost", result)
        self.assertIn("No human-only controls", result["limitations"][3])

    def test_accepts_zero_post_execution_indicators(self):
        rows = synthetic_rows()
        for row in rows:
            row["process"] = {name: 0 for name in PROCESS}
        result = benchmark_hie_tasks(rows)
        self.assertEqual(result["metrics"]["post_execution_diagnostic"]["n"], len(rows))

    def test_insufficient_tasks_or_models_rejected(self):
        with self.assertRaises(ValueError):
            benchmark_hie_tasks(synthetic_rows(2, 10))
        rows = synthetic_rows()
        for row in rows:
            row["llm"] = "one"
        with self.assertRaisesRegex(ValueError, "diversity"):
            benchmark_hie_tasks(rows)

    def test_csv_integrity_and_no_implicit_conversion(self):
        headers = ("Execution_Id", "Developer", "LLM", "Story_Points",
                   "Actual_Time_Min", *PROCESS)
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "tasks.csv"
            with file.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers)
                writer.writeheader()
                writer.writerow({
                    "Execution_Id": 1, "Developer": "D1", "LLM": "L1",
                    "Story_Points": 2, "Actual_Time_Min": 22.5,
                    **{name: 0 for name in PROCESS},
                })
            parsed = read_hie_tasks(file)
            self.assertEqual(parsed[0]["actual_minutes"], 22.5)
            with file.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers)
                writer.writerow({
                    "Execution_Id": 1, "Developer": "D2", "LLM": "L2",
                    "Story_Points": 4, "Actual_Time_Min": 10,
                    **{name: 1 for name in PROCESS},
                })
            with self.assertRaisesRegex(ValueError, "duplicate"):
                read_hie_tasks(file)

    def test_rejects_nonfinite_target(self):
        headers = ("Execution_Id", "Developer", "LLM", "Story_Points",
                   "Actual_Time_Min", *PROCESS)
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / "bad.csv"
            with file.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=headers)
                writer.writeheader()
                writer.writerow({
                    "Execution_Id": 2, "Developer": "D1", "LLM": "L1",
                    "Story_Points": 1, "Actual_Time_Min": "nan",
                    **{name: 0 for name in PROCESS},
                })
            with self.assertRaises(ValueError):
                read_hie_tasks(file)


if __name__ == "__main__":
    unittest.main()
