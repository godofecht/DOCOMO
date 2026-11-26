# Real completed-project effort corpus

DOCOMO collects **published actual project effort records**, not estimated or model-generated labels. Raw source bytes are retrieved at immutable commits and checked against Git blob SHA-1 before parsing; the project records and evaluation report are generated as GitHub Actions artifacts rather than copies of external datasets committed to this repository.

## Imported project observations

| Source | Records | Actual label | Size proxy | Evaluation |
| --- | ---: | --- | --- | --- |
| COCOMO81 | 63 | Person-months | KSLOC | Historical ID-modulo-five holdouts |
| NASA93 | 93 | Person-months | Equivalent physical KSLOC | Leave-one-completion-year-out |
| China | 499 | Person-hours | Adjusted function points (AFP) | Historical ID-modulo-five holdouts |
| Desharnais | 81 | Person-hours | Adjusted function points | Leave-one-completion-year-out |
| Kitchenham | 145 | Person-hours | Adjusted function points | Retrospective ID-group holdouts; recorded human first estimate |
| Maxwell | 62 | Person-hours | Function points | Retrospective source-row-index-group holdouts |

All six are sourced from [Derek Jones's collected public software estimation datasets](https://github.com/Derek-Jones/Software-estimation-datasets/tree/e3fbd4faa2a5aec94b06535369664c3ebbcbac39), fixed at commit `e3fbd4faa2a5aec94b06535369664c3ebbcbac39`. COCOMO81, NASA93, China, Desharnais, Kitchenham and Maxwell have pinned source blob digests in `src/docomo/datasets.py`.

Their total is **943 historical project observations**, NOT a proven unique set of 736 independent projects. COCOMO81 and NASA93 have overlapping origins and can contain overlapping projects; their record IDs are dataset-local. Never pool, deduplicate heuristically, or sum their samples to inflate a generalisation claim.

All observations represent historical completed effort, not validated modern acceptance, machine expenditure or AI-assisted development. The dataset descriptions refer to real original project logs and secondary compilations, but DOCOMO has **not** independently audited each original project timekeeping record. Historical size/complexity variables may describe the final product, not what managers knew at the start of work. It is therefore invalid to claim they are ex-ante forecasting features without a separate timeline audit.

## Data ingestion and labels

The `docomo-projects` command loads all 736 records and validates source checksums, row counts, unique IDs within each dataset, positive actual effort and plausible feature fields.

For China, the label is `Effort`, representing actual person-hours. The secondary variable `N_effort` is explicitly **excluded** because it is a normalized effort outcome that may differ and cannot be quietly substituted into calibration. `Duration` is excluded as it is post-execution information.

For Desharnais, the label is `Effort` and size is `PointsAjust`. `Length` and completion year are not used as predictors; completion year is used **only** to hold out a historical cohort. Experience fields coded `-1` are handled using explicit missingness flags instead of silently interpreting `-1` as negative years.

For NASA93, the label is `act_effort`, size is `equivphyskloc`, and the fifteen ordinal COCOMO-I effort ratings plus development mode are candidate explanatory features. The original mode and year fields are not confused with modern COCOMO II scale factors.

For Kitchenham, the original source reports first human effort estimates and actual later person-hours for 145 project rows. Ten original project-type values are missing and get explicit missingness indicators instead of fabricated types. The human first estimate is a separately evaluated **human baseline**, not a prediction made by an AI coding agent. All 145 source project IDs are retained.

For Maxwell, the original immutable ARFF contains **62 actual project rows**, even though secondary papers sometimes report 63. The 15 ordinal technology factors are summarized by a fixed mean rather than fitting 15 uncalibrated coefficients on a 62-row training set. The source row index is used only as the within-file identifier; it does not imply a stable organizational project ID or a time-based holdout.

For COCOMO81, the known effort adjustment factor and development mode provide the additional explanatory drivers. Published source rows, no generated numbers, determine the dependent variables.

The normalized export preserves per-observation source ID, original local project number, declared effort and size units, actual effort, candidate features, cohort grouping and descriptor fields. `independent_acceptance_verified`, `ai_use_measured` and `external_cost_ledger_audited` remain **false** across historical records.

## Benchmark model, holdouts and negative findings

The baseline predicts log effort using log size only. The challenger adds recorded cost/complexity descriptors. Both use fixed ridge-regularized linear regression with **training-fold-only feature standardization and fitting**. A training median comparator prevents improvements over a particularly weak size-only baseline being overinterpreted.

Leave-one-year-out is used for NASA93 and Desharnais when completion years exist. It is not strictly a forward-chaining forecast: training on other years may include work **later** than a test project's completion year. COCOMO81 and China lack unambiguous original completion dates in the respective prepared files and therefore use historical ID-modulo-five holdouts. These splits are retrospective, not real untouched prospective deployments, and related organizational projects may span folds.

Each separate dataset reports MAE, median absolute and relative error, log-RMSE and PRED25, plus improvement/regression against the size-only model. A reported historical improvement is an exploratory association, not proof that new predictors work before project completion.

Run:

```sh
pip install -e .
docomo-projects --output real-project-results.json --records-output real-project-cases.json
docomo-projects --dataset-dir .docomo-cache --offline --output reproduced.json
```

The command refuses missing/corrupt source files in offline mode. CI downloads the exact pinned originals, evaluates all six domains and uploads an artifact containing both **all real observation rows** and their source-specific metrics.

## Other actually evaluated engineering work

The [evidence registry](../catalog/evidence_registry.json) distinguishes actual historic project cost from METR's 246 randomised human-AI tasks, Alaswad's 330 measured human–LLM task executions, the January 2026 industrial study of **ten completed projects with over 100 user stories**, and the 500 human-validated issue repairs in SWE-bench Verified. Those are different experimental outcomes.

The industrial study [DOI 10.17632/ytmwsf2997.2](https://data.mendeley.com/datasets/ytmwsf2997/2) includes real story-level person-hours and estimates from human experts and several AI tools; the AI tools *estimated* historical work, they did not necessarily implement it. Its original XLSX has not yet been downloaded or authenticated in this project, so it is registered for ingestion rather than falsely counted as an analysed cohort.

[SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified) contains 500 human-validated repository issue/PR problems and independent task-specific tests. Those are excellent case studies of behavioural verification but do not publish end-to-end project person-hours. The corpus stays separate until an immutable benchmark snapshot and reproducible evaluation traces are obtained.

[SWE-bench Pro](https://labs.scale.com/leaderboard/swe_bench_pro_public_v2) reports 1,865 complex tasks spanning 41 professional repositories but includes public and restricted evaluation subsets. DOCOMO does not misrepresent all tasks as publicly reproducible or as person-month cost evidence.

The correct next step is to attach independently observed **time/cost** and **acceptance oracles** to future eligible project cohorts, not synthesize those labels from commit dates or patch sizes.
