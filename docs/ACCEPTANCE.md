# Acceptance-risk evaluation for AI-native software delivery

DOCOMO previously fitted development effort only on successfully accepted projects. That is a **selection-conditioned outcome**, and a smaller prediction error on accepted deliveries does not establish low total cost when many projects fail.

The `acceptance_evaluation` field in `docomo holdout <experiment.json>` separately evaluates whether a project meeting a fixed independent acceptance protocol will pass. Every attempted project contributes its success/failure outcome, including abandoned and failed work. No project is discarded for failing acceptance.

## Target and evaluation design

For a specified project population and frozen oracle, `accepted` is a binary outcome. Predictors are restricted to project features fixed at planning time: functional scope, dependency edges, verification obligations, ambiguous requirements and chosen workflow category. No post-implementation retries, tests, defect counts, billing charges or human labor outcomes enter the model.

The parent `holdout` evaluator requires training, calibration and final test cohorts with non-overlapping repositories. This module receives **already validated** project manifests from those cohorts. It never repartitions projects or optimizes features on the test set.

The model is a ridge-regularized logistic regression fitted to **training outcomes only**, using standardized planning features. Separately, a single intercept adjustment is fit on **calibration outcomes only**, without changing other coefficients. The untouched test cohort is evaluated once.

Three non-selected comparators are reported on exactly the same test projects: the training-cohort acceptance rate, the training-only logistic model, and the calibration-intercept-adjusted logistic model. Output includes Brier score, mean Bernoulli log loss, empirical test acceptance rate, average predicted probability, and Wilson confidence interval for the observed test rate. These are distinct from the accepted-project cost regression and its split-conformal intervals.

## Limits and refusal

The acceptance model requires at least 50 recorded training attempts, including at least 8 successes and 8 failures, plus 20 calibration attempts, including at least 4 successes and 4 failures. Missing class diversity produces `insufficient_acceptance_evidence` with no coefficients or predicted probability. The screening thresholds are pragmatic safeguards, **not a validated statistical power guarantee**.

A dataset containing exclusively successful projects cannot determine the probability that future projects will fail. DOCOMO explicitly refuses to infer that probability from the successful subset.

External acceptance evidence remains self-attested unless separately independently audited. Project outcomes are not necessarily independent across developers, organizations or customer requirements. Even good held-out test Brier scores do not guarantee out-of-domain calibration; changes to evaluation policy, agent model, system quality demands, workflow or task population require retesting.

The output is **not a causal AI benefit estimator**, and it does not yet compute expected unconditional cost of delivering an accepted system. A project cannot generally be repeated as an identical independent Bernoulli trial; attempts on distinct requirements have changing scope and dependency structure. Multiplying accepted-conditional engineering cost by the inverse of a purported completion probability would therefore be unjustified without an independently validated retry/abandonment model.

## Run

```sh
docomo holdout prospective-experiment.json
```

Inspect `acceptance_evaluation` alongside `test_metrics_conditional_on_acceptance`, `test_interval_evaluation` and `split_counts`. For insufficient evidence, acceptance status is explicit and forecasts are omitted. Test fixtures are synthetic and remain opt-in only through Python unit tests; production CLI refuses any project tagged synthetic.

True general AI-era COCOMO calibration still requires a representative and prospectively audited cohort with independently verifiable software acceptance, original human effort records, machine invoices and future-project test outcomes.
