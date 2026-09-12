from __future__ import annotations

from itertools import product
import csv
import json
import math
import re
from pathlib import Path
from datetime import datetime, timezone
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix
from .intelligence import FEATURES, FEATURE_VERSION, CLASSES, features, V2_SENSOR_FIELDS
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
SENSOR_COLUMNS = ['source_counts', 'sensor_provenance', 'viirs_detection_count', 'modis_detection_count',
    'unique_satellite_count', 'unique_sensor_count', 'viirs_primary_mean', 'viirs_secondary_mean',
    'modis_primary_mean', 'modis_secondary_mean', 'scan_mean', 'track_mean']
SENSOR_COLUMNS += V2_SENSOR_FIELDS
ASSISTANCE_COLUMNS += SENSOR_COLUMNS
TRAINING_COLUMNS=REVIEW_META+FEATURES

def valid_source_reference(value):
    if not isinstance(value, str) or value != value.strip() or len(value.strip()) < 8:
        return False
    normalized = re.sub(r'[^a-z0-9]+', ' ', value.casefold()).strip()
    placeholders = {'real source or evidence here', 'your verified evidence source',
                    'todo', 'tbd', 'test', 'placeholder', 'n a', 'na', 'none', 'null',
                    'unknown', 'source', 'evidence', 'not available'}
    return (normalized not in placeholders
            and not re.search(r'\b(todo|tbd|placeholder)\b', normalized)
            and not normalized.startswith(('test only', 'real source or evidence here',
                                           'your verified evidence source'))
            and len(set(normalized.replace(' ', ''))) >= 4)


def valid_review_timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return stamp.tzinfo is not None and stamp <= datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False


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
    row.update({key: event.get('sensor_summary', {}).get(key) for key in SENSOR_COLUMNS})
    row['source_counts'] = json.dumps(event.get('source_counts', {}), sort_keys=True)
    row['sensor_provenance'] = json.dumps(event.get('sensor_provenance', []), sort_keys=True)
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

def _find_valid_group_split(y, groups):
    """Find a deterministic leakage-safe train/validation/test group split.

    Whole split_group cohorts stay together. Every split must contain every
    class in CLASSES. Among valid assignments, prefer a split closest to
    60/20/20 by row count.
    """
    required_classes = set(CLASSES)
    unique_groups = sorted(set(groups.tolist()))

    if len(unique_groups) < 3:
        raise ValueError(
            "At least three independent groups are required for "
            "train, validation and test splitting"
        )

    group_indices = {
        group: np.where(groups == group)[0]
        for group in unique_groups
    }
    group_labels = {
        group: set(y[group_indices[group]].tolist())
        for group in unique_groups
    }

    # Quick feasibility check: each class must occur in at least three
    # independent groups, otherwise three disjoint splits cannot all contain it.
    class_group_counts = {
        class_name: sum(
            class_name in group_labels[group]
            for group in unique_groups
        )
        for class_name in CLASSES
    }
    insufficient = {
        class_name: count
        for class_name, count in class_group_counts.items()
        if count < 3
    }
    if insufficient:
        details = ", ".join(
            f"{name}={count}"
            for name, count in sorted(insufficient.items())
        )
        raise ValueError(
            "No leakage-safe 3-way split is possible because some classes "
            f"occur in fewer than three independent groups: {details}"
        )

    total_rows = len(y)
    target_train = total_rows * 0.60
    target_validation = total_rows * 0.20
    target_test = total_rows * 0.20

    best_split = None
    best_score = None

    # 0=train, 1=validation, 2=test.
    # The current dataset has 13 groups, so exhaustive search is manageable.
    for assignment in product((0, 1, 2), repeat=len(unique_groups)):
        if 0 not in assignment or 1 not in assignment or 2 not in assignment:
            continue

        train_groups = [
            unique_groups[i]
            for i, split_id in enumerate(assignment)
            if split_id == 0
        ]
        validation_groups = [
            unique_groups[i]
            for i, split_id in enumerate(assignment)
            if split_id == 1
        ]
        test_groups = [
            unique_groups[i]
            for i, split_id in enumerate(assignment)
            if split_id == 2
        ]

        train_labels = set().union(*(group_labels[g] for g in train_groups))
        validation_labels = set().union(
            *(group_labels[g] for g in validation_groups)
        )
        test_labels = set().union(*(group_labels[g] for g in test_groups))

        if train_labels != required_classes:
            continue
        if validation_labels != required_classes:
            continue
        if test_labels != required_classes:
            continue

        tr = np.concatenate([group_indices[g] for g in train_groups])
        va = np.concatenate([group_indices[g] for g in validation_groups])
        test = np.concatenate([group_indices[g] for g in test_groups])

        score = (
            abs(len(tr) - target_train)
            + abs(len(va) - target_validation)
            + abs(len(test) - target_test)
        )

        # Deterministic tie-breaking comes from sorted groups + product order.
        if best_score is None or score < best_score:
            best_score = score
            best_split = {
                "train_indices": tr,
                "validation_indices": va,
                "test_indices": test,
                "train_groups": train_groups,
                "validation_groups": validation_groups,
                "test_groups": test_groups,
                "score": float(score),
            }

    if best_split is None:
        raise ValueError(
            "No leakage-safe train/validation/test group partition contains "
            "every class in every split. Add more independently reviewed groups."
        )

    return best_split


