"""Reproducible domain-specific historical and AI-task calibration.

Early AI-task treatment estimates must never be extrapolated into a global
person-month multiplier for COCOMO. No synthetic calibration data are used.
"""
from __future__ import annotations

import csv
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Sequence

DRIVERS = ('rely','data','cplx','time','stor','virt','turn','acap','aexp','pcap','vexp','lexp','modp','tool','sced')
MODES = {'organic': (3.2, 1.05), 'semidetached': (3.0, 1.12), 'embedded': (2.8, 1.20)}


def _positive(value: str | float | int, label: str) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{label}: invalid number') from exc
    if not math.isfinite(x) or x <= 0:
        raise ValueError(f'{label}: expected positive finite number')
    return x


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    a = [matrix[i][:] + [vector[i]] for i in range(n)]
    for i in range(n):
        pivot = max(range(i, n), key=lambda j: abs(a[j][i]))
        if abs(a[pivot][i]) < 1e-12:
            raise ValueError('rank-deficient design matrix')
        a[i], a[pivot] = a[pivot], a[i]
        factor = a[i][i]
        a[i] = [v / factor for v in a[i]]
        for j in range(n):
            if j != i:
                factor = a[j][i]
                a[j] = [a[j][k] - factor * a[i][k] for k in range(n+1)]
    return [a[i][-1] for i in range(n)]


def _ols(x: Sequence[Sequence[float]], y: Sequence[float]) -> list[float]:
    if not x or len(x) != len(y):
        raise ValueError('no matching observations')
    p = len(x[0])
    if len(x) < p + 1 or any(len(row) != p for row in x):
        raise ValueError('insufficient observations for model')
    gram = [[math.fsum(row[i] * row[j] for row in x) + (1e-8 if i == j and i > 0 else 0.0)
             for j in range(p)] for i in range(p)]
    rhs = [math.fsum(row[i] * z for row, z in zip(x, y)) for i in range(p)]
    return _solve(gram, rhs)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return math.fsum(x*y for x, y in zip(a, b))


def _metrics(actual: list[float], predictions: list[float]) -> dict:
    if not actual or len(actual) != len(predictions):
        raise ValueError('metrics require matched nonempty values')
    errors = [abs(y-p) for y, p in zip(actual, predictions)]
    logs = [math.log(p/y) for y, p in zip(actual, predictions)]
    return {
        'n': len(actual),
        'mae': math.fsum(errors)/len(errors),
        'median_absolute_error': statistics.median(errors),
        'median_relative_error': statistics.median(e/y for e, y in zip(errors, actual)),
        'log_rmse': math.sqrt(math.fsum(z*z for z in logs)/len(logs)),
        'pred25': sum(e/y <= .25 for e, y in zip(errors, actual))/len(errors),
    }


def read_cocomo81(path: str | Path) -> list[dict]:
    with open(path, newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) < 15:
        raise ValueError('too few historic observations')
    required = {'num', 'dev_mode', 'loc', 'actual', *DRIVERS}
    if any(not required.issubset(row) for row in rows):
        raise ValueError('missing required historical fields')
    output = []
    identifiers = set()
    for row in rows:
        idx = int(row['num'])
        if idx in identifiers:
            raise ValueError('duplicate project ID')
        identifiers.add(idx)
        mode = row['dev_mode'].strip().lower().replace('-', '')
        if mode not in MODES:
            raise ValueError(f'unknown COCOMO-I development mode: {mode}')
        eaf = math.prod(_positive(row[d], d) for d in DRIVERS)
        output.append({'id': idx, 'mode': mode, 'kloc': _positive(row['loc'], 'loc'),
                       'person_months': _positive(row['actual'], 'actual'), 'eaf': eaf})
    return output


def _cocomo81(row: dict) -> float:
    a, b = MODES[row['mode']]
    return a * row['kloc'] ** b * row['eaf']


