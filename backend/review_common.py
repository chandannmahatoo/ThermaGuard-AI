"""Small CSV safety helpers shared by offline human-review commands."""
import csv
import io
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.intelligence import CLASSES, FEATURES
from app.ml import TRAINING_COLUMNS
from app.review_validation import valid_source_reference

MANUAL_FIELDS = ('split_group', 'label', 'reviewed', 'reviewer', 'source_reference')


def read_csv(path):
    """Read a strict, unique event table and retain bytes for safe replacement."""
    path = Path(path)
    if not path.exists():
        raise ValueError(f'CSV not found: {path}')
    original = path.read_bytes()
    reader = csv.DictReader(io.StringIO(original.decode('utf-8-sig'), newline=''))
    columns = list(reader.fieldnames or [])
    if not columns or len(columns) != len(set(columns)):
        raise ValueError('CSV header is empty or contains duplicate columns')
    if 'event_id' not in columns:
        raise ValueError('CSV is missing event_id')
    rows = list(reader)
    seen = set()
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f'CSV row {line} has the wrong number of cells')
        event_id = row['event_id']
        if not event_id.strip() or event_id != event_id.strip():
            raise ValueError(f'CSV row {line} has a blank or padded event_id')
        if event_id in seen:
            raise ValueError(f'Duplicate event_id: {event_id}; refusing to discard either row')
        seen.add(event_id)
    return columns, rows, original


def write_csv(path, columns, rows, original=None):
    """Back up an existing file, then atomically replace it; no-op if unchanged.

    Detect edits since read_csv(). Do not run CSV editors and these commands
    concurrently: the comparison is a safeguard, not a multi-user lock.
    """
    path = Path(path)
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction='raise')
    writer.writeheader()
    writer.writerows(rows)
    content = buffer.getvalue().encode('utf-8')
    current = path.read_bytes() if path.exists() else None
    if current != original:
        raise ValueError('CSV changed since it was read; reload before writing')
    if content == current:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if current is not None:
        directory = path.parent / 'backups'
        directory.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        backup = directory / f'{path.stem}.{stamp}.csv'
        with backup.open('xb') as stream:
            stream.write(current)
    descriptor, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if (path.read_bytes() if path.exists() else None) != original:
            raise ValueError('CSV changed during writing; original preserved, retry after reloading')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return backup


def reviewed_errors(row):
    """Publication guard: never publish a row the unchanged ml.dataset rejects."""
    errors = []
    event_id = row.get('event_id', '')
    if not event_id.strip() or event_id != event_id.strip():
        errors.append('event_id must be nonempty and unpadded')
    if row.get('label') not in CLASSES:
        errors.append('label must be one of the five accepted classes')
    if row.get('reviewed', '').lower() != 'true':
        errors.append('reviewed must be true (no surrounding whitespace)')
    if row.get('is_demo', '').lower() != 'false':
        errors.append('is_demo must be false (no surrounding whitespace)')
    for key in ('reviewer', 'source_reference', 'split_group'):
        value = row.get(key, '')
        if not value.strip():
            errors.append(f'{key} is required')
        elif value != value.strip():
            errors.append(f'{key} must not contain surrounding whitespace')
    if not valid_source_reference(row.get("source_reference")):
        errors.append("source_reference must identify meaningful evidence, not a placeholder")
    present = 0
    for key in FEATURES:
        value = row.get(key, '')
        if value == '':
            continue
        try:
            number = float(value)
            if not math.isfinite(number):
                raise ValueError()
            present += 1
        except (ValueError, TypeError):
            errors.append(f'{key} must be finite numeric data or blank')
    if not present:
        errors.append('at least one finite numeric ML feature is required')
    return errors


def require_training_columns(columns):
    missing = [key for key in TRAINING_COLUMNS if key not in columns]
    if missing:
        raise ValueError('Missing required CSV columns: ' + ', '.join(missing))
