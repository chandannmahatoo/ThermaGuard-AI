"""Inspect one candidate; change human-owned metadata only with explicit flags."""
from datetime import datetime, timezone
import argparse
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError
from app import ml
from app.intelligence import CLASSES
from review_common import MANUAL_FIELDS, read_csv, require_training_columns, reviewed_errors, write_csv
from review_event_summary import load_event, render_summary, display


def update_review_row(path, event_id, updates):
    """Never alter features/provenance, select a label, or infer source references."""
    path = Path(path)
    columns, rows, original = read_csv(path)
    require_training_columns(columns)
    matches = [row for row in rows if row['event_id'] == event_id]
    if not matches:
        raise ValueError(f'Candidate not found: {event_id}; export current events first')
    row = matches[0]
    if not updates:
        return row.copy(), None
    if set(updates) - set(MANUAL_FIELDS):
        raise ValueError('Only label, split_group, reviewer, source_reference and reviewed can be updated')
    if any(not isinstance(value, str) for value in updates.values()):
        raise ValueError('Review values must be text')
    if 'label' in updates and updates['label'] not in CLASSES:
        raise ValueError('Invalid label; choose one of the five accepted classes')
    if 'reviewed' in updates and updates['reviewed'].lower() not in ('true', 'false'):
        raise ValueError('reviewed must be true or false')
    changes = dict(updates)
    if 'reviewed' in changes:
        changes['reviewed'] = changes['reviewed'].lower()
    if changes.get('reviewed') == 'true' and 'reviewed_at' not in changes:
        # Timestamp the explicit human approval now; never backdate existing labels.
        changes['reviewed_at'] = datetime.now(timezone.utc).isoformat()
    edited = {**row, **changes}
    if edited.get('is_demo', '').lower() != 'false':
        raise ValueError('Only non-demo candidate rows can be reviewed')
    for key in ('reviewer', 'split_group'):
        if not edited.get(key, '').strip():
            raise ValueError(f'{key} is required for an explicit update')
        if edited[key] != edited[key].strip():
            raise ValueError(f'{key} must not contain surrounding whitespace')
    if edited.get('reviewed', '').lower() not in ('true', 'false'):
        raise ValueError('reviewed must be true or false; specify it explicitly to correct the row')
    if edited['reviewed'].lower() == 'true':
        problems = reviewed_errors(edited, require_timestamp=True)
        if problems:
            raise ValueError('; '.join(problems))
        if 'reviewed' not in changes:
            raise ValueError('Editing an approved row requires explicit --reviewed true to reapprove or --reviewed false to reopen')
    columns += [key for key in changes if key not in columns]
    row.update(changes)
    backup = write_csv(path, columns, rows, original)
    return row.copy(), backup


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('event_id')
    parser.add_argument('--candidates', type=Path, default=ml.CANDIDATES)
    parser.add_argument('--label', choices=CLASSES)
    parser.add_argument('--split-group')
    parser.add_argument('--reviewer')
    parser.add_argument('--reviewed-at')
    parser.add_argument('--review-notes')
    parser.add_argument('--source-reference')
    parser.add_argument('--reviewed', type=str.lower, choices=['true', 'false'])
    args = parser.parse_args(argv)
    try:
        _, rows, _ = read_csv(args.candidates)
        row = next((row for row in rows if row['event_id'] == args.event_id), None)
        if row is None:
            raise ValueError(f'Candidate not found: {args.event_id}; export current events first')
        print(render_summary(load_event(args.event_id)))
        print('\nAllowed classes (not recommendations):')
        for label in CLASSES:
            print(f'  {label}')
        print('\nExisting human review fields:')
        for key in MANUAL_FIELDS:
            print(f'  {key}: {display(row.get(key))}')
        updates = {key: getattr(args, key) for key in MANUAL_FIELDS if getattr(args, key) is not None}
        if not updates:
            print('\nRead-only: candidate CSV was not modified. No label selected.')
            return 0
        _, backup = update_review_row(args.candidates, args.event_id, updates)
        print('\nUpdated only explicitly supplied review metadata for: ' + args.event_id)
        print(f'Backup: {backup}' if backup else 'Values unchanged; no write or backup needed.')
        print('ML feature cells and every other candidate row are unchanged.')
        return 0
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
    except SQLAlchemyError:
        print('ERROR: Unable to read the configured event database; no review update applied.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
