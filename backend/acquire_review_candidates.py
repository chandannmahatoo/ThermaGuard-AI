"""Acquire real FIRMS review candidates. Never label, train, or send alerts."""
import argparse
import asyncio
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re
import sys

import httpx
from sqlalchemy import select
from app import ml, providers
from app.config import settings
from app.database import Session, Detection, Event
from app.intelligence import validate
from app.main import process
from export_review_candidates import export_candidates
from review_common import read_csv

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {'VIIRS_SNPP_NRT', 'VIIRS_SNPP_SP', 'VIIRS_NOAA20_NRT',
           'VIIRS_NOAA20_SP', 'VIIRS_NOAA21_NRT', 'MODIS_NRT', 'MODIS_SP'}


class ReviewConflict(ValueError):
    pass


def parse_plan(value):
    if not isinstance(value, dict) or not isinstance(value.get('regions'), list) or not value['regions']:
        raise ValueError('Plan must contain a nonempty regions list')
    if len(value['regions']) > 40:
        raise ValueError('Conservative limit: 40 region/date entries per run')
    result = []
    for entry in value['regions']:
        if not isinstance(entry, dict):
            raise ValueError('Each region must be an object')
        name = entry.get('name', '')
        if not isinstance(name, str) or not re.fullmatch(r'[a-z][a-z0-9_]{1,59}', name):
            raise ValueError('Region name must be a meaningful lowercase identifier')
        bounds = entry.get('bounds')
        if (not isinstance(bounds, list) or len(bounds) != 4
                or any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in bounds)):
            raise ValueError('Bounds must be four finite numbers: west,south,east,north')
        w, s, e, n = bounds
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
            raise ValueError('Invalid bounds order or coordinate range')
        try:
            start, end = (date.fromisoformat(entry[k]) for k in ('start_date', 'end_date'))
        except (KeyError, TypeError, ValueError):
            raise ValueError('Dates must use YYYY-MM-DD') from None
        if end < start or (end-start).days >= 365 or end > datetime.now(timezone.utc).date():
            raise ValueError('Date range must be ordered, not future, and at most 365 days')
        source = entry.get('source', 'VIIRS_SNPP_NRT')
        if source not in SOURCES:
            raise ValueError('Unsupported FIRMS source')
        maximum = entry.get('max_observations', 100)
        if type(maximum) is not int or not 1 <= maximum <= 500:
            raise ValueError('max_observations must be an integer from 1 to 500')
        result.append(dict(name=name, bounds=bounds, start_date=start.isoformat(),
                           end_date=end.isoformat(), source=source, max_observations=maximum))
    target = value.get('target_candidates', 40)
    if type(target) is not int or not 30 <= target <= 50:
        raise ValueError('target_candidates must be between 30 and 50')
    return dict(regions=result, target_candidates=target)


def chunks(region):
    start, end = date.fromisoformat(region['start_date']), date.fromisoformat(region['end_date'])
    while start <= end:
        days = min(5, (end-start).days+1)
        yield start.isoformat(), days
        start += timedelta(days=days)


def protect_reviews(db, rows):
    protected = {}
    for row in rows:
        if row.get('reviewed', '').strip().lower() != 'true':
            continue
        item = db.get(Event, row['event_id'])
        if item is None or item.is_demo or item.payload.get('is_demo') is not False:
            raise ReviewConflict('Reviewed event missing or provenance changed: ' + row['event_id'])
        fresh = ml.candidate_row(item.payload)
        for key in ml.ASSISTANCE_COLUMNS + ml.FEATURES:
            value = '' if fresh.get(key) is None else str(fresh[key])
            if key in row and row[key] != value:
                raise ReviewConflict('Reviewed CSV evidence differs from database: ' + row['event_id'])
        protected[item.id] = deepcopy(item.payload)
    return protected


def verify_protected(events, protected):
    current = {event['id']: event for event in events}
    for event_id, snapshot in protected.items():
        if current.get(event_id) != snapshot:
            raise ReviewConflict('Acquisition rolled back: reviewed event changed or reclustered: '
                                 + event_id + '. Human reconciliation required; no label transferred.')


async def ingest_batch(db, observations, reviewed_rows):
    """Reuse the pipeline inside a rollback-capable transaction, with exact evidence guards."""
    protected = protect_reviews(db, reviewed_rows)
    accepted = {}
    for row in observations:
        if row.get('is_demo') is not False or row.get('provider') != 'NASA' or row.get('source') != 'NASA FIRMS':
            raise ValueError('Acquisition accepts only real NASA FIRMS observations')
        verified = validate(row['raw'], is_demo=False)
        if any(verified[k] != row.get(k) for k in verified if k != 'retrieved_at'):
            raise ValueError('Observation does not match validated FIRMS provenance')
        accepted.setdefault(row['id'], row)
    before = {e.id for e in db.scalars(select(Event).where(Event.is_demo.is_(False)))}
    existing = sum(db.get(Detection, key) is not None for key in accepted)
    try:
        events = await process(db, list(accepted.values()), enrich=False,
                               create_notifications=False, commit=False)
        verify_protected(events, protected)
    except Exception:
        db.rollback()
        raise
    after = {e['id'] for e in events}
    return dict(new_detections=len(accepted)-existing, existing_detections=existing,
                duplicate_observations=len(observations)-len(accepted),
                new_events=len(after-before), removed_reclustered_events=len(before-after),
                candidate_events=len(after))


def backup_reviews(path):
    _, rows, content = read_csv(path)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    directory = path.parent / 'backups'
    directory.mkdir(exist_ok=True)
    backup = directory / f'{path.stem}.pre_acquisition.{stamp}.csv'
    with backup.open('xb') as stream:
        stream.write(content)
    snapshot = directory / f'reviewed_snapshot.{stamp}.json'
    snapshot.write_text(json.dumps([r for r in rows if r.get('reviewed', '').strip().lower() == 'true'], indent=2))
    return rows, content, backup


