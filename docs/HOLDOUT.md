# Repository-disjoint prospective calibration of accepted effort

DOCOMO's `holdout` mode evaluates a preselected model on separately collected projects. It is not a certificate of general AI-era calibration.

## Protocol

The JSON input is an object with `schema_version: "1.0"`, `selected_model` (one of `docomo_scope`, `size_only`, `cocomo2_nominal_assumptions`), `registered_at` (offset-aware ISO 8601 date), `registration_uri` (external HTTPS protocol link), `target_repository_coverage` (0.5 to below 1), and nonempty `train`, `calibration`, `test` arrays of full project manifests.

Train, calibration and test must use completely disjoint repositories and project IDs. The training and calibration planning timestamps must precede registration; test planning timestamps must not precede it. This is a *structural assertion*, not cryptographic proof that a preregistration or independent reviewer exists. The result explicitly flags these details as unverified.

The selected model fits human working minutes on accepted training projects only. It does not get access to calibration or test outcomes during coefficient fitting, and the evaluator never selects a model by test performance. The `docomo_scope` design uses preplanned functional units, dependencies, verification obligations, ambiguous requirements and workflow indicators. The `size_only` comparator uses equivalent KSLOC. The historical reference is COCOMO II.2000 Post-Architecture at nominal ratings, translated using a declared 152-hour person-month convention, not a fully rated COCOMO II benchmark.

## Honest group-conformal uncertainty

For each accepted calibration project compute absolute log error `r_i = |log(y_i / prediction_i)|`. For each calibration repository, calculate `R_repo = max(r_i)` among its accepted projects. Sort the repository-level maxima. At requested group coverage `q`, select order statistic `ceil((n+1)*q)` from `n` independent accepted calibration repositories. If the required index exceeds `n`, DO NOT issue a finite interval.

For a new accepted project, the interval is `[point * exp(-R), point * exp(R)]`.

Under exchangeable independent repository groups, with a fixed training-only predictor, the procedure targets marginal coverage for all accepted-project errors in a new repository. It provides **no** guarantee when groups are nonexchangeable, acceptance rules change, the test distribution shifts, or data are selectively reported. Effective sample size is the number of calibration repositories, not the number of tasks.

The held-out evaluation reports log-RMSE, MAE and other errors on *accepted test deliveries only*, and interval coverage by accepted project and by repository. It also reports attempts, failures, and *observed* total human and machine cost including failed projects in all three cohorts. These latter quantities are descriptive and do not imply a model of future unconditional cost or probability of acceptance.

## Guardrails

Requires at least eight training repositories and 30 accepted training projects, ten accepted calibration projects, and four held-out test repositories. Rejects duplicate project IDs, any repository spanning multiple partitions, incompatible domains/currencies, non-positive accepted human effort, missing feature data, invalid date formats, and explicitly synthetic records in production CLI mode. Finite 90% group intervals require at least nine calibration repositories containing accepted projects. Structural thresholds are provisional checks, **not** formal statistical-power guarantees.

Unit tests use synthetic manifests with explicit `allow_synthetic=True` and label outputs accordingly. No synthetic outcome is treated as empirical calibration.

## Run

```sh
docomo holdout path/to/locked-experiment.json
```

The protocol URL and independent acceptance source are supplied by data owners, not audited by the CLI. Independent review and representative prospective data remain prerequisites for declaring a calibrated successor. See `docs/NATIVE.md` and issue #9.
