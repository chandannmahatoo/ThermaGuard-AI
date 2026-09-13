"""Versioned review evidence comparison; never derive or modify human labels.

Legacy rows can only be compared on evidence columns they actually captured.
No numeric rounding hides small changes. Volatile provider metadata, model
predictions and deterministic risk outputs are not human evidence identities.
"""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from app import ml

VERSION = '1'
NON_MATERIAL = {'risk_score', 'risk_level'}
VOLATILE = {'fetched_at', 'refresh_status', 'refresh_reason', 'retry_at', 'cache_age', 'cache_hit', 'last_success', 'last_failure'}
FIELDS = tuple(dict.fromkeys([key for key in ml.FEATURES + ml.ASSISTANCE_COLUMNS if key not in NON_MATERIAL]))
JSON_FIELDS = {'source_counts', 'sensor_provenance'}


def normalize(value):
    if value is None or value == '':
        return None
    if isinstance(value, dict):
        return {key: normalize(v) for key, v in sorted(value.items()) if key not in VOLATILE}
    if isinstance(value, list):
        return sorted((normalize(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
    if isinstance(value, bool):
        return str(value).lower()
    text = str(value)
    try:
        number = Decimal(text)
        if number.is_finite():
            return str(number.normalize())
    except InvalidOperation:
        pass
    return text


def value_for(row, key):
    value = row.get(key)
    if key in JSON_FIELDS and isinstance(value, str) and value:
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            pass  # Invalid provenance is not silently discarded.
    return normalize(value)


def evidence_hash(row):
    payload = {key: value_for(row, key) for key in FIELDS if key in row}
    return hashlib.sha256(json.dumps({'version': VERSION, 'evidence': payload}, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def changes(prior, fresh):
    """Return material fields and harmless represented assistance differences."""
    material = [key for key in FIELDS if key in prior and value_for(prior, key) != value_for(fresh, key)]
    non_material = [key for key in NON_MATERIAL if key in prior and normalize(prior.get(key)) != normalize(fresh.get(key))]
    return {'material': sorted(material), 'non_material': sorted(non_material),
            'uncaptured_fields': [key for key in FIELDS if key not in prior]}
