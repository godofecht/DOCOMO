"""Out-of-time prediction interval audit against actual completed project costs.

At the beginning of completion-year Y, only residuals from predictions
issued for years STRICTLY before Y may determine the interval. No coverage
claim is issued when adequate historical calibration groups are unavailable.

This is a *prequential retrospective audit*, not formal distribution-free
conformal coverage: the historical records are dependent, drivers may be
recorded after project delivery, and past predictions were not prospectively
logged with proof of original timestamp.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from .forward_years import MODELS, TEMPORAL_SOURCES


def _inputs(audit: Mapping, coverage: float) -> dict[int,list[dict]]:
    if not isinstance(audit, Mapping):
        raise ValueError("strict-forward source evaluation must be an object")
    if audit.get("source_id") not in TEMPORAL_SOURCES:
        raise ValueError("intervals require a NASA93 or Desharnais historical year cohort")
    if audit.get("status") != "strict_earlier_to_later_historical_backtest_not_prospective":
        raise ValueError("cannot calibrate intervals on a source with no forward test predictions")
    if type(coverage) not in (float,int) or not math.isfinite(coverage) or not .5 <= coverage < 1:
        raise ValueError("target coverage must be finite and in [0.5,1)")
    cases = audit.get("test_predictions")
    if not isinstance(cases,list) or not cases:
        raise ValueError("missing original strict-forward predictions")
    projects = defaultdict(list)
    names = set()
    for row in cases:
        if not isinstance(row,Mapping):
            raise ValueError("malformed out-of-time prediction")
        identity = row.get("record_id")
        if not isinstance(identity,str) or not identity or identity in names:
            raise ValueError("duplicate or invalid out-of-time project ID")
        names.add(identity)
        year = row.get("test_completion_year_code")
        if type(year) is not int:
            raise ValueError("invalid historical completion year")
        if row.get("effort_unit") != audit.get("effort_unit"):
            raise ValueError("mixed source effort units")
        actual = row.get("actual_effort")
        predictions = row.get("predictions")
        if not isinstance(predictions,Mapping) or set(predictions) != set(MODELS):
            raise ValueError("all three fixed effort estimators are required")
        if type(actual) not in (int,float) or not math.isfinite(actual) or actual <= 0:
            raise ValueError("invalid observed project effort")
        if any(type(p) not in (int,float) or not math.isfinite(p) or p <= 0
               for p in predictions.values()):
            raise ValueError("invalid positive model forecast")
        projects[year].append(row)
    if len(names) != audit.get("scored_future_year_projects"):
        raise ValueError("reported and actual forward test case counts disagree")
    return projects


def _quantile(scores: list[float], coverage: float, min_residuals: int) -> tuple[float|None,int|None]:
    n=len(scores)
    if n < min_residuals:
        return None,None
    rank=math.ceil((n+1)*coverage-1e-12)
    if rank>n:
        return None,rank
    ordered=sorted(scores)
    return ordered[rank-1],rank


def audit_forward_intervals(source: Mapping[str,Any], *,
                            target_coverage: float = .8,
                            min_prior_years: int = 2,
                            min_prior_predictions: int = 12) -> dict:
    """Report retrospective prediction intervals with strictly prior errors.

    Uses an explicitly labelled pooled per-project quantile over earlier
    out-of-time residuals, not a theorem of independent year-block coverage.
    """
    if type(min_prior_years) is not int or min_prior_years < 2:
        raise ValueError("at least two distinct previous completion years required")
    if type(min_prior_predictions) is not int or min_prior_predictions < 5:
        raise ValueError("at least five previous out-of-time residuals required")
    by_year=_inputs(source,target_coverage)
    history={model:[] for model in MODELS}
    seen_years=0
    scored={model:[] for model in MODELS}
    records=[]
    available_cases=0
    unavailable_cases=0
    for year in sorted(by_year):
        test=by_year[year]
        prior_scores={model:list(history[model]) for model in MODELS}
        # Do NOT update calibration residuals inside the same test year.
        intervals={}
        for model in MODELS:
            radius,rank=(None,None)
            if seen_years>=min_prior_years:
                radius,rank=_quantile(prior_scores[model],target_coverage,min_prior_predictions)
            intervals[model]=(radius,rank)
        for item in test:
            actual=item["actual_effort"]
            outcome={"record_id":item["record_id"],
                     "test_completion_year_code":year,
                     "actual_effort":actual,
                     "effort_unit":source["effort_unit"],
                     "prior_completed_prediction_years":seen_years,
                     "prior_out_of_time_residuals":len(prior_scores["size_only"]),
                     "intervals":{}}
            all_have_interval=True
            for model in MODELS:
                p=item["predictions"][model]
                radius,rank=intervals[model]
                if radius is None:
                    outcome["intervals"][model]={"status":"insufficient_strictly_prior_prediction_residuals",
                        "forecast":p,"lower":None,"upper":None,
                        "prior_residual_rank":rank,"covered":None}
                    all_have_interval=False
                else:
                    lower=p*math.exp(-radius)
                    upper=p*math.exp(radius)
                    covered=lower<=actual<=upper
                    outcome["intervals"][model]={
                        "status":"prior_year_calibrated_empirical_interval",
                        "forecast":p,"lower":lower,"upper":upper,
                        "log_radius":radius,"prior_residual_rank":rank,
                        "covered":covered,"log_interval_width":2*radius,
                        "below":actual<lower,"above":actual>upper,
                    }
                    scored[model].append({"covered":covered,"log_interval_width":2*radius})
            records.append(outcome)
            available_cases+=int(all_have_interval)
            unavailable_cases+=int(not all_have_interval)
        for item in test:
            for model in MODELS:
                history[model].append(abs(math.log(item["actual_effort"]/item["predictions"][model])))
        seen_years+=1

    results={}
    for model in MODELS:
        values=scored[model]
        results[model]={
            "tested_with_finite_interval":len(values),
            "empirical_coverage":sum(v["covered"] for v in values)/len(values) if values else None,
            "mean_log_interval_width":statistics.mean(v["log_interval_width"] for v in values)
                                      if values else None,
            "nominal_target_coverage":float(target_coverage),
            "finite_interval_available":bool(values),
            "coverage_theorem_claimed":False,
        }
    return {
        "status":"strict_prior_year_empirical_interval_audit_not_prospective_coverage",
        "source_id":source["source_id"],"effort_unit":source["effort_unit"],
        "coverage_target":float(target_coverage),
        "min_prior_years":min_prior_years,
        "min_prior_predictions":min_prior_predictions,
        "total_source_project_observations":source["total_project_observations"],
        "forward_test_project_count":len(records),
        "projects_with_all_finite_intervals":available_cases,
        "projects_without_finite_intervals":unavailable_cases,
        "model_results":results,
        "case_intervals":records,
        "unreliable_coverage_warning":True,
        "warnings":[
            "Intervals use only old out-of-time model residuals, never this year's results or future projects.",
            "No interval is emitted until two earlier evaluated years and sufficient past predictions exist.",
            "Historical completion-year grouping and correlated projects violate distribution-free i.i.d. coverage assumptions.",
            "Recorded source drivers may include hindsight information unavailable at original project planning.",
            "This is a retrospective diagnostic. Independent prospective tests of interval coverage are still required.",
        ],
    }


def audit_all_forward_intervals(forward: Mapping[str,Any], *, target_coverage:float=.8) -> dict:
    if not isinstance(forward,Mapping) or forward.get("status")!="retrospective_strict_forward_year_project_effort_validation":
        raise ValueError("requires true strict forward year evaluation")
    sources=forward.get("domains")
    if not isinstance(sources,Mapping) or set(sources)!=set(TEMPORAL_SOURCES):
        raise ValueError("both time-labelled historical datasets required")
    return {
        "status":"prequential_legacy_intervals_not_ai_native_prediction_coverage",
        "target_coverage":target_coverage,
        "domains":{name:audit_forward_intervals(sources[name],target_coverage=target_coverage)
                   for name in TEMPORAL_SOURCES},
        "future_unseen_project_coverage_certified":False,
    }
