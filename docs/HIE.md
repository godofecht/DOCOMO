# HIE 2026: real human–LLM task measurements, without forecast leakage

## Evidence

Feisal Alaswad et al. (2026), *Hybrid intelligence effort for software effort estimation in LLM assisted development*, Discover Computing 29, article 424. DOI: [10.1007/s10791-026-10331-6](https://doi.org/10.1007/s10791-026-10331-6).

The authors report a controlled study with 22 developers, 110 tasks and three LLMs. Their released `Task_execution_observations.csv` contains **330** execution records and measures task-completion time, Story Points, model used, interaction counts, modified files, validation problems and manual corrections. DOCOMO pins the upstream repository at commit `09e105d5a7fb3f15e5412d688dbf79d21c42329b` and checks the Git blob hash `428cc5078962adadd3939289b3bec0ffe6e4ead5`. The original data remain at [the upstream repository](https://github.com/FeisalAlaswad/Hie_effort_estimation/blob/09e105d5a7fb3f15e5412d688dbf79d21c42329b/Task_execution_observations.csv), rather than being republished inside DOCOMO.

The paper explicitly calls the research an *exploratory, explanatory investigation*, not a finalized predictive cost-estimation model. The public CSV lacks original task and repository identifiers, so no test partition can guarantee that comparable or identical tasks do not appear in more than one fold. It also contains no human-only condition, no inference expenditure, and no independently auditable release-acceptance result.

## Two incompatible estimation settings

A planning-time prediction must use only information available *before execution*. DOCOMO compares the median duration observed in training developers, Story Points alone, and Story Points plus the **assigned** LLM. These are the only allowed forward-looking models in the benchmark.

For an explanatory, explicitly **post-execution diagnostic**, it additionally includes prompt iterations, corrective prompts, context prompts, files modified, validation issues and manual corrections. Those variables emerge while the work is already underway; they may be consequences of complexity, consequences of duration, or parts of the process mediating duration. The diagnostic is **not** a deployable ex-ante estimator, even if its held-out numerical error is smaller.

Avoid the particularly misleading analysis of assigning a low future-cost prediction to a task simply because an engineer needed few corrective prompts, when the number of corrective prompts is unknown at estimation time.

## Reproducible validation

The HIE benchmark is invoked by `docomo-calibrate` and written separately as `hie_task_process_diagnostics` in its JSON output. It uses developer-group-held-out folds: each developer's observations appear only in the training or test side of any given fold. The regression target is log(minutes) and the models use training-only standardization with fixed ridge regularisation. Report log-RMSE, MAE, median absolute and relative errors, and PRED25.

All four models are evaluated on the same held-out observations. Their comparison is **descriptive**: it is not a causal estimate of AI productivity, and the source design offers no untouched project-level verification set. The grouping does not solve unknown duplicated task identities, project dependencies, or selection of the 110 task examples. In particular, do not interpret differences between the three LLM assignments as a controlled counterfactual estimate without further identification and randomization checks.

Run:

```sh
pip install -e .
docomo-calibrate --output calibration-report.json
```

Read the `hie_task_process_diagnostics` object. To demonstrate integrity protection, deliberately altering any cached CSV causes a checksum mismatch rather than silently refitting.

## Relevance to DOCOMO

This study provides directly observed **task completion time in an AI-assisted context** and helps evaluate the hypothesis that execution-time verification and interaction measures explain variation beyond traditional planning proxies. It does not identify separately measured construction, verification and integration person-hours, does not measure assurance-adjusted outcome quality, and cannot calibrate the economics of an accepted software project. For those requirements, collect prospective original human-time and machine-billing ledgers under `docs/LEDGER.md` and repository-disjoint independent acceptance under `docs/HOLDOUT.md`.

This is a deliberate third, separate empirical domain, alongside historical COCOMO81 project effort and the early-2025 randomized METR task-time treatment experiment. Pooling them as if they measured the same estimand would invalidate the study.
