"""One deterministic event, feature, baseline and decision-support pipeline."""
import hashlib
import math
import statistics
from datetime import datetime, timezone
from pyproj import Geod
from .config import settings

GEOD = Geod(ellps='WGS84')
FEATURE_VERSION = '2'
FEATURES = ['mean_frp','max_frp','mean_brightness','max_brightness','quality_mean','duration_hours','detection_count','night_fraction','spatial_spread_km','persistence_days','detection_frequency','recurrence_count','historical_mean_frp','historical_max_frp','historical_std_frp','historical_baseline_available','distance_to_industrial_m','distance_to_refinery_m','distance_to_powerplant_m','distance_to_factory_m','distance_to_forest_m','distance_to_farmland_m','distance_to_residential_m','nearby_industrial_count','nearby_facility_count','ndvi','vegetation_fraction','built_up_fraction','landuse_industrial','landuse_forest','landuse_farmland']
CLASSES = ['industrial_fire', 'persistent_industrial_thermal_source', 'agricultural_vegetation_fire', 'natural_thermal_event', 'possible_false_positive']
def distance(a, b):
    return GEOD.inv(a['longitude'], a['latitude'], b['longitude'], b['latitude'])[2] / 1000

def validate(row, is_demo=False):
    lat, lon = float(row['latitude']), float(row['longitude'])
    if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Invalid coordinates')
    observed = datetime.strptime(f"{row['acq_date']} {str(row['acq_time']).zfill(4)}", '%Y-%m-%d %H%M').replace(tzinfo=timezone.utc)
    frp = float(row['frp'])
    brightness = float(row.get('bright_ti4') or row.get('brightness'))
    if not all(math.isfinite(v) and v >= 0 for v in (frp, brightness)): raise ValueError('Invalid thermal value')
    identity = '|'.join(str(row.get(k,'')) for k in ['latitude','longitude','acq_date','acq_time','satellite','instrument'])
    source_id = hashlib.sha256(identity.encode()).hexdigest()[:20]
    return dict(id=('demo-' if is_demo else 'firms-') + source_id, source='deterministic_fixture' if is_demo else 'NASA FIRMS', source_id=source_id, provider='demo' if is_demo else 'NASA', processing_version='1', retrieved_at=datetime.now(timezone.utc).isoformat(), observed_at=observed.isoformat(), latitude=lat, longitude=lon, frp=frp, brightness=brightness, confidence=row.get('confidence'), satellite=row.get('satellite'), instrument=row.get('instrument'), day_night=row.get('daynight','U'), is_demo=is_demo, raw=row)

def quality(row):
    value=str(row.get('confidence') or '').lower()
    if value in {'l','n','h'}:return {'l':0.,'n':.5,'h':1.}[value]
    try:
        number=float(value)
        return number/100 if math.isfinite(number) and 0<=number<=100 else None
    except ValueError:return None

