"""All observations in this test file are synthetic OOXML fixtures, never real data."""
import copy
import hashlib
import json
import math
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from docomo.industrial_stories import (
    METHODS, evaluate_industrial_estimators, import_industrial_stories
)
from docomo.xlsx_source import read_xlsx_sheet

HEADERS = ("Project", "Story", "Actual PH", "Expert PH", "Poker PH",
           "ChatGPT PH", "DeepSeek PH", "Copilot PH", "Gemini PH")
COLUMNS = {
    "project_id": "Project", "story_id": "Story", "actual_person_hours": "Actual PH",
    "human_expert": "Expert PH", "planning_poker": "Poker PH",
    "chatgpt": "ChatGPT PH", "deepseek": "DeepSeek PH",
    "copilot": "Copilot PH", "gemini": "Gemini PH",
}


def source_manifest(path):
    return {
        "schema_version": "1.0",
        "dataset_doi": "10.17632/ytmwsf2997.2",
        "source_version": 2,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "worksheet": "Real Source",
        "header_row": 1,
        "columns": dict(COLUMNS),
    }


def make_synthetic_workbook(path, *, formula_row=None, missing_row=None,
                            duplicate_story=False, projects=10, stories=11,
                            hidden=False):
    """Write actual OOXML bytes using stdlib for synthetic fixture only."""
    root = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    package = 'http://schemas.openxmlformats.org/package/2006/relationships'
    sheet_xml = [f'<worksheet xmlns="{root}"><sheetData>']
    lines = [list(HEADERS)]
    for project in range(1, projects+1):
        for story in range(1, stories+1):
            actual = 9 + project + story
            row = [f"P{project}", f"S{story}", float(actual),
                   float(actual)*1.2, float(actual)*1.08, float(actual)*1.14,
                   float(actual)*.85, float(actual)*.95, float(actual)*1.3]
            lines.append(row)
    if duplicate_story:
        lines[-1][1] = lines[-2][1]
    cols = "ABCDEFGHI"
    for i, row in enumerate(lines, start=1):
        sheet_xml.append(f'<row r="{i}">')
        for j, value in enumerate(row):
            if missing_row == i and j == 3:
                continue
            ref = f"{cols[j]}{i}"
            if formula_row == i and j == 2:
                sheet_xml.append(f'<c r="{ref}"><f>SUM(1,2)</f><v>3</v></c>')
            elif isinstance(value, str):
                sheet_xml.append(
                    f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
                )
            else:
                sheet_xml.append(f'<c r="{ref}"><v>{value}</v></c>')
        sheet_xml.append('</row>')
    sheet_xml.append('</sheetData></worksheet>')
    workbook = (
        f'<workbook xmlns="{root}" xmlns:r="{rel}"><sheets>'
        '<sheet name="Real Source" sheetId="1" r:id="rId1"/>'
        + ('<sheet name="Hidden" sheetId="2" state="hidden" r:id="rId2"/>' if hidden else '')
        + '</sheets></workbook>'
    )
    rels = (f'<Relationships xmlns="{package}">'
            f'<Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/>'
            + (f'<Relationship Id="rId2" Type="{rel}/worksheet" Target="worksheets/sheet2.xml"/>' if hidden else '')
            + '</Relationships>')
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml",workbook)
        archive.writestr("xl/_rels/workbook.xml.rels",rels)
        archive.writestr("xl/worksheets/sheet1.xml","".join(sheet_xml))
        if hidden:
            archive.writestr("xl/worksheets/sheet2.xml",
                             f'<worksheet xmlns="{root}"><sheetData/></worksheet>')
    return path


