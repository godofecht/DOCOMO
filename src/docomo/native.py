"""Group-held-out research calibration of *actual* independently accepted project effort.

This is a prospective training facility, not a claim that public AI-native
project data already exist. It does not interpret source lines as verified value.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .calibration import _metrics, _ols
from .cocomo2 import estimate_cocomo_ii
from .manifests import assess_readiness, validate_project

COCOMO_HOURS_PER_PM = 152.0


def _vector(record: Mapping[str, Any], model: str) -> list[float]:
    features = record['planning_features']
    if model == 'size_only':
        return [1.0, math.log(features['equivalent_ksloc'])]
    if model == 'docomo_scope':
        return [
            1.0,
            math.log(features['functional_units']),
            math.log1p(features['dependency_edges']),
            math.log1p(features['verification_obligations']),
            math.log1p(features['ambiguous_requirements']),
            float(record['workflow'] == 'ai_assisted'),
            float(record['workflow'] == 'agent_delegated'),
        ]
    raise ValueError(f'unrecognised model {model}')


def _prediction(record: Mapping[str,Any], name: str, beta: list[float] | None) -> float:
    if name == 'cocomo2_nominal_assumptions':
        result = estimate_cocomo_ii({'equivalent_ksloc':record['planning_features']['equivalent_ksloc']})
        return result['person_months']*COCOMO_HOURS_PER_PM*60
    if beta is None:
        raise ValueError('missing fitted coefficients')
    estimate = math.exp(math.fsum(x*b for x,b in zip(_vector(record,name), beta)))
    if not math.isfinite(estimate) or estimate <= 0:
        raise ValueError('invalid predicted effort')
    return estimate


def calibrate_native(manifests: Sequence[Mapping[str, Any]], *, allow_synthetic: bool = False,
                     folds: int = 4) -> dict:
    """Estimate and compare *conditional accepted-project* human effort in minutes.

    Requires real versioned measurements across diverse independent repositories.
    With no data, returns an explicit insufficiency report; never fits synthetic data
    unless specifically invoked by a test with allow_synthetic=True.
    """
    if not isinstance(manifests, list):
        raise ValueError('manifests must be a JSON array')
    if not allow_synthetic and any(isinstance(record, Mapping) and record.get('synthetic') is True
                                   for record in manifests):
        raise ValueError('synthetic project manifests cannot calibrate production models')
    readiness = assess_readiness(manifests)
    if not readiness['structurally_ready_for_external_calibration_review']:
        return {
            'status': 'insufficient_project_evidence',
            'readiness': readiness,
            'coefficients': None,
            'warnings': ['No fitted AI-native cost model; requirements and independent evidence gate not met.'],
        }

    records = [validate_project(m) for m in manifests]
    accepted = [r for r in records if r['acceptance']['accepted']]
    repos = sorted({r['snapshot']['repository'] for r in accepted})
    if len(repos) < folds * 2 or not 3 <= folds <= 6:
        return {
            'status': 'insufficient_accepted_repository_coverage',
            'readiness': readiness,
            'coefficients': None,
        }
    assignment = {repo:i%folds for i,repo in enumerate(repos)}
    all_sized = all('equivalent_ksloc' in r['planning_features'] for r in accepted)
    names = ['docomo_scope'] + (['size_only', 'cocomo2_nominal_assumptions'] if all_sized else [])
    paired = {name:[] for name in names}
    for k in range(folds):
        train = [r for r in accepted if assignment[r['snapshot']['repository']] != k]
        test = [r for r in accepted if assignment[r['snapshot']['repository']] == k]
        if not test or len(train) <= 7:
            return {
                'status':'insufficient_group_holdout_training_data',
                'readiness':readiness,
                'coefficients':None,
            }
        for name in names:
            if name == 'cocomo2_nominal_assumptions':
                beta = None
            else:
                beta = _ols([_vector(r,name) for r in train],
                            [math.log(r['outcome']['total_human_minutes']) for r in train])
            for r in test:
                paired[name].append((r['outcome']['total_human_minutes'], _prediction(r,name,beta)))
    metrics = {name:_metrics([x for x,_ in pairs],[y for _,y in pairs])
               for name,pairs in paired.items()}
    winner = min(names,key=lambda name:(metrics[name]['log_rmse'],name))
    trained = {name:_ols([_vector(r,name) for r in accepted],
                         [math.log(r['outcome']['total_human_minutes']) for r in accepted])
               for name in names if name != 'cocomo2_nominal_assumptions'}
    return {
        'status':'internal_repo_group_validation_only',
        'calibration_domain': next(iter(readiness['domains'])),
        'model_selection': winner,
        'coefficient_units':'log(human_working_minutes)',
        'minutes_per_person_month':COCOMO_HOURS_PER_PM*60,
        'full_sample_coefficients': trained,
        'cross_validated_metrics': metrics,
        'independent_repositories':len(repos),
        'accepted_projects':len(accepted),
        'unaccepted_projects':len(records)-len(accepted),
        'readiness':readiness,
        'comparison_status': 'COCOMOII_nominal_assumptions_not_rated' if all_sized else 'missing_COCOMOII_size_or_ratings',
        'machine_expenditure': {
            'currency':records[0]['outcome']['currency'],
            'mean_cost_per_accepted':math.fsum(r['outcome']['machine_cost'] for r in accepted)/len(accepted),
            'status':'descriptive_only_not_predicted',
        },
        'caveats': [
            'Coefficients are fit only to accepted deliveries, not probability of acceptance or cost of abandoned projects.',
            'Same-project failed attempts are included only if the supplied measurement ledger is truthful.',
            'Group crossvalidation is exploratory and does NOT constitute an untouched prospective test set.',
            'The COCOMO II baseline defaults to nominal factors; a rated Post-Architecture comparison needs audited factor ratings.',
            'Observational AI-workflow associations are NOT causal productivity treatment effects.',
            'Self-attested independent acceptance must be audited before any external calibration claim.',
            'Separate elapsed-time, uncertainty intervals and predicted machine cost still require validation.',
        ],
    }
