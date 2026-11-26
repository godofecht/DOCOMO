# DOCOMO

**Decision-Oriented Complexity and Model-grounding Observatory**

DOCOMO is an experimental framework for assessing AI-assisted software cost without assuming that line count, model confidence, or a single complexity rating captures the difficulty of delivering correct behaviour.

**Grounding:** given explicitly supplied plausible interpretations, decisions, decision losses, and evidence likelihoods, the evaluator computes EVPI and EVSI. It also supports no-prior minimax regret and explicit finite-prior sensitivity, without inventing probabilities.

**Complexity:** given independently assessed trials of human or AI-assisted workflows, the evaluator reports observed human cost, machine cost, elapsed time, and acceptance uncertainty. It only qualifies a strategy for a stated reliability target when the Wilson confidence lower bound clears that target.

DOCOMO now includes **partial empirical calibration** for historical project effort and early-2025 AI-assisted task duration. It is **not yet a generally calibrated AI-native COCOMO successor**: its public datasets do not contain the contemporary end-to-end verified project costs necessary for that claim. The mathematical specification, evidence assumptions, limitations and development roadmap are in [docs/MODEL.md](docs/MODEL.md). A falsification-oriented calibration plan is in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md).

## Usage

Requires Python 3.11 or newer.

```sh
python -m pip install -e .
docomo grounding examples/scheduler.json
docomo robust-grounding examples/robust-scheduler.json
docomo complexity examples/strategies.json
docomo cocomo2 examples/cocomo2-nominal.json
docomo manifest examples/project-manifest.json
docomo ledger examples/effort-ledger.json
docomo protocol-freeze examples/prospective-protocol.json
docomo readiness examples/project-manifest-list.json
docomo native-calibrate examples/project-manifest-list.json
docomo-calibrate --output calibration-report.json
docomo-forecast --report calibration-report.json --input examples/forecast-task.json
docomo-forecast --report calibration-report.json --input examples/forecast-historical.json
python -m unittest discover -s tests -v
```

The JSON examples are illustrative inputs, not empirical findings. The CLI rejects incoherent probability or cost tables instead of making up missing values.

Grounding may return `not_decision_relevant`, `additional_grounding_worthwhile`, or an explicitly unresolved result. Complexity may return `insufficient_evidence_for_target`; few perfect trials are not sufficient for a reliability claim.

## Empirical calibration

The [calibration specification](docs/CALIBRATION.md) documents COCOMO81 project-level baselines and the original 246-task METR randomised study. The calibration tool downloads immutable upstream snapshots, verifies their Git blob hashes, estimates fitted coefficients, evaluates out-of-fold prediction errors, and reports a developer-cluster bootstrap interval for the task treatment effect. It reproduces the published METR AI time ratio increase of approximately 18.8% without treating it as a universal AI multiplier. The full JSON report is published as a CI artifact.

A third independent [2026 human–LLM task benchmark](docs/HIE.md) uses 330 observed task executions from 22 developers and three LLMs. It compares planning-time Story Points and assigned model against **retrospective** interaction measures, with developer-held-out folds. It explicitly prohibits using post-execution corrections as ex-ante predictors and does not claim project-level AI cost calibration.

The [external evidence register](docs/EVIDENCE_SOURCES.md) identifies real public datasets and states which conclusions each supports and why they cannot be silently pooled into a global AI productivity coefficient.

## AI-native calibration research engine

The `native-calibrate` mode implements a prospective, strictly gated project-level human-effort regression and compares repository-group-held-out predictive errors against a size-only model and a nominal-assumptions COCOMO II reference. It requires 50+ project records, 8+ repositories, independent acceptance links and detailed non-overlapping human time accounting. Synthetic fixtures are explicitly rejected in the default production mode. **No qualified AI-native data corpus is bundled or claimed, and group CV is not an independent prospective certification.** See [docs/NATIVE.md](docs/NATIVE.md).

## Prospective repository-disjoint evaluation

