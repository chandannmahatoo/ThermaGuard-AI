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
    problems = [f"{row['event_id']}: {error}" for row in reviewed for error in reviewed_errors(row)]
    if problems:
        raise ValueError('Refusing invalid reviewed rows:\n' + '\n'.join(problems))
    eligible = ml.dataset(candidates)
    if {row['event_id'] for row in eligible} != {row['event_id'] for row in reviewed}:
        raise ValueError('Reviewed rows disagree with ml.dataset eligibility; no output written')
    output_rows = [{key: row[key] for key in ml.TRAINING_COLUMNS}
                   for row in sorted(reviewed, key=lambda row: row['event_id'])]
    original = output.read_bytes() if output.exists() else None
    if candidates.read_bytes() != snapshot:
        raise ValueError('Candidate CSV changed during validation; retry after reloading')
    backup = write_csv(output, ml.TRAINING_COLUMNS, output_rows, original)
    return {**ml.readiness(eligible), 'candidate_rows': len(rows), 'published_rows': len(output_rows),
            'class_counts': {label: sum(row['label'] == label for row in eligible) for label in CLASSES},
            'backup': backup, 'output': output}


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
