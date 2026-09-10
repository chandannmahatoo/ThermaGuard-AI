import asyncio
import csv
from pathlib import Path
import pytest
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import main, ml, providers
from app.config import REQUIRED_RISK_WEIGHT_KEYS
from app.database import Base,get_db,Detection,Event,Organization,AreaAssignment,User,Alert
from app.intelligence import validate,cluster,features,assess,FEATURES
from app.security import hash_password

@pytest.fixture
def client(monkeypatch):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    factory=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(main,'engine',engine);monkeypatch.setattr(main,'Session',factory)
    def db():
        with factory() as session:yield session
    main.app.dependency_overrides[get_db]=db
    with TestClient(main.app) as c:yield c,factory
    main.app.dependency_overrides.clear()

def auth(c,operator=False):
    response=c.post('/api/v1/auth/login',json={'email':('operator' if operator else 'admin')+'@demo.thermaguard.local','password':'DemoTherma2026!'})
    assert response.status_code==200
    return {'Authorization':'Bearer '+response.json()['access_token']}

def row(**kwargs):
    return dict(latitude='22',longitude='70',acq_date='2026-09-10',acq_time='0100',frp='100',bright_ti4='340',satellite='test',instrument='VIIRS',**kwargs)

def test_validation():
    source=row(); result=validate(source)
    assert result['raw']==source and not result['is_demo'] and result['source']=='NASA FIRMS'
    for key,value in [('latitude','91'),('longitude','nan'),('frp','-1'),('acq_time','9999')]:
        with pytest.raises(ValueError):validate({**source,key:value})

def test_clustering_and_isolation():
    a=validate(row());b=validate({**row(),'latitude':'22.001','acq_time':'0200'})
    assert len(cluster([a,b,a]))==1
    assert cluster([b,a])[0]['id']==cluster([a,b])[0]['id']
    assert len(cluster([a,validate(row(),True)]))==2
    assert len(cluster([a,validate({**row(),'acq_date':'2026-09-12'})]))==2

def test_features_risk_baseline():
    event=cluster([validate(row())])[0]
    assert len(features(event))==len(FEATURES)
    risk=assess(event,[])
    assert risk['risk_score']==36 and not risk['abnormality']['baseline_available']
    past={**event,'last_seen_time':'2026-09-01T00:00:00+00:00','mean_frp':20}
    assert assess(event,[past])['abnormality']['abnormality_status']=='above_baseline'

def test_health_login_model_gate(client):
    c,_=client
    assert c.get('/health').json()['status']=='ok'
    assert c.get('/api/v1/events').status_code==401
    h=auth(c)
    assert c.get('/api/v1/model/status',headers=h).json()['training_ready'] is False
    assert c.post('/api/v1/model/train',headers=h).status_code==409
    assert c.post('/api/v1/auth/login',json={'email':'admin@demo.thermaguard.local','password':'wrongpassword123'}).status_code==401

def test_pipeline_evidence_alerts(client):
    c,factory=client;h=auth(c)
    events=c.get('/api/v1/events',headers=h).json();assert len(events)==4
    first=events[0];assert first['is_demo'] and first['classification']['classification_confidence'] is None
    evidence=c.get(f"/api/v1/events/{first['id']}/evidence",headers=h).json()
    assert len(evidence['detected_facts'])==3
    assert evidence['risk_assessment']['risk_score']==60
    alerts=c.get('/api/v1/alerts',headers=h).json();assert len(alerts)==1
    assert c.post(f"/api/v1/alerts/{alerts[0]['id']}/acknowledge",headers=h).json()['status']=='acknowledged'
    with factory() as db:
        main.create_alerts(db,first);db.commit();assert len(list(db.scalars(select(Alert))))==1

