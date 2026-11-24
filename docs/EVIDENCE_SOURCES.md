# External empirical evidence eligibility register (20 November 2026)

This register prevents using mismatched public datasets to assert a general, calibrated AI-era COCOMO successor. Each research dataset has distinct estimands, scope, inclusion criteria, and independent verification conditions.

## A. Historical COCOMO-I project costs — **eligible for historical effort calibration only**

Source: Derek Jones, [COCOMO-81.csv](https://github.com/Derek-Jones/Software-estimation-datasets/blob/e3fbd4faa2a5aec94b06535369664c3ebbcbac39/COCOMO-81.csv).
63 projects with effort multipliers, KSLOC and actual person-months. Already integrated in DOCOMO with pinned git blob integrity verification. No agentic AI, COCOMO II scale factors, modern model versions, verification evidence, or machine expenditure. Strict domain: historical COCOMO-I effort.

## B. Early-2025 METR developer productivity — **eligible for randomized task-time effects only**

Source: [study](https://arxiv.org/abs/2507.09089) and [public tasks](https://github.com/METR/Measuring-Early-2025-AI-on-Exp-OSS-Devs/blob/7ff2d7670235f531dff77eff58355bd77392f396/data_complete.csv). 246 tasks from 16 experienced developers, randomized AI access, pre-randomization unaided-time expectations and actual implementation times. Already integrated. Reproduced conditional estimate exp(beta_AI)-1 = +0.1884 (slower under AI access in this specific experiment). This does not measure accepted whole-project person-months, inference charges or independent release assurance. Do not transplant to project costs.

The [late-2025/2026 follow-up](https://github.com/METR/Measuring-Late-2025-AI-on-OSS-Devs/blob/55f007216a26493f0a9b7650ab3191cad7fb9e7f/data.csv) offers additional randomized tasks but has investigator-described participation selection effects. Only an appropriately labelled sensitivity study, not an unconditional modern coefficient.

## C. Industrial user-story effort and AI *estimates* — **candidate for estimator benchmarking; ineligible as AI-generated-effort treatment**

Source: [Mendeley Data, January 2026, DOI 10.17632/ytmwsf2997.2](https://data.mendeley.com/datasets/ytmwsf2997/2), “Software Projects User Stories Estimates with PRED & MMRE.” Description reports >100 actual logged-effort user stories from 10 industrial web/mobile projects, plus independent expert, Planning Poker and ChatGPT/DeepSeek/Copilot/Gemini *effort predictions*. Licence CC BY 4.0. Data describe actual effort and retrospective **AI cost estimates**, not controlled AI-assisted construction. Potential use: held-out project-level test of cost *estimation* as a function of requirements, after obtaining and verifying original data and feature timing. Not evidence that AI speeds construction. Before adoption, verify file availability, collection protocol, study chronology, units and project-family leakage.

## D. Measured AI-assisted project economic case study — **eligible for descriptive external case study, not population calibration**

Source: [Neves, Garcia and Gama, CBSoft 2026 replication package](https://zenodo.org/records/21843234), DOI 10.5281/zenodo.21843234. Published 7 August 2026, the reported downloadable replication package contains `data/development-log.csv` with per-activity human hours, tokens, AI costs, counterfactual estimates and billing screenshots, plus prompt and pay reference records. This may supply a grounded case study for the machine-vs-human accounting decomposition after verifying original records. It is **not** a representative many-project calibration set; counterfactual estimates are not observed control-group effort; billing screenshots alone do not independently certify software behaviour.

The ZIP was not mirrored by DOCOMO because its content was not inspected/verified in this evaluation.

## E. Open time tracking across sectors — **eligible for learning project/failure accounting patterns, not AI-specific software calibration**

Source: [Abitbol and Arod (2025), Gryzzly](https://pmc.ncbi.nlm.nih.gov/articles/PMC11972307/), Scientific Data, 4.4 million activity declarations across 173,323 tasks and 50,759 projects, 2017–2024, covering multiple industries. Includes collaboration, planned vs actual costs and failure dynamics; not necessarily all software projects, predates the contemporary agentic-AI workflow, no verified model usage. Useful as external input to accounting schemas and failure/censoring methodology, not as COCOMO replacement ground truth.

## F. AI agent coding/PR traces — **eligible for workflow/quality proxies, not verified person-hours**

Examples: [AIDev](https://arxiv.org/abs/2602.09185), [GitHub Agentic PR Dataset](https://github.com/mabujadallah/GitHub-Agentic-PR-Dataset), [AgentLogs](https://arxiv.org/abs/2608.29204). The projects provide PR metadata, commit/diff histories, agent lifecycle and in some cases system logs. Merge latency, commit timestamps, approval status, number of tokens and changed lines are not equivalent to independently audited engineer working minutes or a passed external acceptance suite. Can inform workload-distribution and quality-proxy studies, but should never be silently translated into true accepted-delivery cost.

## G. Observed human–LLM task process effort — **eligible for exploratory AI-task benchmark only**

Source: [Alaswad et al., Discover Computing (2026)](https://doi.org/10.1007/s10791-026-10331-6) and [pinned 330-row task-execution CSV](https://github.com/FeisalAlaswad/Hie_effort_estimation/blob/09e105d5a7fb3f15e5412d688dbf79d21c42329b/Task_execution_observations.csv). Contains observed task minutes, 22 developers and three LLM assignments, Story Points and logged corrective/validation/integration indicators. The study calls its analysis explanatory and exploratory, not a validated forward cost forecast.

DOCOMO evaluates grouped held-out-developer error of pre-execution Story Points and assigned-model features separately from **post-execution** interaction diagnostics. Using the latter for a planning-time forecast would leak information unavailable at decision time. The CSV omits task/repository identifiers and therefore cannot establish independence of project or task families across folds. It has no unaided control, independently audited release or machine cost. Do not infer global productivity or project accepted-outcome cost. See [docs/HIE.md](HIE.md).

## Source inclusion and transportability criteria

Record for each dataset: original source, exact pinned release/checksum, collection dates, actual sample/population, unit of analysis, sampling and exclusions, intervention (if any), measured outcomes vs estimates or proxies, independent acceptance provenance, cost/currency unit, missing-data mechanism, known caveats, and permitted estimands.

No merged training table may contain mixed unconverted units (minutes/person-months/currency), non-matched acceptance criteria or control treatments from materially different populations. Training/test splits must be grouped by repository/project and frozen before evaluating final model accuracy. Publication date is not the same as era of model tools or actual development.

Only after enough **real AI-native accepted project outcomes** are collected under the schema in docs/NATIVE.md, plus independent acceptance auditing and prospective validation, is the claim “calibrated DOCOMO successor for domain X” justified. Sources C–F are leads, not automatically certified inputs. The current code correctly declines production AI-native calibration on synthetic fixtures or insufficient data.
