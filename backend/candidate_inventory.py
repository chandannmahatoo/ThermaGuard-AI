"""Read-only inventory and geographic/time naming assistance, never group approval."""
import argparse
from collections import Counter
from datetime import datetime
import json
import math
from pathlib import Path
import re

from app import ml
from review_common import read_csv

PLAN = ml.ROOT / 'data' / 'review_acquisition_plan.example.json'


def cohort_for(row, regions):
    """Bounds are search zones, not land-use labels or proof of independent cohorts."""
    try:
        lat, lon = float(row['latitude']), float(row['longitude'])
        when = datetime.fromisoformat(row['start_time'])
        if not math.isfinite(lat) or not math.isfinite(lon):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        return 'unknown', 'unknown'
    matches = []
    for region in regions:
        w, s, e, n = region['bounds']
        if w <= lon <= e and s <= lat <= n:
            matches.append(region['name'])
    # Overlapping zones deliberately share a deterministic combined cohort name.
    name = '_'.join(sorted(set(matches))) or 'unmapped'
    name = re.sub(r'[^a-z0-9_]', '_', name.lower())
    return name, name + '_' + when.strftime('%b_%Y').lower()


def inventory(path=ml.CANDIDATES, plan=PLAN):
    _, rows, _ = read_csv(path)
    regions = json.loads(Path(plan).read_text()).get('regions', []) if Path(plan).exists() else []
    result = []
    for original in rows:
        region, cohort = cohort_for(original, regions)
        result.append({**original, 'region': region, 'suggested_cohort': cohort,
                       'date': original.get('start_time', '')[:10]})
    result.sort(key=lambda r: (r['date'], r['region'], r['event_id']))
    dates = [r['date'] for r in result if r['date']]
    reviewed = sum(r.get('reviewed', '').strip().lower() == 'true' for r in result)
    return result, dict(total=len(result), reviewed=reviewed, unreviewed=len(result)-reviewed,
                        candidate_regions=dict(Counter(r['region'] for r in result)),
                        date_range=[min(dates), max(dates)] if dates else [],
                        distinct_geographic_cohorts=len({r['region'] for r in result if r['region'] not in ('unknown', 'unmapped')}),
                        suggested_time_cohorts=sorted({r['suggested_cohort'] for r in result}))


def render_table(rows):
    keys = ['event_id', 'region', 'suggested_cohort', 'latitude', 'longitude', 'date',
            'reviewed', 'label', 'split_group', 'landuse_class', 'recurrence_count', 'risk_level']
    lines = ['\t'.join(keys)]
    for row in rows:
        lines.append('\t'.join(''.join(c if c.isprintable() else ' ' for c in str(row.get(k, ''))) for k in keys))
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, default=ml.CANDIDATES)
    parser.add_argument('--plan', type=Path, default=PLAN)
    args = parser.parse_args(argv)
    rows, summary = inventory(args.candidates, args.plan)
    print(render_table(rows))
    print(json.dumps(summary, indent=2))
    print('Cohort names are suggestions only. No split_group or review field was changed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
