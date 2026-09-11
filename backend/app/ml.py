import csv
from .review_validation import valid_source_reference
import json
import math
from pathlib import Path
from datetime import datetime, timezone
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
from .intelligence import FEATURES, FEATURE_VERSION, CLASSES, features
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data'/'reviewed_labels.csv'
CANDIDATES=ROOT/'data'/'review_candidates.csv'
ARTIFACT=ROOT/'models'/'classifier.joblib'
META=ROOT/'models'/'metadata.json'

# Review data contract.
# REVIEW_META: human-owned columns (never derived by code).
# ASSISTANCE_COLUMNS: reviewer-assistance context only; must never become
# training features (kept disjoint from FEATURES; verified in tests).
# TRAINING_COLUMNS: exactly what the training pipeline reads.
REVIEW_META=['event_id','split_group','label','reviewed','reviewer','source_reference','is_demo']
ASSISTANCE_COLUMNS=['latitude','longitude','start_time','last_seen_time','landuse_class','osm_context_available','satellite_context_available','abnormality_score','abnormality_status','risk_score','risk_level','nearby_facility_names']
TRAINING_COLUMNS=REVIEW_META+FEATURES

def dataset(path=None):
    data=Path(path) if path else DATA
    if not data.exists(): return []
    with data.open() as file: rows=list(csv.DictReader(file))
    eligible=[]
    for row in rows:
        if row.get('is_demo','').lower()!='false' or row.get('reviewed','').lower()!='true' or row.get('label') not in CLASSES or not row.get('event_id') or not row.get('reviewer') or not row.get('source_reference') or not row.get('split_group'): continue
        if not valid_source_reference(row.get("source_reference")): continue
        if any(not row.get(k, "").strip() or row[k] != row[k].strip() for k in ("event_id", "reviewer", "split_group")): continue
        try:
            row.update({key:float(row[key]) if row.get(key) else None for key in FEATURES})
            if not any(row[k] is not None for k in FEATURES): continue
            if any(row[k] is not None and not math.isfinite(row[k]) for k in FEATURES): continue
        except ValueError: continue
        eligible.append(row)
    ids=[r['event_id'] for r in eligible]
    if len(ids)!=len(set(ids)): raise ValueError('Training requires one reviewed feature row per event')
    return eligible

def candidate_row(event):
    """One deterministic review-candidate row from an event payload.

    Human-review fields are always emitted empty/false; only humans fill
    them. Assistance columns carry context for the reviewer and are
    disjoint from FEATURES, so they can never become training inputs.
    """
    features=event.get('features') or {}
    context=event.get('context') or {}
    history=event.get('history') or {}
    risk=event.get('risk') or {}
    abnormality=risk.get('abnormality') or {}
    facilities=[f.get('name') for f in (context.get('facilities') or []) if f.get('name')]
    row={key:'' for key in REVIEW_META}
    row.update({
        'event_id':event.get('id'),
        'reviewed':'false',
        'is_demo':str(bool(event.get('is_demo',False))).lower(),
        **{name:features.get(name) for name in FEATURES},
        'latitude':event.get('latitude'),
        'longitude':event.get('longitude'),
        'start_time':event.get('start_time'),
        'last_seen_time':event.get('last_seen_time'),
        'landuse_class':context.get('landuse_class'),
        'osm_context_available':str(bool(context.get('osm_context_available'))).lower() if context.get('osm_context_available') is not None else '',
        'satellite_context_available':str(bool(context.get('satellite_context_available'))).lower() if context.get('satellite_context_available') is not None else '',
        'abnormality_score':abnormality.get('abnormality_score'),
        'abnormality_status':abnormality.get('abnormality_status'),
        'risk_score':risk.get('risk_score'),
        'risk_level':risk.get('risk_level'),
        'nearby_facility_names':('; '.join(sorted(set(str(n) for n in facilities))) or '') if facilities else '',
    })
    return row

def readiness(rows):
    """Single source of truth for the training gate (mirrors status())."""
    labels=set(r['label'] for r in rows); groups=set(r['split_group'] for r in rows)
    missing=([f'{30-len(rows)} more reviewed events'] if len(rows)<30 else [])+[c for c in CLASSES if c not in labels]+([f'{10-len(groups)} more independent split groups'] if len(groups)<10 else [])
    return dict(eligible_rows=len(rows),classes_present=len(labels),classes_total=len(CLASSES),split_groups=len(groups),training_ready=len(rows)>=30 and len(labels)==len(CLASSES) and len(groups)>=10,missing=missing)

