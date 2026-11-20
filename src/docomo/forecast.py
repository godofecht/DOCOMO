"""Domain-scoped point forecasts from externally calibrated DOCOMO report artifacts.

Deliberately refuses to turn historical project coefficients or 2025
AI-task time effects into an unsupported AI-native project-cost forecast.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .calibration import DRIVERS, MODES


def _positive(x: Any, name: str) -> float:
    if type(x) not in (int, float) or not math.isfinite(float(x)) or x <= 0:
        raise ValueError(f'{name} must be a strictly positive finite number')
    return float(x)


def _coefficient(values: Any, name: str, count: int) -> list[float]:
    if not isinstance(values, list) or len(values) != count:
        raise ValueError(f'{name} must have {count} coefficients')
    for x in values:
        if type(x) not in (int, float) or not math.isfinite(float(x)):
            raise ValueError(f'{name} contains a non-finite coefficient')
    return [float(x) for x in values]


def forecast(report: Mapping[str, Any], spec: Mapping[str, Any]) -> dict:
    if not isinstance(report, Mapping) or report.get('schema_version') != '1.0' or report.get('calibration_status') != 'partial_domain_specific':
        raise ValueError('expected an authenticated, versioned partial-domain calibration report')
    if not isinstance(spec, Mapping):
        raise ValueError('forecast input must be an object')
    domain = spec.get('domain')
    if domain == 'historical_cocomo81':
        body = report.get('historical_effort')
        if not isinstance(body, Mapping) or body.get('samples') != 63:
            raise ValueError('missing expected historical COCOMO81 calibration')
        model = body.get('cross_validated_best')
        if model not in ('cocomo81_intermediate_fixed', 'size_only',
                         'cocomo81_recalibrated', 'size_mode_eaf'):
            raise ValueError('unsupported project model')
        mode = spec.get('development_mode')
        if mode not in MODES:
            raise ValueError('development_mode must be organic, semidetached or embedded')
        ks = _positive(spec.get('equivalent_kloc'), 'equivalent_kloc')
        multipliers = spec.get('cocomo81_multipliers')
        if not isinstance(multipliers, Mapping) or set(multipliers) != set(DRIVERS):
            raise ValueError('provide all 15 historically defined COCOMO81 multipliers')
        eaf = math.prod(_positive(multipliers[d], d) for d in DRIVERS)
        row = {'mode': mode, 'kloc': ks, 'eaf': eaf}
        if model == 'cocomo81_intermediate_fixed':
            a, b = MODES[mode]
            estimate = a * ks**b * eaf
        else:
            betas = body.get('full_data_coefficients', {})
            lengths = {'size_only':2, 'cocomo81_recalibrated':1, 'size_mode_eaf':5}
            beta = _coefficient(betas.get(model), model, lengths[model])
            if model == 'size_only':
                log_est = beta[0] + beta[1]*math.log(ks)
            elif model == 'cocomo81_recalibrated':
                a, b = MODES[mode]
                log_est = beta[0] + math.log(a) + b*math.log(ks) + math.log(eaf)
            else:
                log_est = (beta[0] + beta[1]*math.log(ks) + beta[2]*math.log(eaf)
                           + beta[3]*float(mode=='embedded')
                           + beta[4]*float(mode=='semidetached'))
            estimate = math.exp(log_est)
        if not math.isfinite(estimate) or estimate <= 0:
            raise ValueError('forecast is out of numeric range')
        bounds = body.get('observed_kloc_range')
        outside = (isinstance(bounds, list) and len(bounds)==2
                   and not (bounds[0] <= ks <= bounds[1]))
        return {'domain': domain, 'model':model,
                'point_prediction_person_months': estimate,
                'outside_training_size_range': outside,
                'calibration_status':'historical_only',
                'warnings':['Based on pre-AI COCOMO81 observations, NOT calibrated AI-native project effort.',
                            'No independently calibrated prediction interval is available.',
                            'COCOMO I driver ratings are not interchangeable with COCOMO II factors.']}

    if domain == 'metr_early_2025_tasks':
        body = report.get('early_ai_task_time')
        if not isinstance(body, Mapping) or body.get('samples') != 246:
            raise ValueError('missing expected METR early task calibration')
        minutes = _positive(spec.get('estimated_minutes_without_ai'), 'estimated_minutes_without_ai')
        ai = spec.get('ai_allowed')
        if type(ai) is not bool:
            raise ValueError('ai_allowed must be boolean')
        coefficients = body.get('coefficients', {})
        if not isinstance(coefficients, Mapping):
            raise ValueError('missing task model coefficients')
        beta = _coefficient([coefficients.get(k) for k in (
            'intercept', 'log_pre_randomization_estimate', 'ai_allowed')], 'task model', 3)
        point = math.exp(beta[0] + beta[1]*math.log(minutes) + beta[2]*int(ai))
        if not math.isfinite(point) or point <= 0:
            raise ValueError('task time forecast is outside numeric range')
        bounds = body.get('observed_estimate_range')
        outside = (isinstance(bounds,list) and len(bounds)==2
                   and not (bounds[0] <= minutes <= bounds[1]))
        return {
            'domain':domain, 'model':'metr_early_2025_ols',
            'conditional_geometric_mean_minutes':point,
            'outside_training_estimate_range':outside,
            'calibration_status':'historical_task_population_only',
            'warnings':['Conditional task-duration forecast for METR early-2025 open-source study population only.',
                        'Predicted geometric mean is NOT an arithmetic expected time or verified accepted-delivery cost.',
                        'No calibrated individual task prediction interval; no extrapolation to new model versions.'],
        }
    raise ValueError('forecast domain is unsupported; never silently combine incompatible calibrations')
