"""Publish complete human-reviewed rows in the unchanged ML column order.

Incomplete, malformed, demo or numerically ineligible reviewed rows cause a
refusal, not silent dropping. Does not train or change the training gate.
"""
from pathlib import Path
import sys

from app import ml
from app.intelligence import CLASSES
from review_common import read_csv, require_training_columns, reviewed_errors, write_csv

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'reviewed_labels.csv'
CANDIDATES = ml.CANDIDATES


def finalize(candidates=None, output=None):
    candidates = Path(candidates) if candidates is not None else CANDIDATES
    output = Path(output) if output is not None else OUTPUT
    columns, rows, snapshot = read_csv(candidates)
    require_training_columns(columns)
    invalid_flags = [row['event_id'] for row in rows if row.get('reviewed', '').lower() not in ('true', 'false')]
    if invalid_flags:
        raise ValueError('Invalid reviewed values (use true/false without padding): ' + ', '.join(invalid_flags))
    reviewed = [row for row in rows if row['reviewed'].lower() == 'true']
    if not reviewed:
        raise ValueError('Nothing to finalize: no rows are marked reviewed=true')
    problems = [f"{row['event_id']}: {error}" for row in reviewed for error in reviewed_errors(row, require_timestamp=True)]
    if problems:
        raise ValueError('Refusing invalid reviewed rows:\n' + '\n'.join(problems))
    eligible = ml.dataset(candidates)
    if {row['event_id'] for row in eligible} != {row['event_id'] for row in reviewed}:
        raise ValueError('Reviewed rows disagree with ml.dataset eligibility; no output written')
    # Preserve sensor provenance alongside the unchanged model-input prefix.
    sensor_columns = [key for key in ml.SENSOR_COLUMNS if key in columns
                      and any(row.get(key, '') not in ('', None, '{}', '[]') for row in reviewed)]
    output_columns = ml.TRAINING_COLUMNS + sensor_columns + [key for key in ('reviewed_at','review_notes') if key in columns]
    output_rows = [{key: row.get(key, '') for key in output_columns}
                   for row in sorted(reviewed, key=lambda row: row['event_id'])]
    original = output.read_bytes() if output.exists() else None
    if candidates.read_bytes() != snapshot:
        raise ValueError('Candidate CSV changed during validation; retry after reloading')
    backup = write_csv(output, output_columns, output_rows, original)
    return {**ml.readiness(eligible), 'candidate_rows': len(rows), 'published_rows': len(output_rows),
            'class_counts': {label: sum(row['label'] == label for row in eligible) for label in CLASSES},
            'backup': backup, 'output': output}


def extend_sensor_evidence(output=None, session_factory=None):
    """Append observed evidence to the canonical legacy export, without reapproving labels.

    Existing cells are immutable. New timestamp/notes remain blank; only an
    explicit human review can satisfy the V2 gate. No training is performed.
    """
    import json
    from app.database import Session, Event, Detection
    from app.intelligence import sensor_evidence
    output=Path(output) if output else OUTPUT
    columns,rows,snapshot=read_csv(output)
    additions=[key for key in ml.SENSOR_COLUMNS+['reviewed_at','review_notes'] if key not in columns]
    with (session_factory or Session)() as db:
        for row in rows:
            item=db.get(Event,row['event_id'])
            if item is None or item.is_demo:raise ValueError('Canonical reviewed event missing or demo')
            observations=[]
            for identity in item.payload.get('detection_ids',[]):
                detection=db.get(Detection,identity)
                if detection is None or detection.is_demo:raise ValueError('Real observation missing')
                observations.append(detection.payload)
            evidence=sensor_evidence(observations)
            values={**evidence['sensor_summary'],
                    'source_counts':json.dumps(evidence['source_counts'],sort_keys=True),
                    'sensor_provenance':json.dumps(evidence['sensor_provenance'],sort_keys=True)}
            for key in additions:row[key]='' if values.get(key) is None else values[key]
    backup=write_csv(output,columns+additions,rows,snapshot)
    return {'rows_preserved':len(rows),'appended_columns':additions,'backup':str(backup) if backup else None,'reapproved':0}


def main():
    try:
        report = finalize()
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
    print(f"Wrote {report['published_rows']} reviewed rows to {report['output']}")
    print('Class distribution:')
    for label, count in report['class_counts'].items():
        print(f'  {label}: {count}')
    print(f"Split groups: {report['split_groups']}")
    print(f"Training ready: {'YES' if report['training_ready'] else 'NO'}")
    for item in report['missing']:
        print(f'  Missing: {item}')
    if report['backup']:
        print(f"Previous published CSV backup: {report['backup']}")
    print('No model training was requested or performed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
