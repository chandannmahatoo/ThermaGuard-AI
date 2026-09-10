import csv
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
ARTIFACT=ROOT/'models'/'classifier.joblib'
META=ROOT/'models'/'metadata.json'

def dataset():
    if not DATA.exists(): return []
    with DATA.open() as file: rows=list(csv.DictReader(file))
    eligible=[]
    for row in rows:
        if row.get('is_demo','').lower()!='false' or row.get('reviewed','').lower()!='true' or row.get('label') not in CLASSES or not row.get('event_id') or not row.get('reviewer') or not row.get('source_reference') or not row.get('split_group'): continue
        try:
            row.update({key:float(row[key]) if row.get(key) else None for key in FEATURES})
            if not any(row[k] is not None for k in FEATURES): continue
            if any(row[k] is not None and not math.isfinite(row[k]) for k in FEATURES): continue
        except ValueError: continue
        eligible.append(row)
    ids=[r['event_id'] for r in eligible]
    if len(ids)!=len(set(ids)): raise ValueError('Training requires one reviewed feature row per event')
    return eligible

def status():
    try: rows=dataset(); error=None
    except ValueError as exc: rows=[];error=str(exc)
    ready=len(rows)>=30 and len(set(r['label'] for r in rows))==len(CLASSES) and len(set(r['split_group'] for r in rows))>=10
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