def test_organization_scope(client):
    c,_=client;admin=auth(c);operator=auth(c,True)
    all_events=c.get('/api/v1/events',headers=admin).json();events=c.get('/api/v1/events',headers=operator).json()
    assert len(events)==2
    hidden=next(e for e in all_events if e not in events)
    for suffix in ['','/evidence','/risk','/history']:
        assert c.get('/api/v1/events/'+hidden['id']+suffix,headers=operator).status_code==404
    assert c.get('/api/v1/admin/organizations',headers=operator).status_code==403
    assert c.post('/api/v1/firms/sync',headers=operator,json={}).status_code==403
    assert c.post('/api/v1/copilot/chat',headers=operator,json={'question':'Explain','event_id':hidden['id']}).status_code==404

def test_registration_cannot_escalate(client):
    c,_=client
    c.post('/api/v1/auth/register',json={'email':'new@example.invalid','password':'longsecurepassword','role':'admin','organization_id':1})
    result=c.post('/api/v1/auth/login',json={'email':'new@example.invalid','password':'longsecurepassword'}).json()
    h={'Authorization':'Bearer '+result['access_token']}
    assert c.get('/api/v1/events',headers=h).json()==[]
    assert c.get('/api/v1/auth/me',headers=h).json()['role']=='organization'

def test_demo_sync_and_fallback(client,monkeypatch):
    c,_=client;h=auth(c)
    assert c.post('/api/v1/firms/sync',headers=h,json={}).status_code==409
    response=c.post('/api/v1/copilot/chat',headers=h,json={'question':'Why is the event risky?'})
    assert response.json()['mode']=='deterministic_fallback'
    assert 'DEMO DATA' in response.json()['answer']

def test_firms_mock(monkeypatch):
    monkeypatch.setattr(main.settings,'firms_map_key','test')
    original=httpx.AsyncClient
    def handler(request):
        return httpx.Response(200,text='latitude,longitude,acq_date,acq_time,frp,bright_ti4\n22,70,2026-09-10,0100,100,340\n999,70,2026-09-10,0100,100,340')
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    records,rejected=asyncio.run(providers.firms([68,6,98,38]))
    assert len(records)==1 and rejected==1 and not records[0]['is_demo']

def test_osm_mock_and_failure(monkeypatch):
    original=httpx.AsyncClient
    def handler(request):return httpx.Response(200,json={'elements':[{'type':'node','id':1,'lat':22,'lon':70,'tags':{'landuse':'industrial'}}]})
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    result=asyncio.run(providers.osm({'latitude':22,'longitude':70}))
    assert result['osm_context_available'] and result['distance_to_industrial_m']==0
    assert result['distance_to_forest_m'] is None
    def failure(request):return httpx.Response(503)
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(failure),**kw))
    assert not asyncio.run(providers.osm({'latitude':22,'longitude':70}))['osm_context_available']

def test_training_excludes_demo(tmp_path,monkeypatch):
    path=tmp_path/'labels.csv';monkeypatch.setattr(ml,'DATA',path)
    path.write_text('event_id,split_group,label,reviewed,reviewer,source_reference,is_demo,mean_frp\ne1,g1,industrial_fire,true,reviewer,test,true,100\n')
    assert ml.dataset()==[] and not ml.status()['training_ready']

def test_threshold_and_admin_bounds(client):
    c,_=client;h=auth(c);operator=auth(c,True)
    assert c.post('/api/v1/admin/threshold',headers=operator,json={'threshold':20}).status_code==403
    assert c.post('/api/v1/admin/threshold',headers=h,json={'threshold':101}).status_code==422
    assert c.post('/api/v1/admin/threshold',headers=h,json={'threshold':50}).json()['threshold']==50
    assert c.get('/api/v1/admin/threshold',headers=h).json()['threshold']==50
    assert c.post('/api/v1/admin/assignments',headers=h,json={'organization_id':1,'area_name':'Invalid','bounds':[90,20,70,30]}).status_code==422

