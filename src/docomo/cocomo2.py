"""COCOMO II.2000 Post-Architecture reference estimator.

Published ratings and constants, NOT calibrated against DOCOMO AI data.
Source: USC COCOMO II Model Definition Manual, version 2.1, Table 62.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

RATINGS = ('VL', 'L', 'N', 'H', 'VH', 'XH')
SCALE = {
    'PREC': (6.20, 4.96, 3.72, 2.48, 1.24, 0.00),
    'FLEX': (5.07, 4.05, 3.04, 2.03, 1.01, 0.00),
    'RESL': (7.07, 5.65, 4.24, 2.83, 1.41, 0.00),
    'TEAM': (5.48, 4.38, 3.29, 2.19, 1.10, 0.00),
    'PMAT': (7.80, 6.24, 4.68, 3.12, 1.56, 0.00),
}
# None means the published rating is inapplicable, not an inferred multiplier.
EFFORT = {
    'RELY': (0.82, 0.92, 1.00, 1.10, 1.26, None),
    'DATA': (None, 0.90, 1.00, 1.14, 1.28, None),
    'CPLX': (0.73, 0.87, 1.00, 1.17, 1.34, 1.74),
    'RUSE': (None, 0.95, 1.00, 1.07, 1.15, 1.24),
    'DOCU': (0.81, 0.91, 1.00, 1.11, 1.23, None),
    'TIME': (None, None, 1.00, 1.11, 1.29, 1.63),
    'STOR': (None, None, 1.00, 1.05, 1.17, 1.46),
    'PVOL': (None, 0.87, 1.00, 1.15, 1.30, None),
    'ACAP': (1.42, 1.19, 1.00, 0.85, 0.71, None),
    'PCAP': (1.34, 1.15, 1.00, 0.88, 0.76, None),
    'PCON': (1.29, 1.12, 1.00, 0.90, 0.81, None),
    'APEX': (1.22, 1.10, 1.00, 0.88, 0.81, None),
    'PLEX': (1.19, 1.09, 1.00, 0.91, 0.85, None),
    'LTEX': (1.20, 1.09, 1.00, 0.91, 0.84, None),
    'TOOL': (1.17, 1.09, 1.00, 0.90, 0.78, None),
    'SITE': (1.22, 1.09, 1.00, 0.93, 0.86, 0.80),
    'SCED': (1.43, 1.14, 1.00, 1.00, 1.00, None),
}
A, B, C, D = 2.94, 0.91, 3.67, 0.28


def _positive(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f'{name} must be a positive finite number')
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f'{name} must be a positive finite number')
    return result


def _ratings(provided: Any, table: dict, kind: str) -> tuple[dict[str, float], dict[str, str], list[str]]:
    if provided is None:
        provided = {}
    if not isinstance(provided, Mapping):
        raise ValueError(f'{kind} must be an object')
    extra = set(provided) - set(table)
    if extra:
        raise ValueError(f'unknown {kind} factors: {sorted(extra)}')
    numeric, names, defaults = {}, {}, []
    for name, row in table.items():
        raw = provided.get(name, 'N')
        if name not in provided:
            defaults.append(name)
        if isinstance(raw, str):
            label = raw.upper()
            if label not in RATINGS:
                raise ValueError(f'{kind}.{name}: invalid rating {raw}')
            value = row[RATINGS.index(label)]
            if value is None:
                raise ValueError(f'{kind}.{name}: {label} is not a defined COCOMO II rating')
            numeric[name] = value
            names[name] = label
        elif kind == 'scale_factors':
            value = float(raw) if type(raw) in (int, float) else float('nan')
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'{kind}.{name}: numeric scale factor must be finite and nonnegative')
            numeric[name] = value
            names[name] = 'numeric'
        else:
            numeric[name] = _positive(raw, f'{kind}.{name}')
            names[name] = 'numeric'
    return numeric, names, defaults


def estimate_cocomo_ii(spec: Mapping[str, Any]) -> dict:
    """COCOMO II.2000 nominal Post-Architecture equations.

    KSLOC is *equivalent* delivered source size according to COCOMO II sizing
    rules, not merely generated lines. Module-level driver aggregation, reuse,
    adaptation, auto-translation and early-design models are not implemented.
    """
    if not isinstance(spec, Mapping):
        raise ValueError('spec must be an object')
    ks = _positive(spec.get('equivalent_ksloc'), 'equivalent_ksloc')
    sf, sf_names, assumed_sf = _ratings(spec.get('scale_factors'), SCALE, 'scale_factors')
    em, em_names, assumed_em = _ratings(spec.get('effort_multipliers'), EFFORT, 'effort_multipliers')
    exponent = B + .01 * math.fsum(sf.values())
    try:
        effort_without_sced = A * ks**exponent * math.prod(v for k,v in em.items() if k!='SCED')
        effort = effort_without_sced * em['SCED']
        schedule_factor = D + .2*(exponent-B)
        schedule_percent = _positive(spec.get('schedule_percent', 100.0), 'schedule_percent')
        months = C*effort_without_sced**schedule_factor * schedule_percent/100
    except OverflowError as exc:
        raise ValueError('numerical overflow in COCOMO II calculation') from exc
    if not all(map(math.isfinite, (effort, effort_without_sced, months))) or min(effort, effort_without_sced, months) <= 0:
        raise ValueError('invalid derived effort or schedule')
    if em_names['SCED'] != 'N' and 'schedule_percent' not in spec:
        raise ValueError('non-nominal SCED requires explicit schedule_percent')
    return {
        'model': 'COCOMO_II_2000_POST_ARCHITECTURE', 'model_status': 'published_historical_baseline',
        'equivalent_ksloc': ks, 'exponent': exponent, 'effort_adjustment_factor': math.prod(em.values()),
        'person_months': effort, 'nominal_schedule_person_months': effort_without_sced,
        'calendar_months': months, 'estimated_average_people': effort/months,
        'scale_factor_values': sf, 'effort_multiplier_values': em,
        'assumed_nominal_scale_factors': assumed_sf,
        'assumed_nominal_effort_multipliers': assumed_em,
        'limitations': [
            'Unmodified published 2000-era formula; not recalibrated for AI.',
            'Equivalent KSLOC must follow COCOMO II sizing/reuse procedures.',
            'Ratings and costs require independent elicitation; omitted ratings are assumed nominal and disclosed.',
            'Schedule compression is a separately supplied percentage, not inferred from SCED rating.',
        ],
    }
