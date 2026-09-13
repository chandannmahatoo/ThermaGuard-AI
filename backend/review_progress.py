"""Read-only human-review progress using the existing ML eligibility and gate."""
import argparse
from collections import Counter
from pathlib import Path
import sys

from app import ml
from app.intelligence import CLASSES
from review_common import read_csv


def review_progress(path=None):
    path = Path(path) if path is not None else ml.CANDIDATES
    _, rows, _ = read_csv(path)
    report = ml.candidate_report(path)
    eligible = ml.dataset(path)
    counts = Counter(row['label'] for row in eligible)
    return {**report, 'total_candidates': len(rows),
            'class_counts': {label: counts[label] for label in CLASSES},
            'missing_classes': [label for label in CLASSES if not counts[label]],
            'remaining_rows': max(0, 30 - len(eligible)),
            'remaining_groups': max(0, 10 - report['split_groups']),
            'row_completion_percent': min(100, len(eligible) / 30 * 100)}


def render_progress(report):
    lines = [f"Total candidates: {report['total_candidates']}",
             f"Reviewed rows: {report['reviewed_rows']}",
             f"Eligible rows: {report['eligible_rows']}", 'Required minimum: 30',
             f"Remaining reviewed events needed: {report['remaining_rows']}", '',
             'Class distribution (eligible rows only):']
    lines.extend(f"{label}: {count}" for label, count in report['class_counts'].items())
    lines.extend(['', f"Classes present: {report['classes_present']}/5",
                  'Missing classes: ' + (', '.join(report['missing_classes']) or 'None'),
                  f"Split groups: {report['split_groups']}/10",
                  f"Remaining independent groups needed: {report['remaining_groups']}",
                  f"Eligible-row completion: {report['row_completion_percent']:.1f}% (30-row target only)",
                  f"Training ready: {'YES' if report['training_ready'] else 'NO'}",
                  'This is candidate readiness, not a trained model or publication of reviewed_labels.csv.',
                  'Group independence and source authenticity require human verification.'])
    if report['problems']:
        lines.append('Validation problems (resolve before finalization):')
        lines.extend(f'- {problem}' for problem in report['problems'])
    return '\n'.join(lines)


def resolve_legacy_source(row):
    """Resolve only mutually consistent stored query or documented sensor/version evidence."""
    import re
    from app.config import FIRMS_SOURCES
    from app.intelligence import sensor_family, observation_identity, validate
    if row.get('is_demo'):
        return None, 'demo'
    raw = row.get('raw') or {}
    family = sensor_family(row)
    version = str(raw.get('version') or row.get('version') or '')
    instrument = row.get('instrument') or raw.get('instrument')
    inferred = None
    if version.upper().endswith('NRT') and re.fullmatch(r'\d+(?:\.\d+)?NRT', version.upper()):
        inferred = {'SNPP':'VIIRS_SNPP_NRT','NOAA20':'VIIRS_NOAA20_NRT','NOAA21':'VIIRS_NOAA21_NRT','MODIS':'MODIS_NRT'}.get(family)
    explicit = row.get('source_dataset') or row.get('acquisition_query', {}).get('source')
    if explicit and (explicit not in FIRMS_SOURCES or FIRMS_SOURCES[explicit][1] != instrument
                     or (inferred and explicit != inferred)):
        return None, 'ambiguous'
    source = explicit or inferred
    if not source:
        return None, 'unresolved'
    expected_family = 'MODIS' if source.startswith('MODIS') else source.split('_')[1]
    if family != expected_family:
        return None, 'ambiguous'
    try:
        normalized = validate(raw, source_dataset=source)
        if observation_identity(normalized) != observation_identity(row):
            return None, 'ambiguous'
    except (ValueError, TypeError, KeyError):
        return None, 'unresolved'
    return source, 'stored_query' if explicit else 'documented_sensor_version'


def reconcile_legacy(apply=False, session_factory=None):
    from copy import deepcopy
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.database import Session, Detection
    report = {'resolved':0, 'unresolved':0, 'ambiguous':0, 'already_recorded':0, 'methods':{}, 'applied':apply}
    with (session_factory or Session)() as db:
        for item in db.scalars(select(Detection).where(Detection.is_demo.is_(False))):
            if item.payload.get('source_dataset'):
                report['already_recorded'] += 1
                continue
            source, method = resolve_legacy_source(item.payload)
            if source:
                report['resolved'] += 1
                report['methods'][method] = report['methods'].get(method,0)+1
                if apply:
                    payload = deepcopy(item.payload)
                    payload.update(source_dataset=source, provider='NASA FIRMS',
                        version=payload.get('raw',{}).get('version'),
                        source_reconciliation={'method':method,'recorded_at':datetime.now(timezone.utc).isoformat()})
                    item.payload = payload  # Preserve observation ID, raw row, measurements and event IDs.
            else:
                report['ambiguous' if method=='ambiguous' else 'unresolved'] += 1
        if apply:db.commit()
    return report