`docomo holdout <experiment.json>` requires an explicitly selected model, immutable preregistration URL and timestamp, and three distinct sets of repository-level project manifests: `train`, `calibration`, and `test`. It fits a model **only** on training projects, constructs log-scale prediction intervals from worst accepted-project residuals by calibration repository, and evaluates the withheld test repositories once. Failed project outcomes are reported separately; all output remains conditional on acceptance. Insufficient calibration repositories produce no finite interval rather than fabricated precision. External audit of self-attested evidence and a genuinely predeclared independent test set remain required. See [holdout specification](docs/HOLDOUT.md).

## Failure-aware acceptance evaluation

The prospective `docomo holdout` report now contains a distinct `acceptance_evaluation` section. When there are sufficient **both accepted and failed** projects, it fits a planning-only acceptance logistic model on training repositories, adjusts its intercept using separate calibration repositories, and scores untouched test projects against a training-prevalence baseline. It reports Brier/log-loss and observed acceptance confidence intervals, not an unverified guarantee or an unconditional cost forecast. If only successful deliveries were recorded, it explicitly refuses to invent a failure probability. See [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md).

## Measurement evidence ledger

The `docomo ledger` command reconciles each of seven human-effort stages against per-actor UTC work-session evidence and checks that non-overlapping time and source-linked machine billing records reproduce the project manifest totals. It explicitly labels source claims as **not independently authenticated**, rather than treating HTTPS URLs or declared reviewer independence as proof. [Evidence collection protocol](docs/LEDGER.md).

## Study-wide evidence integrity

`docomo study-audit <bundle.json>` reconciles **every** project in training, calibration and test against a detailed human/machine activity ledger. It verifies study-wide unique event IDs, no contributor-time double counting across projects, compatible data domains, independent repository partitions and a canonical SHA256 fingerprint of planning-time features **excluding observed outcomes**. It refuses synthetic production evidence and returns `cost_ledgers_and_planning_reconciled_not_authenticated`, never a certificate of external preregistration. See [the study audit protocol](docs/STUDY_AUDIT.md).

## Pre-outcome selection and study enrollment

`docomo protocol-freeze` freezes inclusion and exclusion **rules** before test projects even exist. The independent `docomo protocol-population` operation compares a complete source inventory to the preregistered repositories, enrollment windows, fixed model and acceptance oracle, refusing missing eligible attempts and other unregistered exclusions. The module deliberately does **not** trust self-issued timestamps, user-supplied inventory completeness or GitHub URLs as proof of independent external registration. [Protocol design](docs/PROSPECTIVE.md).

## GitHub server-side registration attestation

`docomo github-attest <attestation.json>` verifies an explicit GitHub Actions **push** run ID, its GitHub-server-reported creation time, the immutable commit SHA used by the workflow run, and the exact checked-out protocol JSON at that commit. Authored/committer timestamps are ignored because Git clients can backdate them. It verifies the Git blob checksum and canonical protocol digest. The output distinguishes this provider-verified timestamp/content check from **unverified** study-population completeness, evidence authenticity and independently accepted software. See [GitHub attestation protocol](docs/GITHUB_ATTESTATION.md).

## Primary evidence file verification

`docomo-source-audit` now requires source **file bytes** behind every human time entry, machine invoice, review record, and acceptance report. SHA-256 checks match copies to ledger entries, reject missing or tampered source files and unsafe local paths, and report duplicate bytes used for multiple sources. It does not authenticate the external publisher or prove the files are truthful. See [docs/SOURCE_AUDIT.md](docs/SOURCE_AUDIT.md).

## Real evaluated projects and adversarial model amendments

`docomo-projects` fetches four immutable, checksum-verified original datasets and exports **736 actual completed-project effort records** (63 COCOMO81, 93 NASA93, 499 China and 81 Desharnais), retaining separate units and warning about possible repeated projects across sources. It runs leave-one-completion-year-out validation where a year exists and clearly labelled retrospective ID-group folds otherwise. [Source and validation rules](docs/REAL_PROJECTS.md).