def train():
    current_status = status()
    if not current_status["training_ready"]:
        raise ValueError(current_status["reason"])

    rows = dataset()
    X = np.array([features(r) for r in rows])
    y = np.array([r["label"] for r in rows])
    groups = np.array([r["split_group"] for r in rows])

    split = _find_valid_group_split(y, groups)
    tr = split["train_indices"]
    va = split["validation_indices"]
    test = split["test_indices"]

    required_classes = set(CLASSES)
    for split_name, index in (
        ("train", tr),
        ("validation", va),
        ("test", test),
    ):
        if set(y[index]) != required_classes:
            raise ValueError(
                f"{split_name} split does not contain every required class"
            )

    model = make_pipeline(
        SimpleImputer(
            strategy="median",
            add_indicator=True,
            keep_empty_features=True,
        ),
        RandomForestClassifier(
            n_estimators=200,
            class_weight="balanced",
            random_state=42,
            n_jobs=1,
        ),
    )
    model.fit(X[tr], y[tr])

    def evaluate(index):
        truth = y[index]
        prediction = model.predict(X[index])
        p, r, f, _ = precision_recall_fscore_support(
            truth,
            prediction,
            average="macro",
            zero_division=0,
        )
        return dict(
            rows=int(len(index)),
            accuracy=float(accuracy_score(truth, prediction)),
            balanced_accuracy=float(
                balanced_accuracy_score(truth, prediction)
            ),
            macro_precision=float(p),
            macro_recall=float(r),
            macro_f1=float(f),
            per_class=classification_report(
                truth,
                prediction,
                labels=CLASSES,
                output_dict=True,
                zero_division=0,
            ),
            confusion_matrix=confusion_matrix(
                truth,
                prediction,
                labels=CLASSES,
            ).tolist(),
        )

    meta = dict(
        model_version=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        feature_version=FEATURE_VERSION,
        features=FEATURES,
        classes=CLASSES,
        algorithm="RandomForestClassifier",
        n_estimators=200,
        class_weight="balanced",
        random_state=42,
        training_rows=len(rows),
        validation=evaluate(va),
        test=evaluate(test),
        split_counts={
            "train": len(tr),
            "validation": len(va),
            "test": len(test),
        },
        split_groups={
            "train": split["train_groups"],
            "validation": split["validation_groups"],
            "test": split["test_groups"],
        },
        split_class_distribution={
            "train": {
                class_name: int(np.sum(y[tr] == class_name))
                for class_name in CLASSES
            },
            "validation": {
                class_name: int(np.sum(y[va] == class_name))
                for class_name in CLASSES
            },
            "test": {
                class_name: int(np.sum(y[test] == class_name))
                for class_name in CLASSES
            },
        },
    )

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACT)
    META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta

def predict(event):
    if event.get('sensor_summary', {}).get('modis_detection_count', 0):
        return dict(predicted_class=None, class_probabilities=None, classification_confidence=None,
            model_version=None, feature_version=FEATURE_VERSION,
            reason='Current reviewed model is not validated for MODIS or mixed-sensor events')
    if not ARTIFACT.exists() or not META.exists(): return dict(predicted_class=None,class_probabilities=None,classification_confidence=None,model_version=None,feature_version=FEATURE_VERSION,reason='No model trained on reviewed observations')
    metadata=json.loads(META.read_text())
    if metadata.get('features')!=FEATURES or metadata.get('feature_version')!=FEATURE_VERSION:
        return dict(predicted_class=None,class_probabilities=None,classification_confidence=None,model_version=None,feature_version=FEATURE_VERSION,reason='Trained feature schema incompatible; retraining required')
    model=joblib.load(ARTIFACT); probs=model.predict_proba([features(event)])[0]; mapping=dict(zip(model.classes_,map(float,probs)))
    return dict(predicted_class=max(mapping,key=mapping.get),class_probabilities=mapping,classification_confidence=max(mapping.values()),model_version=json.loads(META.read_text())['model_version'],feature_version=FEATURE_VERSION)
