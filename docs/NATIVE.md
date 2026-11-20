# AI-native project calibration: experimental specification

DOCOMO's native-calibrate is a research calibrator, not proof that the required real project observations have been collected.

## Target and outcome

Current outcome: human working minutes conditional on eventual independently asserted project acceptance, including failed attempts within each successful project's ledger. It does not estimate the expected expenditure on abandoned projects. Machine charges are kept separate and summarised descriptively; acceptance probability and elapsed calendar time are not yet predicted.

Human time must be recorded in exactly seven mutually exclusive categories: specification, implementation, verification, integration, orchestration, rework, assurance. Do not infer measured time from commit timestamps or model tokens.

## Provenance and screening

Each record follows examples/project-manifest.json with fixed repository and requirements commit, independent acceptance evidence link and reviewer declaration, model/tool version, prospective scope and complexity features, and complete human and machine accounting. All projects in one fit must occupy the same declared domain and currency.

The structural screen requires at least 50 project outcomes, 8 distinct repositories, 30 accepted deliveries, both human-only and AI workflows, and sufficient accepted repositories for grouped validation. These are screening heuristics, not validated sample-size calculations.

Synthetic records are rejected by default; unit tests explicitly opt in and their status is synthetic_algorithm_test_only. Zero-human-effort accepted deliveries require a separate hurdle model and fail closed rather than being silently dropped or log-transformed.

## Candidate models

The primary candidate uses log human minutes as a linear function of log functional units, log1p dependency edges, log1p verification obligations, log1p ambiguous requirements, and indicators for AI-assisted versus agent-delegated workflows.

A size-only regression is compared when every record contains positive equivalent KSLOC. A fixed reference COCOMO II.2000 Post-Architecture estimate with all factors nominal is also compared, converted at 152 working hours per person-month. This last comparison is NOT fully rated COCOMO II; that would require verified factor ratings per project.

The model is evaluated with repository-grouped out-of-fold predictions. Report log-RMSE, MAE, MdAE, median relative error and PRED25, plus coefficients fitted to all accepted observations. Model selection based on the same CV folds remains exploratory and must be confirmed with separate prospective holdout data.

## Important limitations and further work

Acceptance links and reviewer independence remain self-attested until independently audited. The current model conditions on eventual acceptance, so excluded failures/abandonment create selection bias. Observational workflow indicators cannot establish causal AI gains. A more complete successor requires censored/failure outcomes, zero-inflated human effort, model-version drift, confidence-calibrated intervals, project-level machine costs and calendar schedule, and preregistered independent future-project evaluation.

Run:

    docomo native-calibrate examples/project-manifest-list.json

The sample correctly returns insufficient_project_evidence. Real independent data, not the synthetic test suite, are necessary for eventual AI-native calibration certification.
