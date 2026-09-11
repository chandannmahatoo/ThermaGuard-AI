"""Read-only chronological queue; no class predictions or label ranking."""
import argparse
from datetime import date
from pathlib import Path

from app import ml
from candidate_inventory import PLAN, inventory, render_table


def review_queue(rows, *, limit=10, region=None, cohort=None, start_date=None,
                 end_date=None, landuse=None, reviewed='false'):
    if limit < 1:
        raise ValueError('limit must be positive')
    return [r for r in sorted(rows, key=lambda r: (r['date'], r['region'], r['event_id']))
            if (reviewed == 'all' or r.get('reviewed', '').strip().lower() == reviewed)
            and (not region or region == r['region'])
            and (not cohort or cohort in (r['suggested_cohort'], r.get('split_group')))
            and (not start_date or r['date'] >= start_date)
            and (not end_date or r['date'] <= end_date)
            and (not landuse or r.get('landuse_class') == landuse)][:limit]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--candidates', type=Path, default=ml.CANDIDATES)
    parser.add_argument('--plan', type=Path, default=PLAN)
    parser.add_argument('--region')
    parser.add_argument('--cohort')
    parser.add_argument('--date', help='Exact UTC date, YYYY-MM-DD')
    parser.add_argument('--start-date')
    parser.add_argument('--end-date')
    parser.add_argument('--landuse')
    parser.add_argument('--reviewed', choices=['true', 'false', 'all'], default='false')
    args = parser.parse_args(argv)
    start, end = args.date or args.start_date, args.date or args.end_date
    for value in (start, end):
        if value:
            date.fromisoformat(value)
    if start and end and start > end:
        parser.error('start-date must precede end-date')
    if args.limit < 1:
        parser.error('limit must be positive')
    rows, _ = inventory(args.candidates, args.plan)
    selected = review_queue(rows, limit=args.limit, region=args.region, cohort=args.cohort,
                            start_date=start, end_date=end, landuse=args.landuse, reviewed=args.reviewed)
    print(render_table(selected))
    print(f'{len(selected)} candidates shown. Read-only; geographic/time names need human verification.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
