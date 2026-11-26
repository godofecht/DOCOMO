"""Synthetic ARFF fixtures only. Production CI downloads original pinned raw files."""
import math
import tempfile
import unittest
from pathlib import Path

from docomo.project_corpus import read_historical_projects
from docomo.project_benchmarks import evaluate_legacy_domain


def kitchenham_fixture(path, *, bogus_effort=False):
    attrs = [
        ("Project","string"),("Client.code","{1,2,3,4,5,6}"),
        ("Project.type","{A,C,D,P,Pr,U}"),
        ("Actual.start.date",'date "YYYY-MM-DD"'),
        ("Actual.duration","numeric"),("Actual.effort","numeric"),
        ("Adjusted.function.points","numeric"),
        ("Estimated.completion.date",'date "YYYY-MM-DD"'),
        ("First.estimate","numeric"),
        ("First.estimate.method","{A,C,CAE,D,EO,W}"),
    ]
    lines=["@relation kitchenham",*[
        f"@attribute {name} {kind}" for name,kind in attrs
    ],"@data"]
    for i in range(1,146):
        kind="?" if i<=10 else "P"
        effort="?" if bogus_effort and i==91 else str(80+i*3)
        lines.append(f"{i},{i%6+1},{kind},1996-04-05,50,{effort},{30+i},1997-06-15,{90+i*3},EO")
    path.write_text("\n".join(lines)+"\n")


def maxwell_fixture(path, *, missing_t01=False):
    fields=["Syear","App","Har","Dba","Ifc","Source","Telonuse","Nlan",*[
        f"T{i:02d}" for i in range(1,16)
    ],"Duration","Size","Time","Effort"]
    lines=["@relation maxwell",*[f"@attribute {field} numeric" for field in fields],"@data"]
    for i in range(1,63):
        values={
            "Syear":85+i%8,"App":1+i%5,"Har":2,"Dba":1,"Ifc":1,
            "Source":1,"Telonuse":0,"Nlan":1+i%3,
            "Duration":4+i%7,"Size":70+i*4,"Time":1+i%8,"Effort":200+i*40,
            **{f"T{j:02d}":1+(j+i)%5 for j in range(1,16)},
        }
        if missing_t01 and i==1:
            values["T01"]="?"
        lines.append(",".join(str(values[field]) for field in fields))
    path.write_text("\n".join(lines)+"\n")


class ExpandedProjectTests(unittest.TestCase):
    def test_kitchenham_145_actual_effort_and_recorded_human_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"k.arff"
            kitchenham_fixture(file)
            rows=read_historical_projects("kitchenham",file)
        self.assertEqual(len(rows),145)
        self.assertEqual(len(set(r["record_id"] for r in rows)),145)
        self.assertEqual({r["effort_unit"] for r in rows},{"person_hours"})
        self.assertEqual(sum(r["descriptors"]["project_type_missing"] for r in rows),10)
        self.assertTrue(all(r["descriptors"]["original_first_estimate_person_hours"]>0 for r in rows))
        score=evaluate_legacy_domain("kitchenham",rows)
        self.assertEqual(score["metrics"]["original_recorded_human_first_estimate"]["n"],145)
        self.assertTrue(score["original_human_first_estimate_available"])
        self.assertTrue(score["original_human_first_estimate_is_not_ai"])
        self.assertFalse(score["candidate_amendment"]["eligible_for_ai_native_release"])

    def test_kitchenham_missing_measured_effort_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"k.arff"
            kitchenham_fixture(file,bogus_effort=True)
            with self.assertRaisesRegex(ValueError,"actual.effort"):
                read_historical_projects("kitchenham",file)

    def test_maxwell_exact_62_measured_project_records_and_fixed_factors(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"m.arff"
            maxwell_fixture(file)
            rows=read_historical_projects("maxwell",file)
        self.assertEqual(len(rows),62)
        self.assertEqual({r["effort_unit"] for r in rows},{"person_hours"})
        self.assertEqual({r["size_unit"] for r in rows},{"function_points"})
        self.assertTrue(all(len(r["planning_proxy_features"])==8 for r in rows))
        score=evaluate_legacy_domain("maxwell",rows)
        self.assertEqual(score["metrics"]["size_only"]["n"],62)
        self.assertEqual(score["metrics"]["size_and_observed_drivers"]["n"],62)
        self.assertFalse(score["original_human_first_estimate_available"])
        self.assertTrue(math.isfinite(score["metrics"]["size_only"]["log_rmse"]))

    def test_maxwell_63rd_project_cannot_be_fabricated(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"m.arff"
            maxwell_fixture(file)
            file.write_text(file.read_text()+"91,2,2,1,1,1,0,2,"+",".join(["3"]*15)+",7,95,5,1200\n")
            with self.assertRaisesRegex(ValueError,"expected 62 records"):
                read_historical_projects("maxwell",file)

    def test_maxwell_missing_tech_factor_not_imputed(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/"m.arff"
            maxwell_fixture(file,missing_t01=True)
            with self.assertRaisesRegex(ValueError,"t01"):
                read_historical_projects("maxwell",file)


if __name__=="__main__":
    unittest.main()
