# Import real industrial effort estimates from Mendeley Data v2

The [Software Projects User Stories Estimates with PRED & MMRE](https://data.mendeley.com/datasets/ytmwsf2997/2) dataset, published 21 January 2026 by Subhan Anjum and Ali Afzal Malik (DOI **10.17632/ytmwsf2997.2**, CC BY 4.0), describes **ten completed industrial projects and more than 100 user stories**. Each story has an observed effort measure in person-hours, expert judgment and Planning Poker estimates, and four existing AI-generated *estimates* from ChatGPT, DeepSeek, Microsoft Copilot and Gemini.

AI tools in this study supplied **estimates**, not measured hours of AI-assisted implementation. The source does not establish an AI development-speed advantage.

## Source retrieval status

DOCOMO currently verifies the published dataset metadata but **has not yet retrieved the original v2 workbook bytes**. The official provider API was tested from networked GitHub Actions on **26 November 2026**: the three documented public dataset metadata endpoints returned **HTTP 401 Unauthorized**, even though the public dataset landing page remains readable. This was independently recorded in [the discovery workflow artifact](https://github.com/godofecht/DOCOMO/actions/runs/45835180626/artifacts/15125720290), not inferred from a missing file. An explicitly triggered [Mendeley source discovery workflow](../.github/workflows/mendeley-v2-source.yml) can retry with an optional `MENDELEY_ACCESS_TOKEN` repository secret, without making authenticated metadata a routine CI dependency. A successful metadata request still does not constitute original workbook retrieval. Neither the exact v2 SHA-256 nor the workbook worksheet names/header strings are guessed. The [evidence registry](../catalog/evidence_registry.json) therefore remains `identified_source_not_ingested`. CI tests only **synthetic workbook fixtures** created in memory. No fabricated row, invented checksum or bogus cross-validation score is reported as empirical.

Obtaining the original v2 workbook is a prerequisite for legitimate numerical model comparison. Retain it outside Git (respecting licence and attribution), and record the exact DOI, version, publication date, original file checksum and file provenance in your own experiment record. Do not substitute version 1 (its public listing has a different workbook size) or a repackaged copy without an explicit new provenance identity.

## Inspect first, then register the schema

```sh
python -m pip install -e .
docomo-industrial inspect path/to/original-v2.xlsx
docomo-industrial inspect path/to/original-v2.xlsx --sheet "EXACT SOURCE SHEET NAME"
```

Inspect prints the file SHA-256, visible and hidden worksheet names, and the first ten rows of the selected sheet. Formulas are flagged; they are not evaluated. Review the original worksheet and choose the exact columns using the template `catalog/mendeley_v2_mapping.template.json`.

The template deliberately contains **invalid placeholders**. Replace them with the source's exact SHA-256, visible worksheet name, header row and the exact nine distinct column headings: project ID, story ID, actual person-hours, expert estimate, Planning Poker, ChatGPT, DeepSeek, Copilot and Gemini. The official dataset must supply these fields or this version of the adapter refuses admission rather than manufacturing them.

```sh
docomo-industrial score path/to/original-v2.xlsx \
  --mapping path/to/filled-and-checked-v2-mapping.json \
  --records-output industrial-normalized-records.json \
  --output industrial-evaluation.json
```

No original data are rewritten. The normalized export retains every original (project ID, story ID) pair and Excel row number, with actual person-hours and each original estimate separately recorded.

## Adversarial intake requirements

The importer requires exact original file SHA-256 and DOI version 2, a visible worksheet, explicit header mapping, no duplicate headers, ten distinct project IDs, over 100 complete stories, unique story IDs within each project, strictly positive finite numeric actual and estimated person-hours, and no formula-derived input cells. It does not impute missing estimates, silently drop difficult stories, infer unknown units or interpret a rendered blank cache as an acceptable measured outcome.

The OOXML reader accepts normal literal shared-string and inline-string worksheet cells and rejects external links, executable workbook components, malformed cell coordinates, unsafe archive paths and unreasonably large ZIP expansion. It never executes Excel formulas, macros or external references. Hidden sheet names are disclosed and cannot be selected for scored input.

These checks establish **internal consistency and checksum integrity**, not that the original measured hours are authentic. An independent source-data audit must establish whether recorded effort came from genuine project logs and whether the estimators were generated before or after actual effort was known.

## Evaluation with complete project clustering

Each pre-existing estimate is a fixed prediction; DOCOMO does **not** refit or retrain those estimator models on this source. Results report pooled story-level MAE, median relative error, log-RMSE and PRED25, plus the actual and predicted total effort, signed and absolute total error for each of the ten individual projects.

To avoid hiding failures in large projects, the comparison also reports an **equal-project-weighted** average MAE, log-RMSE and absolute project total error. It computes a paired project-cluster bootstrap on the MAE differences between each challenger and the original expert-judgment baseline. Only entire project groups are resampled; individual stories from one project are never counted as statistically independent units.

The bootstrap default is 1000 project-group replicates with a frozen seed. Ten projects are a small sample, so the interval is descriptive, not a proof of future superiority. All negative differences and null intervals remain in the report. No model is automatically promoted, regardless of the score. Project-level grouping is mandatory for any future fitting, calibration or holdout; the current score of original fixed estimates is not a true prospective unseen-project test.

## Connection to DOCOMO's evolution

If these actual estimates are verified, the comparison will show where expert judgment, group consensus and each existing language model systematically overestimate or underestimate **historical user-story effort**, possibly by project class and scope.

The resulting falsifiable amendments may propose new grounded scope descriptors, dependency features, specification ambiguity or uncertainty calibration. Those amendments must then be tested on a **different, prospectively acquired** set of projects. They cannot be certified by selecting a winning equation on the same ten projects.

The complete model-change process is specified in [AMENDMENT_GOVERNANCE.md](AMENDMENT_GOVERNANCE.md). The missing source-data task remains [issue #24](https://github.com/godofecht/DOCOMO/issues/24); full project accepted-delivery cost remains [issue #9](https://github.com/godofecht/DOCOMO/issues/9).

A story-level original cost label does not include verified functional acceptance, inference expenditure, failures, safety-review effort or separately metered integration work. The adapter deliberately keeps these missing variables absent instead of synthesizing a nonexistent AI-native cost dataset.
