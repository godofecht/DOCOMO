# DOCOMO empirical calibration: dataset domains, limits, and acceptance gates

## Status as of November 2026

The project supports **partial, domain-specific empirical calibration**, not yet general AI-native project estimation. A usable COCOMO successor requires representative contemporary, accepted-delivery project records with measured human hours, machine expenditure, acceptance outcomes, and specification/verification constraints. These outcomes are unavailable in the two compatible public datasets. Refuse to assign an unqualified "calibrated successor" badge.

The publicly reproducible calibration spans **two independent domains**.

### Domain A: historical project effort

The [Derek-Jones COCOMO81 dataset](https://github.com/Derek-Jones/Software-estimation-datasets/blob/e3fbd4faa2a5aec94b06535369664c3ebbcbac39/COCOMO-81.csv) contains 63 historical projects, size expressed in KSLOC, observed effort in person-months, development modes and 15 COCOMO-I effort multipliers. Data are pinned by Git commit and Git blob checksum.

Reference baseline (Intermediate COCOMO **I**, not COCOMO II):

    effort = mode_coefficient * KSLOC**mode_exponent * product(all_15_driver_multipliers)

Mode coefficients and exponents: organic (3.2, 1.05); semidetached (3.0, 1.12); embedded (2.8, 1.20). Source: Boehm-era Intermediate COCOMO parameter tables. This formula must not be labelled "unmodified COCOMO II": that model has distinct factors and an exponent including scale factors not present in this dataset.

DOCOMO evaluates fixed Intermediate COCOMO I against log-linear size-only, globally recalibrated COCOMO I, and size/mode/effort-adjustment regression. K-fold assignment is deterministic by recorded project ID (ID modulo fold count). Coefficients fitted on the full dataset are shown separately from out-of-fold predictions. Report log-RMSE, MAE, MdAE, median relative error and PRED25. Small size and unknown project-family dependencies limit confidence in real-world generalisation. Choosing the smallest cross-validated error and publishing full-data coefficients is *exploratory model selection*, not an unbiased independent final benchmark.

### Domain B: early 2025 AI-assisted task time

The [METR early 2025 randomised trial](https://github.com/METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs/blob/7ff2d7670235f531dff77eff58355bd77392f396/data_complete.csv) comprises 246 developer tasks from 16 experienced open-source developers. Task-level randomisation permitted or prohibited AI tools. The primary published specification uses:

    log(total_implementation_time_minutes)
        = intercept + beta_size * log(pre_randomisation_no_AI_time_estimate_minutes)
          + beta_AI * AI_allowed

where total time is initial implementation plus post-review changes, with missing post-review times imputed by the corresponding treatment-group mean as in the original paper.

The estimated conditional task time ratio is `exp(beta_AI)-1`. An estimate of **+0.1884** reproduces the published **+0.188** (about 18.8% longer under AI for these tasks and tools). We additionally compute deterministic developer-cluster bootstrap percentile intervals and out-of-fold metrics withholding developers from training, including an ablation without the AI indicator. Developer-cluster bootstrap is appropriate to the task clustering but with 16 developers is still uncertain. It is not a replacement for the paper's specified robust/clustered analytic CI.

The study's task-time model is **not** a COCOMO productivity multiplier, and cannot be multiplied into historical project person-month forecasts. It is also **not** a measured independent safety, performance, or functional assurance model. The tasks were completed under that research protocol, not an externally audited whole-project acceptance contract.

### Domain C: late 2025 follow-up

A [larger METR follow-up](https://github.com/METR/Measuring-Late-2025-AI-on-OSS-Devs/blob/55f007216a26493f0a9b7650ab3191cad7fb9e7f/data.csv) exists, but investigators warn that changed recruitment and participation-selection effects compromise treatment-effect interpretation. It is intentionally **not pooled** with the early trial. A future branch may provide an explicitly labelled exploratory sensitivity analysis, not a transportable coefficient.

## Reproducibility

All dependencies are from the Python standard library. Raw observations remain in the upstream repositories. DOCOMO retrieves immutable commit-pinned CSVs, verifies their Git blob SHA-1 before any analysis, and caches them in .docomo-cache (not tracked). No upstream data are silently mutated or rehosted.

    pip install -e .
    docomo-calibrate --output calibration-report.json
    docomo-calibrate --dataset-dir .docomo-cache --offline --output repeat.json
    python -m unittest discover -s tests -v

GitHub Actions runs the calibration, validates task and project row counts and reproduction of the published METR treatment effect, and uploads the full calibration JSON as a CI artifact.

The report separates coefficient estimates, out-of-fold performance, sources, warnings and explicitly **unsupported inferences**. It does not yet include prospective uncertainty-calibrated *project* prediction intervals.

## Qualification gates for a calibrated AI-native COCOMO successor

A model may be considered fully calibrated for a stated use-domain only when:

1. The task/project population is precisely defined. Requirements, codebase snapshots, model versions, environment and acceptance oracle are versioned and their provenance audited.
2. Target labels are *actual human engineering effort, non-overlapping compute/machine expenditure, wall-clock completion time and independently accepted functionality*. There must be enough projects to estimate these quantities, not just task-level time.
3. Specification ambiguity, confidence in verification, dependency complexity, and requirements change are measured in advance, without leaking acceptance outcomes into predictor features.
4. Historic COCOMO II is implemented with the actual five scale factors and relevant effort multipliers; otherwise a historical COCOMO-I comparison is labelled accordingly.
5. Calibration and final evaluation data are disjoint by project/repository or future time cohort. Model selection and interval calibration happen entirely inside the training/validation partition; held-out data are used only for final assessment.
6. Final report publishes absolute and relative error, predictive interval coverage, successful acceptance probability, cost/time unit definitions, heterogeneity, source provenance and identified limitations.
7. AI effect estimates from unrelated developer populations or tool generations are not silently transported into project effort. New model versions trigger domain drift validation and re-calibration.

Until these gates pass, DOCOMO should stay in an explicit **partially_calibrated / insufficient_evidence_for_general_ai_project_estimation** state.

## Source references

- Barry Boehm, *Software Engineering Economics* (1981), Intermediate COCOMO model.
- Derek Jones, [COCOMO-81 project dataset](https://github.com/Derek-Jones/Software-estimation-datasets).
- Joel Becker et al., *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*, [paper and analysis](https://arxiv.org/abs/2507.09089).
- METR, [expanded experiment caveats](https://metr.org/blog/2026-02-24-uplift-update/).
