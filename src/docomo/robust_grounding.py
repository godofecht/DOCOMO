"""No-prior minimax-regret and elicited-prior sensitivity for requirement grounding.

A finite set of stakeholder-supplied priors never constitutes an exhaustive
uncertainty set. No implicit uniform priors, unverified evidence likelihoods,
or synthetic probabilities are introduced.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from .grounding import assess_grounding


def _nonnegative(value: Any, field: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)) or value < 0:
        raise ValueError(f'{field}: expected nonnegative finite loss')
    return float(value)


def assess_robust_grounding(spec: Mapping[str, Any]) -> dict:
    if not isinstance(spec, Mapping):
        raise ValueError('robust grounding spec must be an object')
    theta = spec.get('interpretations')
    if not isinstance(theta, list) or not theta or any(not isinstance(t,str) or not t for t in theta):
        raise ValueError('interpretations must be a non-empty array of names')
    if len(set(theta)) != len(theta):
        raise ValueError('duplicate interpretations')
    choices = spec.get('decisions')
    if not isinstance(choices, Mapping) or not choices:
        raise ValueError('decisions must be a non-empty action-to-loss table')
    losses: dict[str,dict[str,float]] = {}
    for name, raw in choices.items():
        if not isinstance(name,str) or not name or not isinstance(raw,Mapping) or set(raw)!=set(theta):
            raise ValueError('every decision must have exactly the declared interpretation losses')
        losses[name]={t:_nonnegative(raw[t],f'decisions.{name}.{t}') for t in theta}
    baselines={t:min(losses[a][t] for a in losses) for t in theta}
    worst_regret={a:max(losses[a][t]-baselines[t] for t in theta) for a in losses}
    minimax=min(losses,key=lambda a:(worst_regret[a],a))
    prior_scenarios=spec.get('prior_scenarios', [])
    if not isinstance(prior_scenarios,list):
        raise ValueError('prior_scenarios must be an array')
    if len(prior_scenarios)!=len({r.get('id') for r in prior_scenarios if isinstance(r,Mapping)}):
        raise ValueError('prior scenario IDs must be unique')
    results=[]
    for index,scenario in enumerate(prior_scenarios):
        if not isinstance(scenario,Mapping) or not isinstance(scenario.get('id'),str) or not scenario['id']:
            raise ValueError(f'prior_scenarios[{index}] must have a nonempty id')
        priors=scenario.get('probabilities')
        if not isinstance(priors,Mapping) or set(priors)!=set(theta):
            raise ValueError('prior scenario probabilities must cover exactly the interpretations')
        single=assess_grounding({
            'task':spec.get('task'),
            'interpretations':dict(priors),
            'decisions':losses,
            'evidence':spec.get('evidence', []),
            'loss_units':spec.get('loss_units','unspecified'),
        })
        results.append({
            'id':scenario['id'],
            'optimal_action':single['baseline_action'],
            'expected_loss':single['baseline_expected_loss'],
            'evpi':single['evpi'],
            'recommended_evidence':single['recommended_evidence'],
            'evidence_net_values':{e['id']:e['net_value'] for e in single['evidence']},
        })
    recommended = {result['recommended_evidence'] for result in results}
    robust_evidence=next(iter(recommended)) if results and len(recommended)==1 and None not in recommended else None
    stable_actions={result['optimal_action'] for result in results}
    channels=set.intersection(*(set(r['evidence_net_values']) for r in results)) if results else set()
    worthwhile=sorted(channel for channel in channels if all(r['evidence_net_values'][channel]>1e-9 for r in results))
    return {
        'task':spec.get('task'),
        'loss_units':spec.get('loss_units','unspecified'),
        'no_prior_minimax_regret_action':minimax,
        'no_prior_minimax_regret':worst_regret[minimax],
        'worst_case_regret_per_action':worst_regret,
        'no_prior_decision_equivalence':all(v<=1e-9 for v in worst_regret.values()),
        'prior_scenarios':results,
        'scenarios_compared':len(results),
        'optimal_action_stable_across_listed_priors':len(stable_actions)==1 if results else None,
        'evpi_range_over_listed_priors':([min(r['evpi'] for r in results),
                                           max(r['evpi'] for r in results)] if results else None),
        'recommended_evidence_stable_across_listed_priors':robust_evidence,
        'evidence_worthwhile_across_all_listed_priors':worthwhile,
        'status':'finite_prior_sensitivity_only' if results else 'no_prior_minimax_regret_only',
        'limitations':[
            'Elicited prior scenarios are neither exhaustive nor necessarily defensible.',
            'No-prior minimax regret is a decision rule, not a probability estimate.',
            'EVPI and evidence decisions are evaluated at the listed points, NOT continuously over a prior interval.',
            'Loss valuations may encode contested normative assumptions and require stakeholder authority.',
            'No automatic discovery or completeness guarantee for interpretations and actions.',
        ],
    }
