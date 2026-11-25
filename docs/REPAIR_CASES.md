# Human-validated repository repair cases

DOCOMO keeps repository issue resolution separate from software project effort. SWE-bench Verified contains 500 human-validated real Python-repository issue/PR tasks. Each issue is tied to a fixed pre-solution Git commit and a reference patch/test suite. The human validation is primarily about task clarity and test fairness, **not** a measurement of total person-hours or externally verified whole-project delivery.

## Source pin

`SWE-bench/SWE-bench_Verified` is pinned to Hugging Face Git revision `78f471bf655a3137b2e8a75af1501690ec009ec3` and `data/test-00000-of-00001.parquet` with SHA-256 `030cfd7f2a704c4c0226e7f104c725a3b41230b1d3517f9c915ad7ea5be3fa25`.

The reader refuses a locally cached or newly downloaded file if the original bytes do not match. It checks the presence of issue descriptions, unique issue identifiers, repositories, full pre-fix Git SHA, reference patches, and gold test patches before treating the input as 500 reference cases. The source data are not silently updated just because the benchmark's `main` branch moves.

This source is hosted as a 6.3 MB Parquet snapshot. Install `pyarrow` using the optional extra; no extra dependency is imposed on the historical COCOMO/effort calibration code:

```sh
pip install -e '.[repair]'
docomo-repairs --index-output verified-repair-index.json
```

The generated index gives the 500 issue IDs, original repository paths, fixed base commits and SHA-256 of issue text, gold source patches and gold tests. It does not contain raw gold patch, gold tests or full task prompts. GitHub Actions publishes this **metadata-only** source inventory as a reproducibility artifact.

## Separating agent and evaluator access

DOCOMO can optionally produce a local agent input file:

```sh
docomo-repairs --agent-prompts-output local-repair-prompts.jsonl --index-output local-repair-metadata.json
```

Each agent-facing JSONL record contains only `instance_id`, `repo`, `base_commit`, `problem_statement`, the official evaluation-protocol label and explicit flags that the gold patch and test oracle were withheld.

The evaluator's original Parquet file must remain inaccessible to the candidate agent. Do **not** include it, its gold patches, `test_patch`, `FAIL_TO_PASS` or `PASS_TO_PASS` in the agent context. Since the actual tasks are public historical PRs, an agent with internet or unrestricted repository history can retrieve a future answer even if its JSON prompt is clean. A proper benchmark rollout must therefore use an isolated checkout at `base_commit` and enforce the official SWE-bench contamination and network rules. This adapter is not a sandbox.

Official SWE-bench images and tests are authoritative for functional repair pass/fail. DOCOMO does **not** claim to have replayed those Docker evaluations itself, and no agent success percentage is reported by simply importing reference cases. Store separately the evaluator version, agent/model version, each run's pass/fail outcome, oracle integrity and source logs before extending the evidence registry to agent performance measurements.

## What this lets DOCOMO evaluate

The original benchmark issue cases can probe semantic grounding and whether implementation outcomes are independently checked against a defined task, including cases with multiple plausible fixes and test fairness concerns. They can also test the falsifiable hypothesis that a DOCOMO specification-ambiguity score or verification burden predicts difficulty of accepted repair.

They cannot identify a completed *project's* financial cost, total human developer time, inference charges, assurance work, or accepted system delivery. Those require directly observed individual human and machine cost records and independent acceptance. Never infer these missing labels from patch size, GitHub commit timestamps, or benchmark difficulty estimates.

A correction to a benchmark task, evaluator, Docker image or gold test should trigger a new versioned provenance record and a reconsideration of earlier agent scores. Previous scores must remain attributable to their frozen benchmark version rather than silently rewritten.

## Relationship with the real cost corpora

The four historical cost datasets contain **736 completed-project observations**, potentially overlapping, in person-month and person-hour units. SWE-bench Verified adds **500 human-validated issue-level cases**. These numbers are separate and must not be summed into a single "1,236 projects" count. METR and HIE also contribute independent AI-time observations at the task level but do not identify those project-level costs.

The evidence registry records both dimensions and explicitly identifies which claims each dataset can or cannot test. A future DOCOMO version should join accepted work to actual timed development records only through original, audited task/project identifiers with clear allocation policies and complete failure accounting.