def _project_features(row: dict, model: str) -> list[float]:
    if model == 'size_only':
        return [1.0, math.log(row['kloc'])]
    if model == 'size_mode_eaf':
        return [1.0, math.log(row['kloc']), math.log(row['eaf']),
                float(row['mode'] == 'embedded'), float(row['mode'] == 'semidetached')]
    if model == 'cocomo81_recalibrated':
        return [1.0]
    raise ValueError(f'unknown model {model}')


def _train_project(rows: list[dict], model: str) -> list[float]:
    x = [_project_features(row, model) for row in rows]
    y = [math.log(row['person_months']) - (
        math.log(_cocomo81(row)) if model == 'cocomo81_recalibrated' else 0
    ) for row in rows]
    return _ols(x, y)


def _predict_project(row: dict, model: str, beta: list[float]) -> float:
    result = _dot(_project_features(row, model), beta)
    if model == 'cocomo81_recalibrated':
        result += math.log(_cocomo81(row))
    return math.exp(result)


def calibrate_projects(rows: list[dict], folds: int = 5) -> dict:
    """Project-level cross-validation; project identifiers assigned deterministic folds."""
    if folds < 3 or folds > len(rows)//3:
        raise ValueError('invalid folds')
    names = ['cocomo81_intermediate_fixed', 'size_only', 'cocomo81_recalibrated', 'size_mode_eaf']
    pairs: dict[str, list[tuple[float,float]]] = {n: [] for n in names}
    for k in range(folds):
        train = [r for r in rows if r['id'] % folds != k]
        test = [r for r in rows if r['id'] % folds == k]
        if not test:
            raise ValueError('empty validation fold')
        for name in names:
            beta = _train_project(train, name) if name != 'cocomo81_intermediate_fixed' else None
            for row in test:
                prediction = _cocomo81(row) if beta is None else _predict_project(row, name, beta)
                pairs[name].append((row['person_months'], prediction))
    metrics = {name: _metrics([v[0] for v in values], [v[1] for v in values]) for name, values in pairs.items()}
    fitted = {name: _train_project(rows, name) for name in names if name != 'cocomo81_intermediate_fixed'}
    winner = min(names, key=lambda name: (metrics[name]['log_rmse'], name))
    return {
        'domain': 'historical_cocomo81', 'samples': len(rows), 'folds': folds,
        'units': 'person_months', 'validation': 'project-id-modulo K-fold; no independent modern-project holdout',
        'model_metrics': metrics, 'full_data_coefficients': fitted,
        'cross_validated_best': winner,
        'warnings': ['COCOMO81 is pre-AI and has COCOMO-I drivers; this is not COCOMO II or AI-native calibration.',
                     'Training coefficients are descriptive and were fitted after selecting a model on these data.',
                     'No task-level AI treatment estimate can directly modify person-month predictions.'],
    }


