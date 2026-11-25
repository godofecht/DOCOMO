import copy
import unittest

from docomo.repair_corpus import DATASET_ID, REVISION, SHA256
from docomo.repair_scoring import score_official_repair_report


def fixture():
    """Fake harness reports used only for schema/denominator tests."""
    cases=[{
        "instance_id":f"demo__lib-{i+1}",
        "repository":"demo/lib" if i < 250 else "demo/compiler",
    } for i in range(500)]
    inventory={
        "dataset":DATASET_ID,"revision":REVISION,
        "parquet_sha256":SHA256,"repair_issues":500,
        "cases":cases,
    }
    ids=[r["instance_id"] for r in cases]
    report={
        "schema_version":2,
        "total_instances":500,"submitted_instances":500,
        "completed_instances":490,
        "resolved_instances":210,"unresolved_instances":275,
        "infra_failure_instances":5,
        "ambiguous_failure_instances":0,
        "empty_patch_instances":10,
        "error_instances":5,
        "submitted_ids":ids,
        "completed_ids":ids[:490],
        "resolved_ids":ids[:210],
        "unresolved_ids":ids[210:485],
        "error_ids":ids[485:490],
        "empty_patch_ids":ids[490:],
        "incomplete_ids":[],
        "infra_failure_ids":ids[210:215],
        "ambiguous_failure_ids":[],
    }
    return inventory,report


def score(inventory, report):
    return score_official_repair_report(
        report,inventory,run_id="fake-run-only-for-tests",
        agent_model_id="fictional-model",
        harness_commit="1"*40,
    )


class RepairScoringTests(unittest.TestCase):
    def test_conservative_full_population_denominator(self):
        inventory,report=fixture()
        result=score(inventory,report)
        self.assertEqual(result["cases"],500)
        self.assertEqual(result["reported_solved"],210)
        self.assertAlmostEqual(result["reported_resolved_fraction"],.42)
        self.assertTrue(result["infrastructure_failures_not_excluded_from_denominator"])
        self.assertFalse(result["evaluation_artifacts_independently_verified"])
        self.assertEqual(result["predictive_cost_calibration_status"],"not_measured")
        self.assertEqual(set(result["by_repository"]),{"demo/lib","demo/compiler"})
        self.assertEqual(result["category_counts"]["error"],5)

    def test_missing_case_cannot_be_removed_from_denominator(self):
        inventory,report=fixture()
        report["incomplete_ids"]=[]
        report["submitted_ids"].pop()
        report["submitted_instances"]=499
        with self.assertRaisesRegex(ValueError,"incomplete cases"):
            score(inventory,report)

    def test_counts_must_match_exact_case_lists(self):
        inventory,report=fixture()
        report["resolved_instances"]=211
        with self.assertRaisesRegex(ValueError,"disagrees"):
            score(inventory,report)

    def test_duplicate_or_overlapping_success_failure_is_invalid(self):
        inventory,report=fixture()
        report["unresolved_ids"].append(report["resolved_ids"][0])
        report["unresolved_instances"]+=1
        with self.assertRaisesRegex(ValueError,"overlap"):
            score(inventory,report)

    def test_wrong_dataset_revision_is_rejected(self):
        inventory,report=fixture()
        inventory["revision"]="0"*40
        with self.assertRaisesRegex(ValueError,"exact pinned"):
            score(inventory,report)

    def test_unregistered_repair_case_is_rejected(self):
        inventory,report=fixture()
        report["resolved_ids"][0]="fake__repo-99"
        with self.assertRaisesRegex(ValueError,"unknown source"):
            score(inventory,report)

    def test_misclassified_infrastructure_error_rejected(self):
        inventory,report=fixture()
        report["infra_failure_ids"]=[report["resolved_ids"][0]]
        report["infra_failure_instances"]=1
        with self.assertRaisesRegex(ValueError,"subset of unresolved"):
            score(inventory,report)

    def test_undisclosed_missing_prediction_is_rejected(self):
        inventory,report=fixture()
        missing=report["submitted_ids"].pop()
        report["submitted_instances"]-=1
        report["incomplete_ids"]=[missing]
        report["empty_patch_ids"].remove(missing)
        report["empty_patch_instances"]-=1
        result=score(inventory,report)
        self.assertEqual(result["category_counts"]["incomplete"],1)
        self.assertEqual(result["cases"],500)
        self.assertAlmostEqual(result["reported_resolved_fraction"],.42)

    def test_mismatched_completed_status_is_rejected(self):
        inventory,report=fixture()
        report["completed_ids"]=[]
        report["completed_instances"]=0
        with self.assertRaisesRegex(ValueError,"memberships"):
            score(inventory,report)

    def test_agent_identity_and_harness_revision_required(self):
        inventory,report=fixture()
        with self.assertRaisesRegex(ValueError,"harness_commit"):
            score_official_repair_report(report,inventory,run_id="x",agent_model_id="a",harness_commit="main")
        with self.assertRaisesRegex(ValueError,"agent_model_id"):
            score_official_repair_report(report,inventory,run_id="x",agent_model_id="",harness_commit="1"*40)

    def test_requires_official_schema_v2(self):
        inventory,report=fixture()
        report["schema_version"]=1
        with self.assertRaisesRegex(ValueError,"schema_version=2"):
            score(inventory,report)


if __name__ == "__main__":
    unittest.main()
