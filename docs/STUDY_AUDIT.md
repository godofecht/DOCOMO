# Study-wide cost-evidence integrity

The accepted-project effort model and binary acceptance model require complete observed measurements. Before fitting either, `docomo study-audit` checks that an entire train/calibration/test cohort has **one matching activity ledger per project** and that the same work session has not been charged to multiple projects.

## Bundle

Input is a JSON object containing `schema_version: "1.0"`, an `experiment` using the same three-way project manifest structure as `docomo holdout`, and a `ledgers` array containing full per-project source accounting as defined in `docs/LEDGER.md`. An optional `expected_protocol_sha256` declares a previously computed fingerprint; if present, an exact mismatch is fatal.

Each project must have a unique project ID. A repository cannot occur in more than one of train, calibration and test. All projects must refer to the same declared domain and accounting currency. The tool checks the claimed preregistration timestamp against planning times, rejects fabricated test-scope timing, and validates each ledger.

Every ledged project must match its normalised manifest exactly, including acceptance result, seven mutually exclusive human time categories, machine charges and failure accounting. There can be no unaccounted project, duplicate project ledger or unexplained extra ledger. All event IDs are unique across the entire study. The tool rejects overlapping recorded work sessions for the same contributor **across projects**, in addition to the per-project checks performed by `docomo ledger`. Different contributors may legitimately work at the same time.

## Protocol fingerprint

The SHA256 `protocol_sha256` is computed from canonical JSON containing the declared model, nominal coverage, registration URL/time and per-project **planning** fields and acceptance-oracle commit. Each planned project is ordered by its unique ID; acceptance outcomes, execution time, labour and cost data are deliberately excluded. Consequently, editing any observed outcome does not silently change the purported planning protocol, while editing a scope feature should change the fingerprint.

An optional `expected_protocol_sha256` can detect a mismatch against a separately stored hash. However, passing this check does **not** demonstrate that the hash was published before the evaluation, and does not prove that test-project selection was decided without knowledge of outcomes. An actual preregistration requires an externally timestamped immutable record and independent verification of its publication chronology. The current data format enumerates realised projects and is not yet a complete prospective *selection-rule* protocol; future revisions should freeze repository/time cohort selection rules before any test outcomes are observed.

## External trust boundary

An HTTPS evidence URL is not the content it references, a declared reviewer is not an authenticated person, a recorded start/end time is not proof of productive labour, and a hash of a user-supplied JSON object does not make that object true. DOCOMO consequently returns `cost_ledgers_and_planning_reconciled_not_authenticated`; its external audit flags remain false.

The code rejects `synthetic: true` input from the default CLI. The tracked `examples/study-bundle.json` is intentionally synthetic, and is used only by explicit opt-in unit tests.

## Run

```sh
docomo study-audit your-locked-study-bundle.json
```

After independent external validation and an untouched future cohort become available, the same experiment can be evaluated using `docomo holdout`. This preflight does not itself calibrate any coefficients and must not be represented as evidence of an AI productivity improvement or a certified COCOMO successor.
