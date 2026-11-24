# GitHub Actions registration attestation

DOCOMO can verify that a specific protocol JSON file was present at a specific immutable Git commit associated with a GitHub Actions workflow run. The action run's creation timestamp comes from the GitHub API, rather than the Git commit author's or committer's freely editable timestamp.

This is a **server-side chronology check**, not a complete independent research validation.

## Register a protocol

Create a cohort definition with `docomo protocol-freeze`, ensuring the declared registration cutoff occurs after the protocol is published and before future test enrollment begins. Commit the same JSON in a GitHub repository with a workflow that executes on a **push**, and let that workflow finish successfully. Keep the immutable commit SHA and its GitHub Actions run ID.

Supply the following JSON to `docomo github-attest <file.json>`:

```json
{
  "schema_version": "1.0",
  "repository": "research-owner/protocol-registry",
  "workflow_run_id": 123456,
  "head_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "protocol_path": "studies/project-cost-protocol.json",
  "expected_protocol_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "protocol": {
    "...": "the complete protocol passed to docomo protocol-freeze"
  }
}
```

The IDs and hashes above are placeholders, not valid attestation evidence. The protocol field must contain the complete object matching the committed file.

`docomo github-attest` calls the documented [GitHub REST workflow-run endpoint](https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run) and [GitHub contents endpoint](https://docs.github.com/en/rest/repos/contents#get-repository-content) using `ref` fixed to the expected commit SHA. It validates the run ID, current public repository, matching workflow commit, successful completed **push** run, GitHub-reported `created_at` no later than the protocol's registered cutoff and test enrollment start, then verifies the retrieved file's size, Git blob checksum, decoded UTF-8 JSON, canonical protocol content and declared SHA-256 fingerprint.

The program refuses late runs, wrong repository, arbitrary branch refs, mismatched commits, invalid or modified content, backdated-only commit claims, malformed file paths and JSON with duplicate object keys. It uses the standard library and only constructs requests to `api.github.com`; the caller cannot specify arbitrary HTTP hosts in this operation.

## Why the event timestamp matters

A Git author date such as 1990 can be written in 2026, so its chronology is not useful as independent proof of pre-registration. A GitHub Actions run's `created_at` value is reported by GitHub's service. When a successful push run identifies the exact immutable commit, that commit necessarily contained the checked protocol at the time it was run, subject to GitHub's API integrity and administrative trust boundary.

This does not prove the repository was publicly accessible at the time of the run: a private repository could have been made public later. Nor does it prove the project inventory was complete, developer start times were independently recorded, the work was done according to the registered process, or an acceptance oracle was genuinely independent. Those require other verified primary sources.

The output therefore uses `github_server_timestamp_and_pinned_content_verified` while leaving all project-population, timer/invoice and acceptance verification flags **false**. A protocol still requires `protocol-population`, `study-audit` and `holdout` on independently collected evidence before conclusions can be drawn.

## Availability and CI

The GitHub REST API may apply unauthenticated rate limits and permissions. A private repository or unavailable workflow run is deliberately refused as unverified; it does not fall back to using easily spoofed commit dates.

Unit tests provide deterministic emulations of the API response and malicious mismatches so CI remains independent of network availability and rate limits. A valid real-world attestation is not manufactured by these tests. For real research, an independent auditor should rerun the API lookups and archive the signed/retrieved response evidence.

## Remaining prerequisites

Use a timestamped external project-intake registry to show that all eligible test projects, including failed and abandoned attempts, entered the inventory at the appropriate time. Audit raw human time and invoices, authenticate external acceptance results, and demonstrate held-out predictive accuracy and interval coverage. DOCOMO cannot claim full calibration merely because the protocol was registered on GitHub.