`docomo-scrutiny` recomputes all those historical benchmarks and challenges a versioned amendment proposal, publishing **negative results and regressions** as first-class evidence. Historic improvements cannot automatically promote a model for AI-native project cost estimation. The [evidence registry](catalog/evidence_registry.json) also distinguishes real developer-time trials, industrial actual-hours story estimates awaiting original-file ingestion, and functional-code acceptance suites such as SWE-bench Verified from actual total project effort. [Evolution protocol](docs/AMENDMENT_GOVERNANCE.md).

```sh
docomo-projects --output real-project-results.json --records-output real-project-cases.json
docomo-scrutiny --output amendment-scrutiny-report.json
```

## Human-validated real repository repairs

With the optional `pyarrow` package, `docomo-repairs` retrieves a SHA-256-pinned **500-case SWE-bench Verified** snapshot and produces a real issue/commit inventory covering distinct repositories. Gold patch and test bytes never enter candidate-agent exports. The records support independent **functional repair acceptance** through the official SWE-bench test harness, but contain neither observed human effort nor machine costs. No agent success rates are claimed without replay logs.

```sh
pip install -e '.[repair]'
docomo-repairs --index-output verified-repair-index.json
docomo-repairs --agent-prompts-output local-repair-prompts.jsonl --index-output local-repair-metadata.json
```

See [docs/REPAIR_CASES.md](docs/REPAIR_CASES.md) for the evaluation boundary.

## Evaluation outcome intake and honest failure accounting

Once an independent evaluator runs the official SWE-bench harness, `docomo-score-repairs` can score its genuine `results.json` (schema version 2) against the pinned 500-case inventory. It refuses unknown or omitted instance IDs, overlap between pass/fail/error categories, inflated counts or a changed source revision. **All 500 cases remain in the denominator**, including evaluation failures and unsubmitted patches. Scores stay marked *run logs unverified* until an independent auditor checks the actual official Docker/test logs and sandbox policy. See [docs/REPAIR_SCORING.md](docs/REPAIR_SCORING.md).

## Original industrial user-story effort, no invented workbook schema

`docomo-industrial inspect original-v2.xlsx` reports the original workbook SHA256 and actual visible/hidden worksheet names. Once the official [Mendeley version 2 dataset](https://data.mendeley.com/datasets/ytmwsf2997/2) has been obtained, fill in the exact source headings, sheet and digest in `catalog/mendeley_v2_mapping.template.json` and run `docomo-industrial score` with that mapping. It insists on **ten original projects, over 100 complete stories, actual numerical person-hours and every original human/AI estimator**, rejecting missing labels, duplicate stories, formula-derived values and mismatched versions. The report gives per-project/pooled error and paired project-cluster bootstrap differences, never claims AI coding productivity. Until the original v2 workbook can be downloaded, this source remains **identified but not ingested** in the evidence registry. [Full specification](docs/INDUSTRIAL_STORIES.md).

## No future-project leakage in historical backtests

`docomo-projects` and `docomo-scrutiny` now run an additional **strict earlier-to-later** challenge on the real NASA93 and Desharnais year-labelled projects. Each year's effort models are fitted *only* on earlier completed years; records from early years without enough predecessors are explicitly excluded rather than using later outcomes to fit a model. The scrutiny report publishes regression failures and a distinct `strict_forward_year_screen` gate. Historical source features may still be retrospective, and these tests are not certification of AI-native accepted-project cost. See [docs/FORWARD_VALIDATION.md](docs/FORWARD_VALIDATION.md).

## Scope

Phase 0 implements decision-theoretic grounding, observational accepted-outcome cost, and partially calibrated, strictly domain-scoped historical and AI-task models. It does not automatically interpret requirements, verify a programme, estimate unknown future costs, derive probabilities from prose, or prove that an acceptance suite covers the right specification.

The repository owner has not yet chosen a project licence.
