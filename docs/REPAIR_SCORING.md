# Independent evaluation outcomes for real repository repairs

DOCOMO now admits 500 human-validated SWE-bench Verified issue cases from a pinned, verified Parquet source. This separate operation can ingest the actual **official SWE-bench evaluation report** from an agent rollout and test its completeness before reporting anything about performance.

The integration follows the data structures of the official `swebench/harness/reporting.py`, pinned as reference at [this source revision](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/swebench/harness/reporting.py). The upstream tool writes `results.json` with `schema_version: 2`, `resolved_ids`, `unresolved_ids`, `error_ids`, `empty_patch_ids`, `incomplete_ids`, `submitted_ids`, `completed_ids`, as well as infrastructure and ambiguous failure annotations.

## How to run

Create the verified case metadata inventory first:

```sh
pip install -e '.[repair]'
docomo-repairs --index-output verified-repair-index.json
```

Run the **actual official SWE-bench harness** independently to obtain a genuine `results.json` and original Docker/evaluation logs. Then:

```sh
docomo-score-repairs \
  --inventory verified-repair-index.json \
  --official-results /path/to/official/results.json \
  --run-id original-swebench-run-id \
  --agent-model-id actual-agent-model-version \
  --harness-commit <40-character-harness-git-sha> \
  --output scored-repair-run.json
```

The harness commit and agent ID must be provided by the experiment operator; DOCOMO does not invent them. If no official run has taken place, there is no valid performance report to import. Unit tests use explicitly synthetic 500-case fixtures and make no scientific performance claim.

## Denominator and missingness rules

Exactly the frozen source population of 500 case IDs must be accounted for, even if an agent did not submit a patch or an evaluation errored. Every source case must belong to precisely one status: resolved, unresolved, error, empty patch or incomplete. The corresponding counts must agree with their case-ID arrays.

Unsubmitted instances are exactly the frozen IDs absent from the official `submitted_ids` array. Completed cases must be submitted, and resolved/unresolved cases must have completed results. Infrastructure failures may be annotated on unresolved/error cases, but they **remain failures in the denominator**.

The output reports the conservative fraction of all 500 frozen problems that the supplied results claim were resolved, a Wilson binomial interval, and repository-specific breakdowns. The Wilson interval assumes independent binary observations and should not be treated as an independent-case guarantee for related repository issues. No selective filtering by solved cases, task difficulty, infrastructure conditions, or unsubmitted patches is allowed in the headline denominator.

## Trust and contamination boundary

This module verifies consistency of a **user-supplied report**, not the origin or truth of its individual success labels. A malicious user can submit a forged `results.json` consistent with the schema. The status is deliberately `official_report_format_and_case_accounting_validated_run_logs_unverified` and `evaluation_artifacts_independently_verified: false`.

An independent evaluator must inspect the original official evaluator files, reconstruct the test results from the fixed dataset, confirm the corresponding container images and harness version, and validate that the agent was not given the gold patch, gold tests or future repository history. Until then it is inaccurate to state that DOCOMO verified an agent's success rate.

A reproducible test can preserve original files and record their SHA-256. The CLI records the checksum of the imported official JSON report itself, but this does not authenticate the source of the report or logs.

## DOCOMO's evolutionary significance

These 500 cases enable a separate, falsifiable **functional repair** evaluation stream. Proposed specification-grounding, semantic-dependency or verification-complexity models can be challenged against issues that actually have source-controlled reference patches and evaluator oracles. Corrections to benchmark acceptance criteria become versioned challenges, not silently edited observations.

But the 500 issue cases contain **no audited human developer time or inference expenditure**, and a successful code patch is not an entire completed project. Therefore a repair-success percentage cannot be converted into person-month estimates without direct measurement under DOCOMO's project ledgers and prospective study protocols.

The full model amendment process remains in [AMENDMENT_GOVERNANCE.md](AMENDMENT_GOVERNANCE.md). A release intended to forecast accepted project costs requires independent contemporary project-level holdouts and evidence of planning-time predictor availability. Positive repository-repair results are supporting evidence about accepted behaviour, not a replacement for cost validation.
