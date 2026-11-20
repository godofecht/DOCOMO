"""Strict, auditable project-outcome manifests for future AI-native calibration.

Input checks prevent missing values and obvious leakage but cannot establish
truth of human-supplied acceptance/provenance claims. No project data are invented.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

HEX40 = re.compile(r'^[a-fA-F0-9]{40}$')
HEX64 = re.compile(r'^[a-fA-F0-9]{64}$')
IDENTIFIER = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
STAGES = ('specification', 'implementation', 'verification', 'integration',
          'orchestration', 'rework', 'assurance')
WORKFLOWS = ('human_only', 'ai_assisted', 'agent_delegated')


def _object(value: Any, name: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError(f'{name} must be an object')
    return value


def _nonnegative(value: Any, name: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f'{name} must be a finite nonnegative number')
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f'{name} must be a finite nonnegative number')
    return value


def _int(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a non-empty string')
    return value.strip()


def _hash(value: Any, name: str, regex: re.Pattern) -> str:
    result = _string(value, name)
    if not regex.fullmatch(result):
        raise ValueError(f'{name} must be a hexadecimal content identifier')
    return result.lower()


def validate_project(manifest: Mapping[str, Any]) -> dict:
    """Normalise a project outcome only with explicit, reviewable evidence links."""
    m = _object(manifest, 'manifest')
    if m.get('schema_version') != '1.0':
        raise ValueError('unsupported manifest schema_version; expected 1.0')
    project_id = _string(m.get('project_id'), 'project_id')
    if not IDENTIFIER.fullmatch(project_id):
        raise ValueError('project_id contains invalid characters')
    domain = _string(m.get('domain'), 'domain')
    workflow = m.get('workflow')
    if workflow not in WORKFLOWS:
        raise ValueError(f'workflow must be one of {WORKFLOWS}')

    s = _object(m.get('snapshot'), 'snapshot')
    repository = _string(s.get('repository'), 'snapshot.repository')
    commit = _hash(s.get('commit'), 'snapshot.commit', HEX40)
    requirements_hash = _hash(s.get('requirements_sha256'), 'snapshot.requirements_sha256', HEX64)
    planning_recorded_at = _string(s.get('planning_recorded_at'), 'snapshot.planning_recorded_at')

    p = _object(m.get('planning_features'), 'planning_features')
    features = {name: _int(p.get(name), f'planning_features.{name}')
                for name in ('functional_units', 'dependency_edges',
                             'verification_obligations', 'ambiguous_requirements')}
    if features['functional_units'] == 0:
        raise ValueError('functional_units must be positive')
    if 'equivalent_ksloc' in p:
        value = _nonnegative(p['equivalent_ksloc'], 'planning_features.equivalent_ksloc')
        if value <= 0:
            raise ValueError('equivalent_ksloc must be positive if supplied')
        features['equivalent_ksloc'] = value

    v = _object(m.get('acceptance'), 'acceptance')
    accepted = v.get('accepted')
    if type(accepted) is not bool:
        raise ValueError('acceptance.accepted must be boolean')
    reviewer = _string(v.get('independent_reviewer'), 'acceptance.independent_reviewer')
    reviewer_kind = v.get('reviewer_kind')
    if reviewer_kind not in ('human_independent', 'automated_independent'):
        raise ValueError('reviewer_kind must specify an independent review process')
    test_oracle_sha = _hash(v.get('oracle_commit'), 'acceptance.oracle_commit', HEX40)
    evidence_url = _string(v.get('evidence_url'), 'acceptance.evidence_url')
    if not evidence_url.startswith(('https://', 'http://')):
        raise ValueError('acceptance.evidence_url must be an http(s) URL')
    if v.get('reviewer_is_author') is not False:
        raise ValueError('acceptance reviewer must not be the author')
    # This records an assertion of independent review, not independent proof.

    o = _object(m.get('outcome'), 'outcome')
    human = _object(o.get('human_minutes'), 'outcome.human_minutes')
    if set(human) != set(STAGES):
        raise ValueError(f'outcome.human_minutes must contain exactly {STAGES}')
    minutes = {name: _nonnegative(human[name], f'outcome.human_minutes.{name}') for name in STAGES}
    machine_cost = _nonnegative(o.get('machine_cost'), 'outcome.machine_cost')
    elapsed = _nonnegative(o.get('elapsed_minutes'), 'outcome.elapsed_minutes')
    currency = _string(o.get('currency'), 'outcome.currency').upper()
    if not re.fullmatch(r'[A-Z]{3}', currency):
        raise ValueError('currency must be a three-letter ISO code')
    if o.get('failed_attempts_included') is not True:
        raise ValueError('failed attempts and rework must be included in outcome cost accounting')
    if sum(minutes.values()) == 0 and machine_cost == 0:
        raise ValueError('an outcome cannot have zero human and machine cost')
    if elapsed == 0:
        raise ValueError('outcome.elapsed_minutes must be positive')
    project_time = _nonnegative(o.get('measurement_quality_score'), 'outcome.measurement_quality_score')
    if project_time > 1:
        raise ValueError('measurement_quality_score must be <= 1')

    context = _object(m.get('runtime'), 'runtime')
    toolchain = _string(context.get('toolchain'), 'runtime.toolchain')
    toolchain_version = _string(context.get('toolchain_version'), 'runtime.toolchain_version')
    model_id = context.get('model_id')
    if workflow != 'human_only':
        model_id = _string(model_id, 'runtime.model_id')
    elif model_id is not None:
        raise ValueError('human_only workflow must not declare active AI model')

    return {
        'schema_version': '1.0',
        'project_id': project_id, 'domain': domain, 'workflow': workflow,
        'snapshot': {'repository': repository, 'commit': commit,
                     'requirements_sha256': requirements_hash,
                     'planning_recorded_at': planning_recorded_at},
        'planning_features': features,
        'acceptance': {'accepted': accepted, 'independent_reviewer': reviewer,
                       'reviewer_kind': reviewer_kind, 'oracle_commit': test_oracle_sha,
                       'evidence_url': evidence_url, 'reviewer_is_author': False},
        'outcome': {'human_minutes': minutes, 'machine_cost': machine_cost,
                    'elapsed_minutes': elapsed, 'currency': currency,
                    'measurement_quality_score': project_time, 'failed_attempts_included': True,
                    'total_human_minutes': sum(minutes.values())},
        'runtime': {'toolchain': toolchain, 'toolchain_version': toolchain_version,
                    'model_id': model_id},
        'evidence_status': 'self_attested_links_need_independent_audit',
    }


def assess_readiness(manifests: Sequence[Mapping[str, Any]]) -> dict:
    """Structural readiness only, not a certification of a calibrated model."""
    records = [validate_project(item) for item in manifests]
    ids = [r['project_id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate project IDs')
    by_domain = Counter(r['domain'] for r in records)
    by_workflow = Counter(r['workflow'] for r in records)
    repos = {r['snapshot']['repository'] for r in records}
    accepted = sum(r['acceptance']['accepted'] for r in records)
    requirements = {
        'at_least_50_project_outcomes': len(records) >= 50,
        'at_least_8_distinct_repositories': len(repos) >= 8,
        'at_least_30_accepted_deliveries': accepted >= 30,
        'human_and_ai_workflows_present': by_workflow['human_only'] > 0
            and (by_workflow['ai_assisted'] + by_workflow['agent_delegated']) > 0,
        'single_project_domain': len(by_domain) == 1,
        'single_currency': len({r['outcome']['currency'] for r in records}) == 1,
    }
    return {
        'projects': len(records), 'accepted': accepted, 'repositories': len(repos),
        'domains': dict(by_domain), 'workflows': dict(by_workflow),
        'structural_requirements': requirements,
        'structurally_ready_for_external_calibration_review': all(requirements.values()),
        'calibration_status': 'not_externally_validated',
        'warnings': [
            'Structural thresholds are necessary screening rules, not sufficient proof of calibrated project effort.',
            'Self-attested acceptance links require independent evidence audit.',
            'Before fitting, audit independence and representativeness, prospective feature timestamps and held-out repositories.',
            'Acceptance outcomes, rework costs and software defects must not leak into planning-time features.',
        ],
    }
