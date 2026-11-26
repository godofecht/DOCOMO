# Strict year-forward historical project cost validation

The historical COCOMO81, NASA93, China and Desharnais corpora contain **736 real completed-project effort observations**, though they may overlap across datasets. The previous source-specific project held-outs used leave-one-completion-year-out for NASA93/Desharnais, but that evaluates an earlier project's effort using training outcomes from *later* projects. This is useful exploratory cross-validation but unrealistic for estimating new work from a model available at the time.

DOCOMO v0.16 adds a second evaluation that eliminates this particular form of hindsight leakage.

## Strict training chronology

NASA93 has 93 real projects with 14 distinct completion-year values, measured actual effort in person-months, and COCOMO-I cost-driver ratings. Desharnais has 81 real projects with reported year codes, actual effort in person-hours, and function-point/experience descriptors.

For each year `Y`, the evaluator constructs `train = {all projects with recorded completion year < Y}` and `test = {all projects completed during Y}`. The test year's effort labels are **not** used to determine its own forecasts. Years later than Y are not in training. The project completion year is only a partition key, never a predictor. Models are always refit from scratch using only the earlier projects and training-only standardization, the same frozen ridge penalty and the same three comparators as the existing evaluation.

The three tested models are an earlier-training-set median, log-size-only ridge regression, and log-size plus all recorded cost/complexity drivers. The comparison remains source-specific with **no numerical pooling of person-hours and person-months**.

## No data manufactured for early years

The challenger requires a minimum number of earlier projects to fit its full coefficient basis, specifically `max(20, 3 × feature_count)`. The source importer has fixed feature definitions, and the model is not simplified after looking at test performance. Years with insufficient earlier training observations are labeled **unscored**, with every excluded original project ID preserved.

Every eligible later year is included. The report includes per-year training/test sample sizes, all earlier training year codes, per-year error metrics, every actually scored original case and prediction error, and aggregated log-RMSE, MAE and PRED25. If no year has sufficient prior history, it returns a refusal without a fabricated error score.

## Amendment challenge

The strict-year result is now a separate evidence section in:

```sh
docomo-projects --output real-project-results.json
docomo-scrutiny --output amendment-scrutiny-report.json
```

A proposed amendment must pass its own predeclared historical source-domain screen **and** is challenged by a strict-year defensive screen on NASA93 and Desharnais. This supplementary screen uses the same frozen minimum improvement and maximum regression parameters as the source-domain proposal. It requires no substantial regression in either year-forward domain and a sufficient improvement in at least one. Failed or missing results set `strict_forward_year_screen` to false rather than silently accepting a partial dataset.

Even if both screens succeed, DOCOMO cannot automatically promote an AI-native project-cost model. Planning-time availability of the historical drivers, independent acceptance, model versions and modern labour/machine accounting are not established by these sources.

## What still is not solved

Completion year may not be a true data-availability date. A project's final scope and cost-driver rating may have been measured **after** it was delivered. If so, even a strictly earlier-year *fit* does not make those features eligible for preplanning prediction. These covariates remain retrospective explanations until individually audited.

Projects inside a corporation or programme may be dependent across years; a yearly split is not proof of organisational independence. Historical sources have been repeatedly reused for model selection, so the results are robustness tests, **not an untouched prospective sample**. COCOMO81 and China currently lack reliable completion years in the imported source rows and are not given fictional time indexes or falsely labelled chronological tests.

Prospective validation for a modern domain still requires independently time-stamped planning features, complete accepted and failed projects, complete human and machine evidence, and future repositories selected by a preregistered population rule. The full release criteria remain in [AMENDMENT_GOVERNANCE.md](AMENDMENT_GOVERNANCE.md) and issues #9/#17.

## Falsification tests

The unit suite changes the observed effort of a future test-year cohort and verifies that earlier and same-year forecast values do not change. It also rejects mixed sources, duplicate projects, fabricated completion-year descriptors and unlabeled year groups. A dataset with no eligible future test year reports insufficient prior history instead of manufacturing training data from the future.


## First observed strict-forward results (26 November 2026)

The CI-run actual published project data give:

| Source | Scored later-year projects | Explicitly unscored early projects | Size-only log-RMSE | With historical drivers | Driver change |
| --- | ---: | ---: | ---: | ---: | ---: |
| NASA93 | 30 | 63 | 0.703421 | 0.721194 | **2.53% regression** |
| Desharnais | 49 | 32 | 0.605975 | 0.426338 | **29.64% improvement** |

The existing leave-one-year-out test reported a 22.53% NASA93 improvement with drivers. Under the stricter forward-only chronology the same challenger is worse by 2.53%. The discrepancy is a **counterexample** to claims that an observed historical driver improvement is stable across validation protocols.

The predeclared research amendment permits a regression of up to 5% in either temporal domain and requires at least one sufficiently improving domain, so its *historical robustness screen* still passes. The positive screen does not erase the negative NASA93 result, certify that driver ratings existed at planning, or authorize a DOCOMO AI-native release. Changing the decision criterion retrospectively to force a different pass/fail verdict would itself be poor scientific practice. A subsequent amendment should independently preregister new thresholds and test a genuinely new cohort.
