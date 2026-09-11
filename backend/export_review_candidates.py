"""Export real events, preserving manual review fields and custom notes safely."""
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app.database import Session, Event
from app.ml import REVIEW_META, ASSISTANCE_COLUMNS, candidate_row
from app.intelligence import FEATURES
from review_common import MANUAL_FIELDS, read_csv, reviewed_errors, write_csv

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'review_candidates.csv'
COLUMNS = REVIEW_META + list(FEATURES) + ASSISTANCE_COLUMNS


def export_candidates(path=None, session_factory=None):
    path = Path(path) if path is not None else OUTPUT
    old_columns, previous, original = read_csv(path) if path.exists() else ([], [], None)
    old = {row['event_id']: row for row in previous}
    extras = [key for key in old_columns if key not in COLUMNS]
    columns = COLUMNS + extras
    rows = []
    with (session_factory or Session)() as db:
        for item in db.scalars(select(Event).where(Event.is_demo.is_(False)).order_by(Event.id)):
            if item.payload.get('id') != item.id or item.payload.get('is_demo') is not False:
                raise ValueError(f'Inconsistent identity/demo provenance for event {item.id}; export stopped')
            fresh = candidate_row(item.payload)
            # Produce the same cell representation as csv.DictWriter before comparison.
            row = {key: '' if fresh.get(key) is None else str(fresh[key]) for key in COLUMNS}
            prior = old.get(item.id)
            if prior:
                if prior.get('is_demo', '').lower() != 'false':
                    raise ValueError(f'{item.id}: prior is_demo is not false; resolve provenance before export')
                evidence_changed = any(prior[key] != row[key] for key in FEATURES + ASSISTANCE_COLUMNS if key in prior)
                if prior.get('reviewed', '').strip().lower() == 'true' and not reviewed_errors(prior) and evidence_changed:
                    raise ValueError(f'{item.id}: reviewed evidence changed. Prior CSV is untouched. A reviewer must explicitly reopen review (reviewed=false) before refreshing this row.')
                for key in MANUAL_FIELDS:
                    if key in prior:
                        row[key] = prior[key]  # Preserve even intentional blanks, exactly.
            row.update({key: prior.get(key, '') if prior else '' for key in extras})
            rows.append(row)
    exported = {row['event_id'] for row in rows}
    if len(exported) != len(rows):
        raise ValueError('Duplicate event_id in database payloads; export stopped')
    missing_reviewed = [key for key in old.keys() - exported if old[key].get("reviewed", "").strip().lower() == "true"]
    if missing_reviewed:
        raise ValueError("Reviewed event IDs disappeared; human reconciliation required: " + ", ".join(sorted(missing_reviewed)))
    backup = write_csv(path, columns, rows, original)
    return dict(total=len(rows), added=sorted(exported - old.keys()), removed=sorted(old.keys() - exported),
                preserved=len(exported & old.keys()), backup=backup, output=path)


def main():
    try:
        report = export_candidates()
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print('ERROR: Cannot read configured event database; candidate CSV was not replaced.', file=sys.stderr)
        return 1
    print(f"Exported {report['total']} real non-demo events")
    print(f"Output: {report['output']}")
    print(f"Manual review fields preserved for {report['preserved']} matching events")
    for title, key in [('New events', 'added'), ('Removed/reclustered events', 'removed')]:
        print(f"{title}: {len(report[key])}")
        for event_id in report[key]:
            print(f'  {event_id}')
    if report['backup']:
        print(f"Prior rows and all reviewer edits backed up to: {report['backup']}")
    else:
        print('No prior content changed; no backup needed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