def model_v2_report(path=None, session_factory=None, published=None):
    """Read-only evidence audit. Never chooses labels, changes groups or calls training."""
    import csv
    import json
    import math
    from datetime import datetime, timezone
    from sqlalchemy import select
    from app.config import FIRMS_SOURCES
    from app.database import Session, Detection, Event, Alert
    from app.intelligence import sensor_evidence, sensor_family, observation_identity, distance
    from review_common import reviewed_errors
    path = Path(path) if path else ml.CANDIDATES
    with path.open() as file: rows=list(csv.DictReader(file))
    published = Path(published) if published else ml.DATA
    publication = []
    if published.exists():
        with published.open() as file:
            publication = list(csv.DictReader(file))
    with (session_factory or Session)() as db:
        detections={r.id:r.payload for r in db.scalars(select(Detection))}
        events={r.id:r.payload for r in db.scalars(select(Event))}
        alerts=len(list(db.scalars(select(Alert))))
    real={key:row for key,row in detections.items() if row.get('is_demo') is False}
    real_events={key:row for key,row in events.items() if row.get('is_demo') is False}
    reviewed={r['event_id']:r for r in rows if r.get('reviewed','').lower()=='true'}
    facts={key:[real[d] for d in event.get('detection_ids',[]) if d in real] for key,event in real_events.items()}
    evidence={key:sensor_evidence(values) for key,values in facts.items() if values}
    effective=lambda row: row.get('source_dataset') or row.get('acquisition_query',{}).get('source') or 'unknown_legacy'
    source_sets={key:sorted({effective(row) for row in values}) for key,values in facts.items()}
    sensor_sets={key:sorted({sensor_family(row) for row in values}) for key,values in facts.items()}
    inventory={source:{'supported':source in FIRMS_SOURCES,'detections':0,'events':0,'reviewed_events':0,'v2_eligible_events':0,'min_date':None,'max_date':None} for source in [*FIRMS_SOURCES,'unknown_legacy']}
    for row in real.values():
        source=effective(row)
        bucket=inventory.setdefault(source,{'supported':False,'detections':0,'events':0,'reviewed_events':0,'v2_eligible_events':0,'min_date':None,'max_date':None})
        day=row.get('observed_at','')[:10]
        bucket['detections']+=1
        if day:
            bucket['min_date']=min(bucket['min_date'] or day,day);bucket['max_date']=max(bucket['max_date'] or day,day)
    issues={'duplicate_candidate_ids':[key for key,n in Counter(r.get('event_id') for r in rows).items() if n>1],
            'conflicting_labels':[], 'stale_reviewed_events':[], 'review_quality_failures':{},
            'invalid_observations':[], 'missing_provenance':sum(not row.get('source_dataset') for row in real.values()),
            'overpass_split_conflicts':[], 'nearby_site_split_conflicts':[], 'missing_detection_references':[]}
    labels={}
    for row in [*rows,*publication]:
        if row.get('reviewed','').lower()=='true':labels.setdefault(row['event_id'],set()).add(row.get('label'))
    issues['conflicting_labels']=[key for key,value in labels.items() if len(value)>1]
    physical={}
    for key,row in real.items():
        try:
            confidence=row.get('confidence')
            valid_confidence=confidence in (None,'','l','n','h') or (math.isfinite(float(confidence)) and 0<=float(confidence)<=100)
            if not valid_confidence:raise ValueError('confidence')
            if not (-90<=float(row['latitude'])<=90 and -180<=float(row['longitude'])<=180 and math.isfinite(float(row['frp'])) and float(row['frp'])>=0):raise ValueError('measurements')
            stamp=datetime.fromisoformat(row['observed_at'])
            if stamp.tzinfo is None or stamp>datetime.now(timezone.utc):raise ValueError('timestamp')
            satellite={'1':'N20','2':'N21','Aqua':'A','Terra':'T'}.get(str(row.get('satellite')),row.get('satellite'))
            physical.setdefault(observation_identity({**row,'satellite':satellite}),[]).append(key)
        except (ValueError,TypeError,KeyError):issues['invalid_observations'].append(key)
    exact=Counter((effective(row),observation_identity(row)) for row in real.values())
    issues['duplicate_provider_observations']=sum(n-1 for n in exact.values() if n>1)
    issues['nrt_sp_extra_representations']=sum(len(values)-1 for values in physical.values())
    eligible=[]
    for key,row in reviewed.items():
        errors=reviewed_errors(row,require_timestamp=True)
        event=real_events.get(key)
        if not event:errors.append('Real event missing')
        else:
            fresh=ml.candidate_row(event)
            from app.review_evidence import changes
            if changes(row, fresh)['material']:
                issues['stale_reviewed_events'].append(key);errors.append('Reviewed evidence differs from stored event')
            if 'unknown_legacy' in source_sets[key]:errors.append('Unknown source provenance')
        if errors:issues['review_quality_failures'][key]=errors
        else:eligible.append(key)
    for key,sources in source_sets.items():
        for source in sources:
            inventory[source]['events']+=1
            inventory[source]['reviewed_events']+=int(key in reviewed)
            inventory[source]['v2_eligible_events']+=int(key in eligible)
    physical_events={}
    for key,event in real_events.items():
        if any(d not in real for d in event.get('detection_ids',[])):issues['missing_detection_references'].append(key)
        if key not in reviewed:continue
        for row in facts[key]:
            satellite={'1':'N20','2':'N21','Aqua':'A','Terra':'T'}.get(str(row.get('satellite')),row.get('satellite'))
            physical_events.setdefault(observation_identity({**row,'satellite':satellite}),set()).add(key)
    for linked in physical_events.values():
        if len(linked)>1 and len({reviewed[key].get('split_group') for key in linked})>1:
            entry=sorted(linked)
            if entry not in issues['overpass_split_conflicts']:issues['overpass_split_conflicts'].append(entry)
    reviewed_ids=sorted(set(reviewed)&set(real_events))
    for index,key in enumerate(reviewed_ids):
        for other in reviewed_ids[:index]:
            if reviewed[key].get('split_group')!=reviewed[other].get('split_group') and distance(real_events[key],real_events[other])<=5:
                issues['nearby_site_split_conflicts'].append([other,key])
    def profile(keys):
        fields=['frp','primary_thermal','secondary_thermal','ndvi','osm_context','historical_recurrence',*ml.V2_SENSOR_FIELDS]
        missing={field:0 for field in fields}
        for key in keys:
            event=real_events[key];members=facts[key];summary=evidence.get(key,{}).get('sensor_summary',{})
            values={**summary,'frp':event.get('mean_frp'),
                'primary_thermal':next((row.get('thermal_primary',row.get('brightness')) for row in members if row.get('thermal_primary',row.get('brightness')) is not None),None),
                'secondary_thermal':next((row.get('thermal_secondary') or row.get('raw',{}).get('bright_ti5') or row.get('raw',{}).get('bright_t31') for row in members if row.get('thermal_secondary') is not None or row.get('raw',{}).get('bright_ti5') or row.get('raw',{}).get('bright_t31')),None),
                'ndvi':event.get('context',{}).get('ndvi'),
                'osm_context':True if event.get('context',{}).get('osm_context_available') else None,
                'historical_recurrence':event.get('history',{}).get('recurrence_count')}
            for field in fields:missing[field]+=int(values.get(field) in (None,''))
        return {'events':len(keys),'missing':missing}
    matrix={label:{family:sum(key in reviewed and reviewed[key].get('label')==label and family in sensor_sets[key] for key in real_events) for family in ('SNPP','NOAA20','NOAA21','MODIS')} for label in CLASSES}
    class_counts={label:sum(row.get('label')==label for row in reviewed.values()) for label in CLASSES}
    eligible_classes={label:sum(reviewed[key].get('label')==label for key in eligible) for label in CLASSES}
    kind=lambda sources: 'unknown' if 'unknown_legacy' in sources else 'mixed_nrt_sp' if any(s.endswith('_NRT') for s in sources) and any(s.endswith('_SP') for s in sources) else 'nrt_only' if all(s.endswith('_NRT') for s in sources) else 'sp_only'
    groups={row.get('split_group') for row in reviewed.values() if row.get('split_group')}
    reasons=[]
    if len(eligible)<100:reasons.append(f'{100-len(eligible)} additional timestamped, current-evidence reviewed events needed for Stage A')
    if any(n<30 for n in eligible_classes.values()):reasons.append('At least 30 eligible reviewed events per class needed for serious V2 evaluation')
    if len({reviewed[key].get('split_group') for key in eligible})<10:reasons.append('Fewer than 10 eligible independent split groups')
    if len({family for key in eligible for family in sensor_sets[key] if family!='unknown'})<2:reasons.append('Eligible reviews do not cover multiple sensor families')
    if not any(evidence.get(key,{}).get('sensor_summary',{}).get('cross_sensor_confirmed') for key in eligible):reasons.append('No eligible reviewed cross-sensor event')
    if issues['nearby_site_split_conflicts'] or issues['overpass_split_conflicts']:reasons.append('Geographic/overpass split leakage risks require human reconciliation')
    if issues['conflicting_labels'] or issues['duplicate_candidate_ids'] or issues['invalid_observations']:reasons.append('Unresolved data quality errors')
    return {'supported_by_code':list(FIRMS_SOURCES), 'inventory_by_source':inventory,
        'totals':{'real_detections':len(real),'demo_detections':len(detections)-len(real),'real_events':len(real_events),'demo_events':len(events)-len(real_events),'alerts':alerts,'candidates':len(rows),'reviewed_claimed':len(reviewed),'unreviewed':sum(r.get('reviewed','').lower()=='false' for r in rows),'v2_eligible':len(eligible)},
        'events_by_source_combination':dict(Counter(' + '.join(sources) for sources in source_sets.values())),
        'events_by_sensor_combination':dict(Counter(' + '.join(sensors) for sensors in sensor_sets.values())),
        'events_processing_kind':dict(Counter(kind(sources) for sources in source_sets.values())),
        'reviewed_by_source_combination':dict(Counter(' + '.join(source_sets[key]) for key in reviewed_ids)),
        'reviewed_by_sensor_combination':dict(Counter(' + '.join(sensor_sets[key]) for key in reviewed_ids)),
        'reviewed_processing_kind':dict(Counter(kind(source_sets[key]) for key in reviewed_ids)),
        'satellites':dict(Counter(row.get('satellite','unknown') for row in real.values())),
        'instruments':dict(Counter(row.get('instrument','unknown') for row in real.values())),
        'class_counts':class_counts,'eligible_class_counts':eligible_classes,'class_sensor_matrix':matrix,'reviewed_split_groups':len(groups),
        'regions':dict(Counter(row.get('acquisition_query',{}).get('region','unrecorded') for row in real.values())),
        'missingness':{'all':profile(list(real_events)), 'by_source':{source:profile([key for key,sources in source_sets.items() if source in sources]) for source in inventory},
            'by_sensor':{family:profile([key for key,sensors in sensor_sets.items() if family in sensors]) for family in ('SNPP','NOAA20','NOAA21','MODIS')},
            'by_class':{label:profile([key for key in reviewed_ids if reviewed[key].get('label')==label]) for label in CLASSES}},
        'cross_sensor_events':sum(e.get('sensor_summary',{}).get('cross_sensor_confirmed',False) for e in evidence.values()),
        'reviewed_cross_sensor_events':sum(evidence.get(key,{}).get('sensor_summary',{}).get('cross_sensor_confirmed',False) for key in reviewed_ids),
        'quality':issues,'MODEL_V2_READY':not reasons,'readiness_reasons':reasons,
        'stage_targets':{'A':100,'B':200,'C':'300–500','per_class_minimum':30,'per_class_preferred':50},
        'notes':['Reviewed-claimed counts retain existing human labels; V2 eligibility additionally requires a timestamp and current evidence.',
                 'Source/sensor counts are overlapping event membership, not extra labeled samples.',
                 'NRT/SP equivalents are retained as representations; independent sensor confirmation excludes those copies.',
                 'Five-kilometre site collisions are conservative review flags, not automatic facility identity or group assignments.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, default=ml.CANDIDATES)
    parser.add_argument('--v2', action='store_true')
    parser.add_argument('--reconcile-sources', action='store_true')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.v2 or args.reconcile_sources:
            import json
            result = reconcile_legacy(args.apply) if args.reconcile_sources else model_v2_report(args.candidates)
            print(json.dumps(result, indent=2))
        else:
            print(render_progress(review_progress(args.candidates)))
        return 0  # A valid progress report is successful even when not training-ready.
    except (ValueError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