def test_real_sync_route_mocked(client,monkeypatch):
    c,factory=client
    with factory() as db:
        db.add(User(email='real-admin@example.invalid',password=hash_password('realpassword123'),role='admin'));db.commit()
    token=c.post('/api/v1/auth/login',json={'email':'real-admin@example.invalid','password':'realpassword123'}).json()['access_token']
    h={'Authorization':'Bearer '+token}
    monkeypatch.setattr(main.settings,'demo_mode',False)
    async def fake_firms(bounds,days):return [validate(row())],0
    async def fake_osm(event):return {'osm_context_available':False}
    monkeypatch.setattr(providers,'firms',fake_firms);monkeypatch.setattr(providers,'osm',fake_osm)
    result=c.post('/api/v1/firms/sync',headers=h,json={})
    assert result.status_code==200 and result.json()['events']==1
    assert len(c.get('/api/v1/events',headers=h).json())==1
    assert c.post('/api/v1/auth/login',json={'email':'admin@demo.thermaguard.local','password':'DemoTherma2026!'}).status_code==401
    assert c.post('/api/v1/firms/sync',headers=h,json={}).json()['events']==1
    with factory() as db:assert len(list(db.scalars(select(Detection).where(Detection.is_demo==False))))==1

def test_ollama_down_retains_events(client,monkeypatch):
    c,_=client;h=auth(c)
    monkeypatch.setattr(main.settings,'ollama_enabled',True);monkeypatch.setattr(main.settings,'ollama_model','test')
    original=httpx.AsyncClient
    def failure(request):return httpx.Response(503)
    monkeypatch.setattr(main.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(failure),**kw))
    assert c.post('/api/v1/copilot/chat',headers=h,json={'question':'Explain'}).json()['mode']=='deterministic_fallback'
    assert len(c.get('/api/v1/events',headers=h).json())==4

def test_cluster_identity_change_preserves_acknowledgement(client):
    c,factory=client;h=auth(c)
    alert=c.get('/api/v1/alerts',headers=h).json()[0]
    c.post(f"/api/v1/alerts/{alert['id']}/acknowledge",headers=h)
    earlier=validate({**row(),'latitude':'22.30','longitude':'70.80','acq_date':'2026-09-09','acq_time':'2300'},True)
    with factory() as db:asyncio.run(main.process(db,[earlier],False))
    updated=c.get('/api/v1/alerts',headers=h).json()
    assert len(updated)==1 and updated[0]['status']=='acknowledged'
    assert updated[0]['event_id']!=alert['event_id']
    assert c.get('/api/v1/events/'+updated[0]['event_id'],headers=h).status_code==200

def test_risk_weights_total_100():
    from app.config import settings
    assert set(settings.risk_weights)==set(REQUIRED_RISK_WEIGHT_KEYS)
    assert all(value>=0 for value in settings.risk_weights.values())
    assert round(sum(settings.risk_weights.values()),6)==100

def test_risk_weight_validation_rejects_invalid():
    from app.config import Settings
    complete={'thermal_severity':50,'persistence':10,'industrial_proximity':10,'residential_proximity':10,'infrastructure_exposure':5,'classification_context':5,'historical_abnormality':10}
    base={'database_url':'sqlite://','jwt_secret':'x'*32,'demo_mode':'true'}
    # Partial init dicts deep-merge with defaults, so reject via explicit full dicts.
    with pytest.raises(Exception):Settings(**{**base,'risk_weights':{**complete,'thermal_severity':110}})
    with pytest.raises(Exception):Settings(**{**base,'risk_weights':{**complete,'thermal_severity':-10}})
    with pytest.raises(Exception):Settings(**{**base,'risk_weights':{**complete,'bogus_extra':5}})
    with pytest.raises(Exception):Settings(**{**base,'risk_weights':{key:10 for key in REQUIRED_RISK_WEIGHT_KEYS}})
    valid=Settings(**{**base,'risk_weights':complete})
    assert round(sum(valid.risk_weights.values()),6)==100

def test_satellite_credentials_missing(monkeypatch):
    monkeypatch.setattr(providers.settings,'copernicus_client_id','')
    result=asyncio.run(providers.satellite({'latitude':22,'longitude':70,'last_seen_time':'2026-09-10T01:00:00+00:00'}))
    assert result['satellite_context_available'] is False
    assert result['reason']=='credentials_missing' and result['ndvi'] is None