def read_metr_early(path: str | Path) -> list[dict]:
    with open(path, newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    required = {'dev_id','issue_id','predicted_time_no_ai','ai_treatment',
                'initial_implementation_time','post_review_implementation_time'}
    if not rows or any(not required.issubset(r) for r in rows):
        raise ValueError('invalid METR early CSV')
    output, ids = [], set()
    for row in rows:
        issue_id = int(row['issue_id'])
        if issue_id in ids:
            raise ValueError('duplicate issue ID')
        ids.add(issue_id)
        assignment = int(float(row['ai_treatment']))
        if assignment not in (0,1):
            raise ValueError('invalid AI treatment')
        initial = _positive(row['initial_implementation_time'], 'initial_implementation_time')
        post = None if row['post_review_implementation_time'].strip() == '' else float(row['post_review_implementation_time'])
        if post is not None and (not math.isfinite(post) or post < 0):
            raise ValueError('invalid post-review time')
        output.append({'id': issue_id, 'developer': int(row['dev_id']),
                       'ai': assignment, 'estimated_no_ai': _positive(row['predicted_time_no_ai'], 'predicted_time_no_ai'),
                       'initial': initial, 'post': post})
    return output


def _imputed(rows: list[dict], population: list[dict]) -> list[dict]:
    means = {}
    for trt in (0,1):
        available = [r['post'] for r in population if r['ai'] == trt and r['post'] is not None]
        if not available:
            raise ValueError('no observed review times for treatment')
        means[trt] = statistics.mean(available)
    return [dict(r, total=r['initial'] + (r['post'] if r['post'] is not None else means[r['ai']])) for r in rows]


def _features_ai(row: dict, include_ai: bool) -> list[float]:
    return [1.0, math.log(row['estimated_no_ai'])] + ([float(row['ai'])] if include_ai else [])


def _fit_ai(rows: list[dict], include_ai: bool) -> list[float]:
    return _ols([_features_ai(r, include_ai) for r in rows], [math.log(r['total']) for r in rows])


def _ai_oof(rows: list[dict], include_ai: bool, folds: int) -> dict:
    true, predictions = [], []
    for k in range(folds):
        tr = [r for r in rows if r['developer'] % folds != k]
        te = [r for r in rows if r['developer'] % folds == k]
        if not tr or not te:
            raise ValueError('empty developer-group validation split')
        tr_i = _imputed(tr, tr)
        te_i = _imputed(te, tr)
        beta = _fit_ai(tr_i, include_ai)
        true.extend(r['total'] for r in te_i)
        predictions.extend(math.exp(_dot(_features_ai(r, include_ai), beta)) for r in te_i)
    return _metrics(true, predictions)


def calibrate_ai_tasks(rows: list[dict], folds: int = 4, replicates: int = 400, seed: int = 2026) -> dict:
    """Early-2025 METR randomised treatment calibration; not a verified delivery-cost model."""
    if len(set(r['developer'] for r in rows)) < folds or replicates < 50:
        raise ValueError('insufficient developers or bootstrap replicates')
    full = _imputed(rows, rows)
    beta = _fit_ai(full, True)
    rng = random.Random(seed)
    groups = defaultdict(list)
    for row in rows:
        groups[row['developer']].append(row)
    group_ids = sorted(groups)
    effects = []
    for _ in range(replicates):
        ids = rng.choices(group_ids, k=len(group_ids))
        sample = [row for group_id in ids for row in groups[group_id]]
        try:
            fit = _fit_ai(_imputed(sample, sample), True)
            effects.append(math.expm1(fit[2]))
        except ValueError:
            continue
    if len(effects) < int(.9 * replicates):
        raise ValueError('too many invalid bootstrap resamples')
    effects.sort()
    lo = effects[int(.025 * len(effects))]
    hi = effects[min(len(effects)-1, math.ceil(.975 * len(effects)) - 1)]
    return {
        'domain': 'metr_early_2025_tasks', 'samples': len(rows), 'developers': len(group_ids),
        'treatment_groups': {'ai_allowed': sum(r['ai'] for r in rows), 'ai_disallowed': sum(not r['ai'] for r in rows)},
        'outcome': 'developer implementation minutes including imputed post-review time',
        'coefficients': {'intercept': beta[0], 'log_pre_randomization_estimate': beta[1], 'ai_allowed': beta[2]},
        'ai_time_ratio_minus_one': math.expm1(beta[2]),
        'cluster_bootstrap_95pct': [lo, hi], 'cluster_bootstrap_successes': len(effects),
        'seed': seed, 'group_validation': 'held-out developers, developer-ID modulo folds',
        'prediction_comparison': {
            'without_treatment': _ai_oof(rows, False, folds),
            'with_treatment': _ai_oof(rows, True, folds),
        },
        'warnings': ['Conditional task-level time ratio, NOT general AI productivity or accepted project effort.',
                     'Treatment was randomised but observational task selection and study population restrict transportability.',
                     'Historical task-completion does not certify independent functionality/security acceptance.',
                     'Imputed post-review times follow the source study convention and depend on treatment group.',
                     'Bootstrap is clustered by developer; intervals remain sensitive to small cluster count.'],
    }
