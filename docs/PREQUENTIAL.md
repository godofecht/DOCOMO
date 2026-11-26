# Prequential uncertainty: no future-year calibration leakage

A point estimate is incomplete without uncertainty. DOCOMO already tests historical NASA93 and Desharnais models using only earlier completed-year outcomes. This module extends that strictly time-respecting evaluation to prediction **intervals**.

## Fixed operational policy

The audit has a declared 80% target coverage, three fixed predictors (training median, log size, and log size plus recorded historical drivers), a minimum of **12 earlier out-of-time residuals**, and at least **two earlier independently evaluated completion-year groups**.

For a test project in year Y, DOCOMO first predicts effort using the model fitted to original project effort labels from years strictly earlier than Y (as in `forward_years.py`). It calibrates the forecast interval around that already-frozen point prediction using the **absolute log residuals of previous out-of-time predictions for years earlier than Y**.

For n prior residuals the quantile rank is `ceil((n+1)*0.80)`. If this exceeds n, or the required number of independent preceding cohorts/observations is unavailable, no finite interval is issued. Otherwise, the resulting radius r yields bounds `[estimate*exp(-r), estimate*exp(r)]`. The quantile is a descriptive historical empirical radius, not a proven distribution-free interval.

Every test year is processed as a batch. Actual outcomes from all projects in year Y enter the calibration history only **after every project in Y has received its intervals**. Changing any held-out same-year or future-year actual effort therefore cannot change the interval bounds issued for Y or earlier years; adversarial tests enforce this invariant.

## Reproducible outputs

```sh
docomo-projects --output real-project-results.json
```

The resulting `strict_prior_year_interval_audit` reports separate NASA93 and Desharnais evidence, and for each case lists its original project ID, completion-year code, actual effort and units, the number of earlier eligible cohorts and prior out-of-time errors, each model's predicted effort, finite lower/upper limits (or null), quantile rank, empirical covered/missed flag and log width.

At the source level it reports how many genuine later-year projects received finite intervals and how many had **insufficient earlier evidence**. For the finite subset it reports empirical coverage and average log interval width for every fixed model. A nominal 80% target does not imply achieved 80% coverage, and the number of evaluated intervals may be small.

CI downloads the original source-pinned project files, recomputes all point and interval forecasts from their actual observed outcomes, and checks missingness accounting and explicit refusal of unsupported prospective coverage claims. No synthetic examples are included in production calibration.

## Limitations

These are historical, retrospective out-of-time residuals; the underlying projects may be correlated and the original cost-driver values may have been recorded after delivery. The finite-sample conformal coverage theorem generally requires exchangeability or other clearly stated assumptions that are not verified here. This method intentionally does **not** present a distribution-free statistical coverage guarantee.

Calendar completion-year grouping is coarse and does not authenticate planning-time availability or ensure organizational disjointness. A project being completed in a prior year does not establish the original features were available before its execution.

A project that receives no finite interval cannot be counted as successful coverage, and a model may have apparent high coverage merely by returning excessively wide bounds. Compare measured width and coverage jointly, plus point error and acceptance failures. A source with insufficient earlier residuals is explicitly unscored rather than supplemented with residuals from the future.

The real AI-native successor requires prospective acceptance-conditioned cost intervals across independent repositories, with a separately estimated project failure probability and full accounting of verification and inference spending. This module is a reusable scrutiny pattern and a stronger diagnostic for historical costs, **not** evidence that AI-native accepted-system delivery uncertainty has already been calibrated.