def candidate_report(path=None):
    """Validate a review-candidates CSV against the training contract.

    Read-only: reports problems, never assigns labels or review fields.
    Eligibility uses exactly the same rules as dataset().
    """
    data=Path(path) if path else CANDIDATES
    empty=dict(candidates_file=False,reviewed_rows=0,eligible_rows=0,classes_present=0,classes_total=len(CLASSES),split_groups=0,training_ready=False,missing=['Run export_review_candidates.py to create data/review_candidates.csv'],problems=['Review candidates file does not exist'],feature_columns_missing=[],extra_columns_ignored=[])
    if not data.exists(): return empty
    with data.open(newline='') as file:
        reader=csv.DictReader(file); header=list(reader.fieldnames or []); rows=list(reader)
    problems=[]; seen={}; multi_group=set(); invalid_reviewed=0; invalid_labels=set(); incomplete=[]; demo_reviewed=[]; reviewed_rows=0
    for row in rows:
        event_id=(row.get('event_id') or '').strip()
        reviewed=(row.get('reviewed') or '').strip().lower()
        if event_id:
            if event_id in seen:
                problems.append(f'Duplicate event_id: {event_id}')
                if seen[event_id]!=(row.get('split_group') or '').strip(): multi_group.add(event_id)
            seen[event_id]=(row.get('split_group') or '').strip()
        if reviewed and reviewed not in ('true','false'): invalid_reviewed+=1
        label=(row.get('label') or '').strip()
        if label and label not in CLASSES: invalid_labels.add(f'{event_id or "?"}: {label}')
        if reviewed=='true':
            reviewed_rows+=1
            if not valid_source_reference(row.get('source_reference')):
                incomplete.append(f'{event_id or "?"}: invalid or placeholder source_reference')
            if not event_id: incomplete.append('Reviewed row with empty event_id')
            for field in ('split_group','reviewer','source_reference'):
                if not (row.get(field) or '').strip(): incomplete.append(f'{event_id or "?"}: missing {field}')
            if (row.get('is_demo') or '').strip().lower()!='false': demo_reviewed.append(event_id or '?')
    if invalid_reviewed: problems.append(f'{invalid_reviewed} row(s) with invalid reviewed value (use true/false)')
    problems+=sorted(invalid_labels)
    if multi_group: problems.append('Event appears in multiple split groups: '+', '.join(sorted(multi_group)))
    if demo_reviewed: problems.append('Reviewed rows with is_demo=true (must be false): '+', '.join(sorted(demo_reviewed)))
    problems+=incomplete
    try: eligible=dataset(data); dataset_error=None
    except ValueError as exc: eligible=[]; dataset_error=str(exc)
    if dataset_error: problems.append(dataset_error)
    missing_meta=[c for c in REVIEW_META if c not in header]
    missing_features=[c for c in FEATURES if c not in header]
    if missing_meta: problems.append('Missing review columns: '+', '.join(missing_meta))
    if missing_features: problems.append('Missing feature columns required by ml.py: '+', '.join(missing_features))
    extra=[c for c in header if c not in FEATURES and c not in REVIEW_META]
    summary=readiness(eligible)
    return dict(candidates_file=True,reviewed_rows=reviewed_rows,**summary,problems=problems,feature_columns_missing=missing_features,extra_columns_ignored=extra)

def status():
    try: rows=dataset(); error=None
    except ValueError as exc: rows=[];error=str(exc)
    ready=readiness(rows)['training_ready']
    meta=json.loads(META.read_text()) if META.exists() and ARTIFACT.exists() else {}
    return dict(training_ready=ready,model_available=bool(meta) and meta.get('features')==FEATURES and meta.get('feature_version')==FEATURE_VERSION,model_version=meta.get('model_version'),eligible_labeled_rows=len(rows),reason=error or ('Dataset eligible; split coverage checked during training' if ready else 'Need at least 30 reviewed non-demo events, all five classes and 10 independent split groups'),feature_version=FEATURE_VERSION)

def train():
    if not status()['training_ready']: raise ValueError(status()['reason'])
    rows=dataset(); X=np.array([features(r) for r in rows]); y=np.array([r['label'] for r in rows]); groups=np.array([r['split_group'] for r in rows])
    a,test=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42).split(X,y,groups))
    tr,va=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=17).split(X[a],y[a],groups[a])); tr,va=a[tr],a[va]
    if any(set(y[index])!=set(CLASSES) for index in (tr,va,test)): raise ValueError('Independent train/validation/test splits must each contain every class; supply more reviewed groups')
    model=make_pipeline(SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True),RandomForestClassifier(n_estimators=200,class_weight='balanced',random_state=42,n_jobs=1))
    model.fit(X[tr],y[tr])
    def evaluate(index):
        prediction=model.predict(X[index]); p,r,f,_=precision_recall_fscore_support(y[index],prediction,average='macro',zero_division=0)
        return dict(accuracy=accuracy_score(y[index],prediction),balanced_accuracy=balanced_accuracy_score(y[index],prediction),macro_precision=p,macro_recall=r,macro_f1=f,per_class=classification_report(y[index],prediction,output_dict=True,zero_division=0),confusion_matrix=confusion_matrix(y[index],prediction,labels=CLASSES).tolist())
    meta=dict(model_version=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),feature_version=FEATURE_VERSION,features=FEATURES,classes=CLASSES,validation=evaluate(va),test=evaluate(test),split_counts={'train':len(tr),'validation':len(va),'test':len(test)})
    ARTIFACT.parent.mkdir(exist_ok=True);joblib.dump(model,ARTIFACT);META.write_text(json.dumps(meta,indent=2));return meta

def predict(event):
    if not ARTIFACT.exists() or not META.exists(): return dict(predicted_class=None,class_probabilities=None,classification_confidence=None,model_version=None,feature_version=FEATURE_VERSION,reason='No model trained on reviewed observations')
    metadata=json.loads(META.read_text())
    if metadata.get('features')!=FEATURES or metadata.get('feature_version')!=FEATURE_VERSION:
        return dict(predicted_class=None,class_probabilities=None,classification_confidence=None,model_version=None,feature_version=FEATURE_VERSION,reason='Trained feature schema incompatible; retraining required')
    model=joblib.load(ARTIFACT); probs=model.predict_proba([features(event)])[0]; mapping=dict(zip(model.classes_,map(float,probs)))
    return dict(predicted_class=max(mapping,key=mapping.get),class_probabilities=mapping,classification_confidence=max(mapping.values()),model_version=json.loads(META.read_text())['model_version'],feature_version=FEATURE_VERSION)
