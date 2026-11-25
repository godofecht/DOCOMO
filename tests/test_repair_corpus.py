import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docomo import repair_corpus


def synthetic_verified_rows():
    result=[]
    for i in range(500):
        repo = ("sample-org/engine", "sample-org/editor")[i%2]
        result.append({
            "instance_id": f"sample-org__engine-{i+1}",
            "repo": repo,
            "base_commit": f"{i+1:040x}",
            "problem_statement": f"Demonstration issue number {i+1}",
            "patch": f"--- a/f\n+++ b/f\n@@ -1 +1 @@\n-{i}\n+{i+1}\n",
            "test_patch": f"--- a/test\n+++ b/test\n@@ -1 +1 @@\n-old{i}\n+new{i+1}\n",
            "FAIL_TO_PASS": [f"test_{i}"],
            "PASS_TO_PASS": [],
        })
    return result


class RepairCorpusTests(unittest.TestCase):
    def test_pinned_dataset_source(self):
        self.assertEqual(len(repair_corpus.REVISION), 40)
        self.assertEqual(len(repair_corpus.SHA256), 64)
        self.assertIn(repair_corpus.REVISION, repair_corpus.URL)
        self.assertIn("SWE-bench_Verified", repair_corpus.URL)

    def test_original_synthetic_dataset_has_gold_but_no_agent_leak(self):
        rows=synthetic_verified_rows()
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"cases.parquet"
            file.write_bytes(b"synthetic-parquet-not-real")
            sha=hashlib.sha256(file.read_bytes()).hexdigest()
            with patch.object(repair_corpus, "SHA256", sha), \
                 patch.object(repair_corpus, "_table", return_value=rows):
                result=repair_corpus.read_verified_repairs(file)
        self.assertEqual(result["repair_issues"], 500)
        self.assertEqual(result["repository_count"], 2)
        self.assertEqual(len(result["agent_prompts"]), 500)
        self.assertEqual(len(result["cases"]), 500)
        self.assertFalse(result["original_human_effort_minutes_available"])
        self.assertEqual(result["evaluated_agent_runs"], 0)
        self.assertNotIn("test_patch", json.dumps(result["agent_prompts"]))
        self.assertNotIn("gold_patch_sha256", json.dumps(result["agent_prompts"]))
        self.assertNotIn("--- a/f", json.dumps(result["agent_prompts"]))
        self.assertTrue(all(not row["original_gold_patch_included"] for row in result["agent_prompts"]))

    def test_duplicate_instance_id_rejected(self):
        rows=synthetic_verified_rows()
        rows[1]["instance_id"]=rows[0]["instance_id"]
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"fake.parquet"
            file.write_bytes(b"x")
            with patch.object(repair_corpus, "SHA256", hashlib.sha256(b"x").hexdigest()), \
                 patch.object(repair_corpus, "_table", return_value=rows):
                with self.assertRaisesRegex(ValueError,"duplicated"):
                    repair_corpus.read_verified_repairs(file)

    def test_missing_gold_or_evaluation_metadata_rejected(self):
        rows=synthetic_verified_rows()
        rows[2]["test_patch"]=""
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"fake.parquet"
            file.write_bytes(b"x")
            with patch.object(repair_corpus, "SHA256", hashlib.sha256(b"x").hexdigest()), \
                 patch.object(repair_corpus, "_table", return_value=rows):
                with self.assertRaisesRegex(ValueError,"gold test patch"):
                    repair_corpus.read_verified_repairs(file)

    def test_wrong_snapshot_refused_even_if_parquet_valid(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"some.parquet"
            file.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "not the pinned dataset"):
                repair_corpus.read_verified_repairs(file)

    def test_offline_absent_snapshot_refuses_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileNotFoundError):
                repair_corpus.fetch_verified_repair_cases(Path(folder),offline=True)

    def test_source_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"swe_bench_verified.parquet"
            path.write_bytes(b"wrong source")
            with self.assertRaisesRegex(ValueError,"checksum mismatch"):
                repair_corpus.fetch_verified_repair_cases(Path(folder),offline=True)


if __name__ == "__main__":
    unittest.main()