def cluster(rows):
    rows = sorted({r['id']:r for r in rows}.values(), key=lambda r:(r['observed_at'],r['id']))
    parents = list(range(len(rows)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]; i = parents[i]
        return i
    for i,a in enumerate(rows):
        for j in range(i):
            b=rows[j]
            if a['is_demo'] == b['is_demo'] and abs((datetime.fromisoformat(a['observed_at'])-datetime.fromisoformat(b['observed_at'])).total_seconds()) <= settings.event_cluster_time_hours*3600 and distance(a,b) <= settings.event_cluster_radius_km:
                parents[root(i)] = root(j)
    groups={}
    for i,row in enumerate(rows): groups.setdefault(root(i),[]).append(row)
    events=[]
    for group in groups.values():
        first,last=group[0],group[-1]
        center=dict(latitude=sum(r['latitude'] for r in group)/len(group),longitude=sum(r['longitude'] for r in group)/len(group))
        qualities=[quality(r) for r in group if quality(r) is not None]
        events.append(dict(quality_mean=sum(qualities)/len(qualities) if qualities else None,id='TG-'+first['id'], **center, is_demo=first['is_demo'], start_time=first['observed_at'],last_seen_time=last['observed_at'],duration_hours=(datetime.fromisoformat(last['observed_at'])-datetime.fromisoformat(first['observed_at'])).total_seconds()/3600,detection_count=len(group),mean_frp=sum(r['frp'] for r in group)/len(group),max_frp=max(r['frp'] for r in group),mean_brightness=sum(r['brightness'] for r in group)/len(group),max_brightness=max(r['brightness'] for r in group),spatial_spread_km=max(distance(center,r) for r in group),night_fraction=sum(r['day_night']=='N' for r in group)/len(group),day_detection_count=sum(r['day_night']=='D' for r in group),night_detection_count=sum(r['day_night']=='N' for r in group),persistence_days=len(set(r['observed_at'][:10] for r in group)),detection_ids=[r['id'] for r in group],status='monitoring'))
    return events

def features(event):
    merged={**event,**event.get('context',{}),**event.get('history',{})}
    if 'context' in event:
        landuse=event['context'].get('landuse_class')
        merged.update({f'landuse_{kind}':float(landuse==kind) if landuse else None for kind in ['industrial','forest','farmland']})
    return [float(merged[k]) if merged.get(k) is not None else float('nan') for k in FEATURES]

def historical_context(event, historical):
    earlier=[e for e in historical if e['is_demo']==event['is_demo'] and e['last_seen_time'] < event['start_time'] and distance(e,event)<=settings.event_cluster_radius_km]
    means=[e['mean_frp'] for e in earlier]
    def mean(key):return statistics.mean(e[key] for e in earlier) if earlier else None
    return dict(historical_baseline_available=bool(earlier),recurrence_count=len(earlier),historical_mean_frp=statistics.mean(means) if means else None,historical_max_frp=max((e['max_frp'] for e in earlier),default=None),historical_std_frp=statistics.pstdev(means) if means else None,historical_mean_brightness=mean('mean_brightness'),historical_mean_spread_km=mean('spatial_spread_km'),historical_mean_duration_hours=mean('duration_hours'),historical_mean_frequency=statistics.mean(e['detection_count']/max(e['duration_hours'],1) for e in earlier) if earlier else None,detection_frequency=event['detection_count']/max(event['duration_hours'],1),time_of_day_pattern='night_dominant' if event['night_fraction']>.5 else 'day_dominant' if event['night_fraction']<.5 else 'mixed')

def assess(event, historical):
    history=event.get('history') or historical_context(event,historical)
    comparisons={'frp':('mean_frp','historical_mean_frp'),'brightness':('mean_brightness','historical_mean_brightness'),'spatial_spread':('spatial_spread_km','historical_mean_spread_km'),'persistence':('duration_hours','historical_mean_duration_hours')}
    ratios={f'{name}_ratio':event[current]/history[baseline] if history.get(baseline) else None for name,(current,baseline) in comparisons.items()}
    ratios['frequency_ratio']=history['detection_frequency']/history['historical_mean_frequency'] if history.get('historical_mean_frequency') else None
    known=[value for value in ratios.values() if value is not None]
    deviation=min(100,max(0,(max(known)-1)*50)) if known else None
    abnormality=dict(baseline_available=history['historical_baseline_available'],abnormality_score=deviation,abnormality_status=('above_baseline' if max(known)>1.5 else 'within_baseline') if known else 'unavailable',explanation_features={**ratios,'historical_event_count':history['recurrence_count']},historical_mean_frp=history['historical_mean_frp'])
    context=event.get('context',{})
    def nearby(key):return context.get(key) is not None and context[key]<1000
    components={'thermal_severity':min(1,event['max_frp']/140),'persistence':min(1,event['duration_hours']/20),'industrial_proximity':float(nearby('distance_to_industrial_m')),'residential_proximity':float(nearby('distance_to_residential_m')),'infrastructure_exposure':float(nearby('distance_to_powerplant_m') or nearby('distance_to_refinery_m')),'classification_context':float(event.get('classification',{}).get('predicted_class')=='industrial_fire'),'historical_abnormality':(deviation or 0)/100}
    factors={key:value*max(0,settings.risk_weights.get(key,0)) for key,value in components.items()}
    score=round(min(100,sum(factors.values())))
    return dict(risk_score=score,risk_level='Normal' if score<=30 else 'Medium' if score<=60 else 'High' if score<=80 else 'Critical',risk_factors=factors,method='Configurable decision-support scoring model; not scientifically validated',missing_context=[k for k in ['distance_to_industrial_m','distance_to_residential_m','ndvi'] if context.get(k) is None],abnormality=abnormality)