async def acquire(plan, *, dry_run=False, candidates=ml.CANDIDATES, session_factory=Session, provider=None):
    plan = parse_plan(plan)
    if dry_run:
        return dict(dry_run=True, provider_requests=0, plan=plan,
                    planned_requests=sum(len(list(chunks(r))) for r in plan['regions']))
    if settings.demo_mode:
        raise ValueError('Acquisition requires DEMO_MODE=false')
    provider = provider or providers.firms
    candidates = Path(candidates)
    # Fail before any provider call if a reviewed event already differs from its evidence.
    _, initial_rows, _ = read_csv(candidates)
    with session_factory() as db:
        protect_reviews(db, initial_rows)
    original_rows, _, backup = backup_reviews(candidates)
    original_reviews = {r['event_id']: r for r in original_rows if r.get('reviewed', '').strip().lower() == 'true'}
    log = dict(started_at=datetime.now(timezone.utc).isoformat(), backup=str(backup),
               no_alerts=True, training_performed=False, batches=[], reviewed_ids=list(original_reviews))
    log_path = candidates.parent / 'review_acquisition_last_run.json'

    def save():
        content = json.dumps(log, indent=2)
        log_path.write_text(content)
        backup.with_suffix('.acquisition.json').write_text(content)

    save()
    for region in plan['regions']:
        region_used = 0
        for start, days in chunks(region):
            with session_factory() as db:
                count = len(list(db.scalars(select(Event).where(Event.is_demo.is_(False)))))
            if count >= plan['target_candidates']:
                log['stop_reason'] = 'Candidate target reached; human review still required'
                save()
                return log
            stat = dict(region=region['name'], bounds=region['bounds'], start_date=start, days=days,
                        source=region['source'], provider_requests=1, raw_observations=None,
                        accepted_observations=0, rejected_observations=None,
                        new_detections=0, existing_detections=0, new_events=0,
                        removed_reclustered_events=0, candidate_events=count)
            log['batches'].append(stat)
            try:
                observations, rejected = await provider(bounds=region['bounds'], days=days,
                                                        start_date=start, source=region['source'])
                stat.update(raw_observations=len(observations)+rejected, accepted_observations=len(observations),
                            rejected_observations=rejected)
                if len(observations)+region_used > region['max_observations']:
                    stat['status'] = 'Skipped whole response: region observation budget exceeded; narrow the plan'
                    save()
                    break  # Do not truncate events into misleading partial clusters.
                region_used += len(observations)
                end = date.fromisoformat(start)+timedelta(days=days-1)
                w, s, e, n = region['bounds']
                for observation in observations:
                    day = date.fromisoformat(observation['observed_at'][:10])
                    if not (w <= observation['longitude'] <= e and s <= observation['latitude'] <= n
                            and date.fromisoformat(start) <= day <= end):
                        raise ValueError('Provider observations fall outside requested bounds/dates')
                    observation['acquisition_query'] = dict(region=region['name'], source=region['source'],
                                                           bounds=region['bounds'], start_date=start, days=days)
                _, rows, original = read_csv(candidates)
                with session_factory() as db:
                    batch = await ingest_batch(db, observations, rows)
                    if candidates.read_bytes() != original:
                        db.rollback()
                        raise ReviewConflict('Candidate CSV changed during acquisition; batch rolled back')
                    db.commit()
                stat.update(batch)
                exported = export_candidates(candidates, session_factory)
                _, updated, _ = read_csv(candidates)
                updated_by_id = {r['event_id']: r for r in updated}
                if any(updated_by_id.get(k) != v for k, v in original_reviews.items()):
                    raise ReviewConflict('Post-export review mismatch: restore preserved backup and reconcile manually')
                stat['candidate_events'] = exported['total']
                stat['status'] = 'committed'
            except ReviewConflict:
                stat['status'] = 'Stopped: reviewed evidence conflict; manual reconciliation required'
                save()
                raise
            except httpx.HTTPStatusError as exc:
                stat['status'] = f'Provider HTTP {exc.response.status_code}; no observations ingested'
            except httpx.HTTPError:
                stat['status'] = 'Provider network failure; no observations ingested'
            except ValueError:
                # Never print provider exceptions, which may contain credential-bearing URLs.
                stat['status'] = 'Stopped: validation/schema/budget failure; inspect plan and provider availability'
                save()
                raise ValueError(stat['status']) from None
            save()
            print(json.dumps(stat), flush=True)
    log['stop_reason'] = 'Plan exhausted; actual counts only'
    save()
    return log


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--region')
    parser.add_argument('--bounds', type=float, nargs=4)
    parser.add_argument('--start-date')
    parser.add_argument('--end-date')
    parser.add_argument('--source', default='VIIRS_SNPP_NRT', choices=sorted(SOURCES))
    parser.add_argument('--max-observations', type=int, default=100)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--no-alert', '--no-alerts', action='store_true', default=True,
                        help='Always enabled for candidate acquisition')
    args = parser.parse_args(argv)
    try:
        if args.plan:
            plan = json.loads(args.plan.read_text())
        else:
            plan = {'regions': [dict(name=args.region, bounds=args.bounds, start_date=args.start_date,
                                    end_date=args.end_date, source=args.source, max_observations=args.max_observations)]}
        print(json.dumps(asyncio.run(acquire(plan, dry_run=args.dry_run)), indent=2))
        return 0
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    except Exception:
        print('ERROR: Acquisition stopped; inspect local database/configuration. Credentials suppressed.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
