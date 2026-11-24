# Measured effort ledger and independent audit workflow

DOCOMO's historical datasets do not include the contemporary AI-native project accounting required for a credible successor to COCOMO II. The `ledger` mode introduces an explicit, per-project measurement source suitable for eventual independent audit.

The ledger is a JSON object with `schema_version: "1.0"`, a complete `manifest` (see `examples/project-manifest.json`), `human_events`, `machine_charges`, and `review`. The example in `examples/effort-ledger.json` is **synthetic**, not an empirical project observation.

## Human observations

Each time event has a unique ID, contributor ID, one of the seven mutually exclusive engineering stages, timezone-qualified start/end timestamps, an evidence URL and a declared source type. The supported source types are `timer`, `signed_timesheet`, and `instrumented_work_session`. The implementation calculates elapsed minutes from timestamps, rejects negative or zero sessions, rejects a single work session exceeding 16 hours, and rejects simultaneous entries for the same contributor. Different contributors can work simultaneously, and their working minutes correctly add even when calendar time overlaps.

All recorded human minutes must reconcile with the stage totals in the versioned project manifest within a small numeric tolerance. No missing stage or unaccounted minutes are silently imputed. This is an auditable **consistency** requirement, not a claim that source events are truthful or complete.

## Machine billing

Every machine expenditure has a unique event ID, an explicit nonnegative amount, currency, evidence URL, and meter such as API inference or compute resources. Event currencies must match the manifest currency and their sum must match the declared total machine cost. Exchange rates, refunds and vendor tax accounting are not invented; those require separate explicit transaction-level evidence and accounting policy.

Human time is never converted to machine charges, and machine charges are never counted as person-months.

## External review limitations

A review record identifies the reviewer, UTC review time, evidence URL, and an explicit assertion that the reviewer was not the author. The validator rejects a reviewer who is also named as a contributor in recorded time and a review time earlier than the most recent work session.

It **does not** authenticate external evidence URLs, timestamps, invoices, reviewer identity, signature or the independence of acceptance tests. Its status is necessarily `reconciled_not_independently_verified`. An independent auditor must verify original timer records, invoice totals, acceptance oracles and evidence provenance before these observations are used for high-stakes calibration claims. Matching a manifest cannot prove that failed attempts, abandoned work or unrecorded labor were included. A claim that all failed attempts are included must be independently checked against source records.

## Run

```sh
docomo ledger examples/effort-ledger.json
python -m unittest discover -s tests -v
```

Future additions should support imported signed timesheet and invoice formats, source content hashes, multi-currency conversions backed by documented rates, per-trial provenance and accounting for abandoned projects. Collection should begin before project work starts, with preregistered definitions for stages, acceptance and failure, and independent reviewers, rather than relying on retrospective developer estimates.

This ledger helps acquire real empirical labels. It does **not** itself fit or certify an AI-native effort model.
