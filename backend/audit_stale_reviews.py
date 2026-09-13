"""Read-only review/data-integrity audit. Never edits CSVs, DB, labels or models."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from sqlalchemy import select
from app import ml
from app.database import Session, Event, Detection
from app.intelligence import cluster, historical_context, assess, FEATURES, features, observation_identity
from app.review_evidence import changes, evidence_hash
from review_common import read_csv, reviewed_errors


def audit(path=None, session_factory=None, sync_plan=False):
    path = Path(path or ml.CANDIDATES)
    columns, rows, original = read_csv(path)
    with (session_factory or Session)() as db:
        events = {e.id:e.payload for e in db.scalars(select(Event).where(Event.is_demo.is_(False)))}
        detections = {d.id:d.payload for d in db.scalars(select(Detection).where(Detection.is_demo.is_(False)))}
    reviewed = [r for r in rows if r.get('reviewed','').strip().lower()=='true']
    queue=[]
    for row in reviewed:
        fresh = ml.candidate_row(events[row['event_id']]) if row['event_id'] in events else None
        difference = changes(row, fresh) if fresh else {'material':['event_missing_or_reclustered'], 'non_material':[], 'uncaptured_fields':[]}
        errors = reviewed_errors(row, require_timestamp=True)
        queue.append({'event_id':row['event_id'], 'label':row.get('label'), 'split_group':row.get('split_group'),
                      'material_fields':difference['material'], 'non_material_fields':difference['non_material'],
                      'uncaptured_fields':difference['uncaptured_fields'], 'metadata_errors':errors,
                      'evidence_hash':evidence_hash(row),
                      'status':'materially_stale' if difference['material'] else 'invalid_metadata' if errors else 'non_materially_changed' if difference['non_material'] else 'valid'})
    valid = [r for r in queue if not r['material_fields'] and not r['metadata_errors']]
    group_by_id={r['event_id']:r.get('split_group') for r in reviewed}
    owners={}
    missing_refs=[]
    for identity,event in events.items():
        if identity not in group_by_id:continue
        for detection_id in event.get('detection_ids',[]):
            if detection_id not in detections:
                missing_refs.append({'event_id':identity,'detection_id':detection_id});continue
            row=detections[detection_id]
            satellite={'1':'N20','2':'N21','Aqua':'A','Terra':'T'}.get(str(row.get('satellite')),row.get('satellite'))
            key=observation_identity({**row,'satellite':satellite})
            owners.setdefault(key,set()).add(identity)
    leaks=[sorted(ids) for ids in owners.values() if len({group_by_id[k] for k in ids})>1]
    hashes=Counter(evidence_hash(row) for row in reviewed)
    result={'dry_run':True,'file':str(path),'total_rows':len(rows),'total_reviewed':len(reviewed),
        'still_valid':sum(r['status']=='valid' for r in queue),
        'materially_stale':sum(bool(r['material_fields']) for r in queue),
        'non_materially_changed':sum(not r['material_fields'] and bool(r['non_material_fields']) for r in queue),
        'invalid_review_metadata':sum(bool(r['metadata_errors']) for r in queue),
        'eligible_current_evidence_and_timestamp':len(valid),
        'exclusion_reasons':dict(Counter(reason for r in queue for reason in r['metadata_errors']+(['Material evidence changed'] if r['material_fields'] else []))),
        'class_counts':dict(Counter(r.get('label') for r in reviewed)),
        'eligible_class_counts':dict(Counter(r['label'] for r in valid)),
        'split_groups':len({r.get('split_group') for r in reviewed}),
        'duplicate_event_ids':[], # read_csv rejects duplicates, never silently drops them.
        'duplicate_evidence_signature_groups':sum(n>1 for n in hashes.values()),
        'demo_reviewed_rows':sum(r.get('is_demo','').lower()!='false' for r in reviewed),
        'missing_feature_columns':[key for key in FEATURES if key not in columns],
        'blank_features':dict(Counter(key for r in reviewed for key in FEATURES if r.get(key) in ('',None))),
        'cross_group_shared_observations':leaks,'missing_detection_references':missing_refs,
        'inventory':{'real_events':len(events),'real_detections':len(detections),
                     'sources':dict(Counter(d.get('source_dataset') or 'unknown' for d in detections.values())),
                     'sensors':dict(Counter(d.get('instrument') or 'unknown' for d in detections.values())),
                     'day_night':dict(Counter(d.get('day_night') or 'unknown' for d in detections.values())),
                     'acquisition_regions':dict(Counter(d.get('acquisition_query',{}).get('region') or 'unrecorded' for d in detections.values())),
                     'event_regions':dict(Counter(e.get('context',{}).get('location',{}).get('state') or 'unavailable' for e in events.values()))},
        'review_queue':queue}
    if sync_plan:
        rebuilt=cluster(list(detections.values()))
        differences=Counter();changed=0
        for event in rebuilt:
            previous=events.get(event['id'])
            if previous is None:continue
            event['context']=previous.get('context',{})
            event['history']=historical_context(event,rebuilt)
            event['classification']=ml.predict(event)
            event['risk']=assess(event,rebuilt)
            event['features']={key:None if value!=value else value for key,value in zip(FEATURES,features(event))}
            keys=[key for key in set(event)|set(previous) if event.get(key)!=previous.get(key)]
            changed+=bool(keys);differences.update(keys)
        result['no_network_rebuild']={'new_detections':0,'rebuilt_events':len(rebuilt),'updated_existing':changed,
            'changed_top_level_fields':dict(differences),'new_event_ids':sorted({e['id'] for e in rebuilt}-set(events)),
            'retired_event_ids':sorted(set(events)-{e['id'] for e in rebuilt}),
            'note':'Provider refreshes intentionally excluded. No persistence or notification dispatch.'}
    if path.read_bytes()!=original:raise ValueError('CSV changed during audit; retry for a consistent report')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates',type=Path,default=ml.CANDIDATES)
    parser.add_argument('--sync-plan',action='store_true',help='Read-only full rebuild without provider calls (may be slow)')
    args=parser.parse_args()
    try: print(json.dumps(audit(args.candidates,sync_plan=args.sync_plan),indent=2))
    except (ValueError,OSError) as error:
        parser.exit(1,f'Audit refused: {error}\n')

if __name__=='__main__':main()
