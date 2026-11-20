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

## AI-native calibration research engine

The `native-calibrate` mode implements a prospective, strictly gated project-level human-effort regression and compares repository-group-held-out predictive errors against a size-only model and a nominal-assumptions COCOMO II reference. It requires 50+ project records, 8+ repositories, independent acceptance links and detailed non-overlapping human time accounting. Synthetic fixtures are explicitly rejected in the default production mode. **No qualified AI-native data corpus is bundled or claimed, and group CV is not an independent prospective certification.** See [docs/NATIVE.md](docs/NATIVE.md).

## Scope

Phase 0 implements decision-theoretic grounding, observational accepted-outcome cost, and partially calibrated, strictly domain-scoped historical and AI-task models. It does not automatically interpret requirements, verify a programme, estimate unknown future costs, derive probabilities from prose, or prove that an acceptance suite covers the right specification.

The repository owner has not yet chosen a project licence.
