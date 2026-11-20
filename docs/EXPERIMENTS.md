# DOCOMO: falsification-oriented evaluation protocol

## Hypotheses

H1: A decision-theoretic grounding policy lowers downstream specification rework compared with equal-budget unstructured clarification.

H2: A model of accepted-outcome cost, verification, coupling, and model/tool configuration predicts held-out effort better than raw source size or a single AI productivity multiplier.

H3: Improving code generation speed does not necessarily reduce verified-delivery cost or wall-clock time proportionally.

All hypotheses may fail. DOCOMO is useful only if empirical evidence supports its predictive or decision quality.

## Task sampling

Build a preregistered collection covering algorithms with formal contracts, low-level concurrency, numerical/DSP components with real-time bounds, API compatibility, legacy code integration, greenfield services, and ambiguous product requirements. Include four combinations: high/low generation difficulty crossed with high/low grounding debt.

Freeze task scope, environment, codebase commit, input distributions, performance and safety constraints, and acceptance protocol before assigning treatments. Document the provenance of each task and who owns its acceptance criteria.

## Conditions and measurements

Randomise comparable task instances and developers between human-only, AI-assisted, and autonomous-agent conditions. Rotate task order to control for learning and familiarity. Track model and tool versions, hardware, context restrictions, inference settings, security controls, and whether agents previously saw test fixtures.

For every attempt, measure human minutes, machine expenditure, elapsed time, independent acceptance result, defect severity, review effort, integration effort, rework, and clarification cost. Never select only successful trials for publication. Independent evaluators should maintain held-out acceptance criteria that the agents cannot modify.

## Grounding evaluation

Have independent experts enumerate plausible requirement interpretations, candidate actions, corresponding losses, and proposed evidence. Document how probabilities were elicited and whether they reflect existing stakeholder intent or contested normative choices. Compare clarification chosen by DOCOMO against a preregistered control using an equal evidence budget. Track whether clarifications actually separate alternatives and reduce wrong decisions.

Analyse sensitivity to prior uncertainty, altered losses, missing interpretations, inaccurate observation likelihoods and incompatible stakeholder goals. Normative disagreements must not be resolved merely by averaging numerical preferences.

## Prediction and inference

Split data by repository, task family or time cohort, not by near-duplicate code examples. Compare errors in accepted-outcome monetary cost, completion time, prediction interval coverage, and confidence calibration. Account for repeated measures and dependence between developers and tasks. Report all failures, exclusions, null findings and credible sensitivity bounds.

A successful DOCOMO result requires better prospective decision outcomes or predictive performance than documented baselines. If uncertainty is too high, the correct result is 'unresolved' or 'insufficient evidence for the acceptance target'.

## Initial implementation limits

The reference CLI computes coherent EVPI/EVSI values from supplied probability tables and reports measured strategy costs with Wilson confidence intervals. It does not run a real study, infer task meanings, learn coefficients, measure verification completeness, or attribute a causal AI productivity effect. Those are separate empirical research deliverables.
