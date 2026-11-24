# Primary supporting-document integrity checks

A GitHub protocol attestation establishes a server timestamp and exact pre-outcome protocol bytes. It does not authenticate invoices, time tracking, review or acceptance evidence. The `docomo-source-audit` command adds a separate **local file integrity** step for such documents.

## Format and expected sources

An evidence index is a versioned JSON object containing the complete `ledger` used by `docomo ledger` and an `artifacts` array. The index needs one entry for each original human time event, machine expenditure, project-review record, and acceptance result. Each entry contains `event_id`, `relative_path`, `sha256` and `source_url`. Event IDs use namespaced forms `human:<event-id>` and `machine:<charge-id>`; the reviewer and acceptance entries are exactly `review` and `acceptance`.

Each local file is read and SHA-256 hashed. The hash must match the entry's declared digest; the claimed URL must equal the source URL already recorded in the accounting ledger. The auditor rejects missing or extra supporting documents, duplicated index identifiers, empty or oversized files, mismatched currencies/ledger totals and SHA-256 mismatches. Path traversal and symlinks escaping the source root are rejected. The file size limit is 25 MB per source (larger originals require a separately designed streaming/storage protocol).

A separate group reports if the *same source bytes* have been used for multiple accounting claims. This is not automatically fraud: a single invoice can legitimately contain several billing line items, and one signed timesheet can support multiple work intervals. It is a signal for independent manual inspection, not an ungrounded correctness verdict.

## Run

```sh
pip install -e .
docomo-source-audit --source-root /path/to/original-evidence /path/to/evidence-index.json
```

The source root must exist locally; the index can refer only to relative paths inside it, not arbitrary network URLs. The CLI does **not** download a URL specified by the dataset author. This prevents silent substitution by current website content and avoids giving user-controlled links unrestricted network access.

For example, to substantiate an engineer's ten-minute verification session, supply a stable timestamped source record from the actual time tracker, calculate SHA-256 over the downloaded original bytes, and link its artifact to that session's exact `human:<event-id>` entry. An independent reviewer should separately verify that the original came from the claimed provider and matches provider records at the appropriate collection time.

## Provenance boundary

The output `source_file_bytes_matched_origin_not_authenticated` means only that bytes supplied on the local file system match the input index and accounting IDs. **The index itself is user-supplied.** An attacker can forge a document and its matching hash; a matching checksum does not authenticate its authorship, times, claimed URL, signature, publisher or reviewer identity.

The module also cannot establish that an omitted project was ever present, that work was genuinely productive, or that an asserted acceptance report corresponds to an independently correct system. Source completeness against the real project population, digitally signed originals, provider API attestation and independent audit are separate tasks.

The unit tests construct **synthetic evidence files in temporary directories** and never treat them as empirical observations. Production refuses a ledger explicitly labelled synthetic. No source documents or scanned PDFs have been fabricated and presented as real research evidence.

## Why this matters for calibration

The accepted-outcome effort estimator requires measured **human engineering time**, while the economic model separately requires metered machine expenditure and independently assessed acceptance outcomes. GitHub commit timestamps, LLM token counts and an invented API cost rate do not satisfy these labels.

This step makes incoming cost records reproducible and checksum-verifiable. To achieve a genuinely calibrated DOCOMO successor, combine it with GitHub timestamped preregistration, cohort selection from an externally audited project-intake registry, prospective held-out outcome evaluation, and independent provider authentication.
