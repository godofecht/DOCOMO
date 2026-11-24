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

## Scope

Phase 0 implements decision-theoretic grounding, observational accepted-outcome cost, and partially calibrated, strictly domain-scoped historical and AI-task models. It does not automatically interpret requirements, verify a programme, estimate unknown future costs, derive probabilities from prose, or prove that an acceptance suite covers the right specification.

The repository owner has not yet chosen a project licence.
