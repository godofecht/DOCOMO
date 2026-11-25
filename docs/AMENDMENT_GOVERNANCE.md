# DOCOMO as a continuously falsifiable model

DOCOMO is not a fixed equation to defend. Every amendment must be a versioned, explicitly falsifiable change that can be challenged, withdrawn or overturned when new evidence appears. Correctly predicting a few retrospectively selected projects is not enough to promote a new general-purpose cost coefficient.

## The evidence hierarchy

Every evidence source has a unique identifier, original published source and unit of analysis. Admissions are recorded in `catalog/evidence_registry.json`, with an explicit `data_status`, actual outcome label, original source location, whether independent acceptance was tested, whether actual AI use was measured, supported inferences and forbidden transports.

The hierarchy distinguishes published historical completed-project actual effort, randomized developer tasks with actual measured time, observational human–LLM task executions, industrial estimated-versus-actual user stories, repository repairs with test-suite acceptance, and **prospective whole-project delivery** with complete timesheet/invoice/acceptance evidence. A benchmark sample is not silently promoted from one class to another.

An evaluator cannot transfer METR's treatment ratio into historical person-months, treat successful SWE-bench patches as evidence of zero verification cost, compare person-month RMSE directly with person-hour RMSE, or claim that two source corpora contain unique projects without provenance deduplication.

## Lifecycle of an amendment

**1. Observation.** A reproducible data source motivates a specific failure or residual in the existing model. Record the original row IDs, measurement units, baseline error, source revision and whether features were available at prediction time. Do not discard failed projects, model runs or inconvenient domains.

**2. Candidate.** Submit a GitHub amendment issue and machine-readable proposal. State the *mechanism* and a measurable hypothesis, not just a better score. Fix the champion, challenger, feature timing, affected domains, evaluation metric, minimum improvement, maximum tolerated regression and adverse-effect cohort checks before test results.

**3. Falsification.** Every benchmarked dataset in a declared test family must appear, including negative and null results. `docomo-scrutiny` recomputes all historical source-pinned backtests, rather than trusting hand-entered leaderboard scores. It reports each domain's comparator log-RMSE, relative improvement, regression, and whether the preregistered historical screen succeeded. Regressions and outliers remain visible in future reports.

**4. Independent prospective test.** For promotion beyond exploratory research, preregister cohort selection using `docomo protocol-freeze`, independently verify provider-reported timestamp and pinned protocol bytes with `docomo github-attest`, audit complete project inventories with `docomo protocol-population`, reconcile all original human/machine source ledgers with `docomo study-audit` and `docomo-source-audit`, then evaluate untouched project repositories with `docomo holdout`. Keep task-acceptance and project-cost models separate.

**5. Counterexamples and human scrutiny.** The review issue must link challenged predictions, negative results, failure to preserve security/availability properties, and counterexamples to asserted grounding. A reviewer independent of the author must verify the source and protocol before model activation. Test metrics and any post hoc thresholds are visible to the review. CI is necessary but cannot prove external independence.

**6. Version decision.** Only a complete externally attested prospective evaluation can make an amendment *eligible for independent adoption review*. No CLI automatically merges or declares a model calibrated from a retrospective score. The maintainer must version a decision recording accepted, rejected, provisional or reversed, its scope, supporting evidence and known falsifiers. A published model must not erase the predecessor or its earlier test performance.

**7. Monitoring and reversal.** Monitor drift by task family, repository, tool/model version, requirement semantics and quality demands. Re-run locked challenge suites when models or evaluators change. Failure of preregistered predictive coverage/error, changed independent acceptance or a discovered training/test contamination requires downgrade/rollback to the last independently validated model.

## Automated amendment example

The versioned example `catalog/driver_amendment.json` asks whether historical complexity and cost drivers improve human-effort estimation beyond size alone **across all four real completed-project corpora**. The machine gate requires a declared relative log-RMSE gain in at least three source domains without a serious regression in any source. That threshold is explicitly a *research screen*, not a statistical significance proof or release certificate.

```sh
docomo-projects --output real-project-results.json --records-output real-project-cases.json
docomo-scrutiny --proposal catalog/driver_amendment.json --output amendment-scrutiny-report.json
```

The review output includes `release_gates`, a domain-by-domain falsification record and `requested_model_upgrade_automatically_authorized: false`. Even if every historical domain improves, `release_status` remains `research_candidate_not_eligible_for_ai_native_release`, because the old data contain no independently audited modern accepted-system effort or verified planning-time feature timestamps.

A failure to improve is a useful result, not evidence that DOCOMO should quietly tweak the threshold until the result looks favourable. Any new threshold must be a new versioned proposal evaluated against different held-out data.

## Invariants enforced today

An amendment cannot cherry-pick fewer than all four historical cost domains in the initial screening family. It must declare exact cost-target type, champion, challenger, frozen decision criteria and data feature timing. Sources must be in the evidence registry with the same unit and expected sample count. The reviewer cannot claim audited planning-time features from sources that do not publish such timestamps. No current retrospective evidence qualifies an automatic AI-native project-cost release.

CI reruns all actual-source data acquisition and benchmark calculations for each relevant code change, uploads normalized per-project observations and numerical reports, and runs the amendment challenge with the negative outcomes present. All data files have immutable commit/blob references and are re-downloaded only when verified unchanged.

## Critical limitations and future generalisation

The current machine scorer covers **one benchmark family**, four historical effort datasets, and three simple comparator models. It does not yet implement executable specification-level counterexample search, economic calibration for mixed human-plus-inference costs, fair pre/post agent comparisons with independent whole-project acceptance, or statistically powered model comparisons on contemporary projects. Those will require new frozen candidate configurations and their own baseline-specific validators.

The historical folds are not externally prospective and some covariates are hindsight measurements. Improvement of the recorded historical log-RMSE is an invitation to gather better evidence, **not** a license to rewrite AI productivity economics.

The Mendeley ten-project user-story corpus still needs original spreadsheet retrieval and a preregistered project-ID split. SWE-bench Verified and Pro require actual immutable issue/patch/test traces and independent agent run results. They cannot fill project cost gaps without real observed human and machine expenditure.

Issue #9 tracks acquiring independently accepted AI-native projects. Issue #17 tracks external evidence authenticity and complete prospective intake. Every claimed new result should either pass those gates or remain an explicitly incomplete, refutable conjecture.

## A concrete target for DOCOMO 1.0

Declare a precise use domain (e.g. a class of AI-assisted repository enhancements with independent acceptance), externally register the sampling and evaluation policy, collect complete labor/machine/verification costs with failures, evaluate on untouched projects from independent repositories, and show calibrated predictive coverage and improvement over *correctly matched* historic COCOMO II, size-only and a scalar AI treatment baseline. Run ablations separating specification grounding, coding, verification, orchestration, integration and rework.

The result must report both what the model predicted correctly **and where it failed**. Calibrated status is bounded by a clearly stated task population, evaluator version and time horizon, and can be revoked when monitoring detects distribution shift. DOCOMO 1.0 is not an eternal law; it is a model allowed to be wrong in ways that can be measured.
