# DOCOMO: decision-grounded complexity estimation

## Aim

DOCOMO is an experimental extension to COCOMO for AI-assisted engineering. Estimate the cost of **accepted, independently verified behaviour**, not lines of code, prompts, generated tokens, or a model's self-rated task difficulty.

There are two independent questions:

1. **Grounding:** Do plausible interpretations of a requirement imply materially different decisions, and would an observation or clarification justify its cost?
2. **Engineering complexity:** Given fixed scope, knowledge, environment, tools, personnel, model versions, and acceptance protocol, what resources are empirically required to achieve an accepted outcome?

Grounding debt and construction effort must never be collapsed into a single subjective complexity score.

## Grounding model

Let Theta be the finite set of candidate interpretations, A the available engineering actions, p(theta) the *explicitly elicited* prior distribution, and L(a,theta) the consequence of selecting action a when theta is intended. Losses must use the same units across actions and scenarios.

Current optimal Bayes risk:

    R0 = min_a sum_theta p(theta) L(a,theta)

Risk with perfect interpretation knowledge:

    R* = sum_theta p(theta) min_a L(a,theta)

Decision-relevant ambiguity:

    EVPI = R0 - R*

A concept can be semantically ambiguous but have EVPI zero for a particular decision: all interpretations may recommend the same action. Thus unresolved semantics is not automatically a reason to delay implementation.

For a proposed evidence channel e with possible observations o, conditional observation probabilities p(o|theta,e), and cost c(e):

    Re = sum_o min_a sum_theta p(theta) p(o|theta,e) L(a,theta)
    EVSI(e) = R0 - Re
    NetValue(e) = EVSI(e) - c(e)

The v0.1 engine recommends the best available **single** evidence channel when NetValue is positive. If no channel was proposed, an EVPI-positive decision stays unresolved. If the only channels are not worth their cost, the result says exactly that; it does not certify a concept as well grounded.

Grounding has several modes. Mathematical contracts and operational semantics provide *definitional* grounding. Benchmarks and test measurements provide *empirical* grounding. Requirements involving fairness, legitimacy, or stakeholder values may need *normative* authority, not statistical inference.

The reference engine does **not** infer plausible interpretations, priors, utility weights, stakeholder intent, or observation probabilities. Such quantities are explicit assumptions that must be independently supported. Never silently substitute equal priors, model confidence, linguistic entropy, or a generated answer for verified evidence. Missing information should produce an unresolved state.

## Complexity model

The theoretical quantity is the lowest conditional expected cost of reaching independently accepted behaviour, subject to an acceptance-probability requirement:

    C_epsilon(T | K,E,V) = inf_pi E[cost(pi)]
                           subject to P(accepted(pi)) >= 1-epsilon

This is an objective, **not** a computed intrinsic task score. T is fixed scope; K is available knowledge; E is execution environment; V is an external acceptance protocol; pi is a permitted human/machine workflow.

The implemented estimator uses repeated attempts for each strategy. Each observed attempt records accepted (boolean), human working minutes, machine cost, and elapsed minutes. A provided hourly rate converts human effort to monetary cost. Elapsed time remains a distinct dimension and is not added to monetary cost.

    acceptance_rate = successes / trials
    estimated_cost_per_accepted_outcome = total_attempt_cost / successes

The latter is an expected repeat-until-success cost *only if* attempts are independent and stationary; otherwise it is descriptive. The engine uses Wilson binomial confidence intervals and qualifies a strategy only if the **lower** confidence bound meets the declared acceptance target. A few perfect trials therefore cannot automatically justify a strong reliability claim.

Keep uncertainty types distinct: ambiguous scope, unknown model parameters, process variability, insufficient verification coverage, and changes to requirements or tools. A Wilson interval only addresses sampling uncertainty about an independent binary success rate. Passing the specified tests does not guarantee the tests reflect actual needs.

## From v0.1 to predictive software economics

Preserve unmodified COCOMO II as a baseline. Calibrate distinct effort categories: specification, generation, verification, integration, orchestration, rework, and assurance. Human labour, inference expenses, infrastructure, and elapsed calendar time need separate accounting to prevent double counting. A global AI productivity multiplier is a competing baseline, not an assumption.

Potential predictive covariates include task dependencies and coupling, proof obligations, independent observability, functional scope, requirement volatility, acceptance thresholds, and model/tool maturity. Their predictive contribution must be demonstrated on held-out projects. SLOC can remain a historical input without being treated as the definition of size.

## Staged roadmap

**Phase 0 (implemented).** Pure-Python grounding evaluator with EVPI/EVSI, explicit loss and evidence likelihood tables; observational complexity evaluator with Wilson intervals and accepted-outcome costs; JSON command-line interface; example fixtures; tests.

**Phase 1.** Versioned task/evidence manifests, task-acceptance provenance, tool/model configuration, machine and human accounting, and independent oracle ownership. Flag when an agent authored both implementation and acceptance tests. Add reproducible evaluation traces.

**Phase 2.** Robust prior and loss sensitivity analysis, uncertain and contested priors, sequential evidence acquisition with dependent tests, and counterexample search. Discovery of no alternative interpretation must never prove completeness.

**Phase 3.** Estimate separate verification/rework/integration distributions; model dependency DAGs and human reviewer bottlenecks; calibrate task-class-specific cost models with out-of-sample coverage checks. Make human-only, AI-assisted, and autonomous agent comparisons experimentally valid.

**Phase 4.** Prospective total cost and schedule forecasts, version-drift detection after model changes, assurance and provenance constraints, comparison to COCOMO II and scalar AI multipliers. Retain explicit 'insufficient evidence' outputs.

## Non-negotiable invariants

Raw observations, supplied assumptions, inferred parameters and forecasts must be separately identified. No invented probabilities, no invented empirical results, no model-confidence-as-accuracy, no unvalidated intrinsic complexity rating. Do not equate speed of generation with delivery of verified, accepted systems.