def test_satellite_success_mock(monkeypatch):
    monkeypatch.setattr(providers.settings,'copernicus_client_id','cid');monkeypatch.setattr(providers.settings,'copernicus_client_secret','secret')
    monkeypatch.setattr(providers.settings,'satellite_provider','copernicus')
    original=httpx.AsyncClient;providers._token_cache.clear()
    def handler(request):
        if request.url.host=='identity.dataspace.copernicus.eu':
            return httpx.Response(200,json={'access_token':'tok','expires_in':300})
        return httpx.Response(200,json={'data':[{'interval':{'from':'2026-09-10T00:00:00Z','to':'2026-09-11T00:00:00Z'},'outputs':{'ndvi':{'bands':{'B0':{'stats':{'mean':0.41232,'sampleCount':3036,'noDataCount':0}}}}}}],'status':'OK'})
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handler),**kw))
    result=asyncio.run(providers.satellite({'latitude':22,'longitude':70,'last_seen_time':'2026-09-10T01:00:00+00:00'}))
    assert result['satellite_context_available'] is True and result['ndvi']==0.4123
    assert result['acquisition_date']=='2026-09-10'
    def failure(request):return httpx.Response(503)
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(failure),**kw))
    result=asyncio.run(providers.satellite({'latitude':22,'longitude':70,'last_seen_time':'2026-09-10T01:00:00+00:00'}))
    assert result['satellite_context_available'] is False and result['reason']=='provider_unavailable'

def test_satellite_feature_propagation(monkeypatch):
    monkeypatch.setattr(providers.settings,'copernicus_client_id','')
    event=cluster([validate(row())])[0]
    context=asyncio.run(providers.satellite(event))
    event['context']=context
    assert len(features(event))==len(FEATURES)
    risk=assess(event,[])
    assert risk['missing_context'] and 'ndvi' in risk['missing_context']

def test_demo_satellite_blocked(client,monkeypatch):
    c,factory=client;h=auth(c)
    events=c.get('/api/v1/events',headers=h).json()
    for event in events:
        assert event['context']['satellite_context_available'] is False
        assert event['context']['reason']=='demo_mode'
        assert event['context']['ndvi'] is None
    demo_threshold=c.get('/api/v1/admin/threshold',headers=h).json()['threshold']
    assert demo_threshold==60

def test_analytics_insufficient_history(client,monkeypatch):
    from app import security
    c,factory=client
    with factory() as db:
        db.add(User(email='hist-admin@example.invalid',password=hash_password('histpassword123'),role='admin'));db.commit()
    token=c.post('/api/v1/auth/login',json={'email':'hist-admin@example.invalid','password':'histpassword123'}).json()['access_token']
    h={'Authorization':'Bearer '+token}
    monkeypatch.setattr(main.settings,'demo_mode',False)
    assert c.get('/api/v1/analytics/summary?days=365',headers=h).json()=={'available':False,'reason':'insufficient_history','window_days':365,'is_demo':False}
    assert c.get('/api/v1/analytics/trends?days=365',headers=h).json()=={'available':False,'reason':'insufficient_history','window_days':365,'is_demo':False}
    assert c.get('/api/v1/analytics/trends?days=366',headers=h).status_code==422
    security._login_failures.clear()

def test_login_throttling(client,monkeypatch):
    from app import security
    monkeypatch.setattr(security,'_login_failures',security.defaultdict(list))
    c,_=client
    for _ in range(10):
        assert c.post('/api/v1/auth/login',json={'email':'admin@demo.thermaguard.local','password':'wrongpassword123'}).status_code==401
    assert c.post('/api/v1/auth/login',json={'email':'admin@demo.thermaguard.local','password':'wrongpassword123'}).status_code==429
    assert c.post('/api/v1/auth/login',json={'email':'operator@demo.thermaguard.local','password':'DemoTherma2026!'}).status_code==200