class IndustrialStudyTests(unittest.TestCase):
    def test_pinned_original_bytes_required_and_human_vs_ai_distinguished(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook = make_synthetic_workbook(Path(folder)/"synthetic.xlsx")
            imported = import_industrial_stories(workbook,source_manifest(workbook))
            self.assertEqual(imported["projects"],10)
            self.assertEqual(imported["stories"],110)
            self.assertEqual(len(imported["records"]),110)
            self.assertEqual(imported["human_effort_unit"],"person_hours")
            self.assertEqual(set(imported["methods"]),set(METHODS))
            self.assertTrue(all(
                r["ai_columns_are_predictions_not_development"] and
                not r["observed_ai_development_cost"]
                for r in imported["records"]
            ))
            self.assertFalse(imported.get("source_origin_verified",False))

    def test_paired_equal_project_scores_without_pooling_project_groups(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx")
            imported=import_industrial_stories(workbook,source_manifest(workbook))
            result=evaluate_industrial_estimators(imported,bootstrap_replicates=150,seed=12)
            self.assertEqual(result["status"],
                             "retrospective_original_estimate_accuracy_not_ai_coding_productivity")
            self.assertEqual(result["projects"],10)
            self.assertEqual(result["stories"],110)
            self.assertEqual(len(result["per_project"]),10)
            self.assertEqual(result["aggregated_story_weighted"]["chatgpt"]["n"],110)
            self.assertEqual(set(result["paired_bootstrap_reference_human_expert"]),set(METHODS)-{"human_expert"})
            self.assertFalse(result["calibrated_full_project_ai_cost"])
            self.assertFalse(result["ai_development_acceleration_identified"])
            self.assertTrue(all(
                len(r["paired_project_cluster_bootstrap_95pct"]) == 2
                for r in result["paired_bootstrap_reference_human_expert"].values()
            ))
            self.assertEqual(result,evaluate_industrial_estimators(imported,bootstrap_replicates=150,seed=12))

    def test_mendeley_v1_or_unpinned_bytes_cannot_pass_as_v2(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx")
            mapping=source_manifest(workbook)
            mapping["source_version"]=1
            with self.assertRaisesRegex(ValueError,"v2"):
                import_industrial_stories(workbook,mapping)
            mapping=source_manifest(workbook)
            mapping["source_sha256"]="0"*64
            with self.assertRaisesRegex(ValueError,"SHA256"):
                import_industrial_stories(workbook,mapping)

    def test_missing_estimate_is_not_imputed_or_dropped(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx",missing_row=2)
            with self.assertRaisesRegex(ValueError,"human_expert"):
                import_industrial_stories(workbook,source_manifest(workbook))

    def test_formula_derived_true_effort_fails_even_with_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx",formula_row=2)
            with self.assertRaisesRegex(ValueError,"formula-derived"):
                import_industrial_stories(workbook,source_manifest(workbook))

    def test_duplicate_project_story_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx",duplicate_story=True)
            with self.assertRaisesRegex(ValueError,"duplicate original project/story"):
                import_industrial_stories(workbook,source_manifest(workbook))

    def test_refuse_partial_project_or_story_population(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx",projects=9)
            with self.assertRaisesRegex(ValueError,"ten real industrial"):
                import_industrial_stories(workbook,source_manifest(workbook))
            workbook=make_synthetic_workbook(Path(folder)/"synthetic2.xlsx",stories=10)
            with self.assertRaisesRegex(ValueError,"over 100 complete"):
                import_industrial_stories(workbook,source_manifest(workbook))

    def test_refuse_hiding_reused_source_column(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx")
            mapping=source_manifest(workbook)
            mapping["columns"]["deepseek"]=mapping["columns"]["chatgpt"]
            with self.assertRaisesRegex(ValueError,"distinct"):
                import_industrial_stories(workbook,mapping)

    def test_hidden_source_sheet_cannot_be_scored(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx",hidden=True)
            result=read_xlsx_sheet(workbook,sheet_name="Real Source")
            self.assertEqual(result["hidden_sheets"],["Hidden"])
            with self.assertRaisesRegex(ValueError,"hidden"):
                read_xlsx_sheet(workbook,sheet_name="Hidden")

    def test_corrupted_xlsx_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=Path(folder)/"synthetic.xlsx"
            workbook.write_bytes(b"not a spreadsheet")
            with self.assertRaises((zipfile.BadZipFile,ValueError)):
                read_xlsx_sheet(workbook,sheet_name="Real Source")

    def test_cluster_bootstrap_samples_whole_projects_not_individual_stories(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx")
            imported=import_industrial_stories(workbook,source_manifest(workbook))
            result=evaluate_industrial_estimators(imported,bootstrap_replicates=200,seed=1234)
            ci=result["paired_bootstrap_reference_human_expert"]["copilot"]
            self.assertEqual(ci["replicates"],200)
            self.assertLessEqual(ci["paired_project_cluster_bootstrap_95pct"][0],
                                 ci["mean_project_mae_reduction_person_hours"])
            self.assertGreaterEqual(ci["paired_project_cluster_bootstrap_95pct"][1],
                                    ci["mean_project_mae_reduction_person_hours"])
            with self.assertRaisesRegex(ValueError,"bootstrap_replicates"):
                evaluate_industrial_estimators(imported,bootstrap_replicates=50)

    def test_spreadsheet_formula_cannot_masquerade_as_blank_row(self):
        with tempfile.TemporaryDirectory() as folder:
            workbook=make_synthetic_workbook(Path(folder)/"synthetic.xlsx",formula_row=2)
            selected=read_xlsx_sheet(workbook,sheet_name="Real Source")
            self.assertIn((2,3),selected["formula_cells"])


if __name__=="__main__":
    unittest.main()
