"""Provider fixtures are synthetic test responses; no network or production DB access."""
import asyncio
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import json
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select

from test_system import client, auth
from test_runtime_reliability import store, observation
from app import providers as p, main
from app.config import settings, Settings
from app.database import User, Event, Alert, EmailNotification, PushSubscription


@pytest.fixture(autouse=True)
def context_setup(monkeypatch):
    p._context_cache.clear()
    monkeypatch.setattr(p,'_nominatim_lock',asyncio.Lock())
    monkeypatch.setattr(p,'_nominatim_last',0)
    for name in ('weather','air_quality','geocoding','eonet','routing'):
        monkeypatch.setattr(settings,name+'_enabled',True)
    monkeypatch.setattr(settings,'openrouteservice_api_key','test-only-secret')
    monkeypatch.setattr(settings,'push_notifications_enabled',False)
    monkeypatch.setattr(settings,'firebase_credentials_path','')
    monkeypatch.setattr(p,'_firebase_app',None)
    monkeypatch.setattr(p,'_firebase_signature',None)
    async def forbidden(*args,**kwargs):raise AssertionError('Unexpected real provider request')
    monkeypatch.setattr(p,'_context_json',forbidden)


@pytest.fixture
def event():
    return dict(id='real-fixture',latitude=22.0,longitude=70.0,last_seen_time='2026-09-11T12:45:00+00:00',
                is_demo=False,context={},risk={'risk_score':85,'risk_level':'High'},detection_ids=['test-one'])


def hourly(name,**overrides):
    weather={'temperature_2m':[28.0],'relative_humidity_2m':[60.0],'precipitation':[0.1],'wind_speed_10m':[12.0],'wind_direction_10m':[180.0]}
    aq={key:[3.2] for key in ('pm2_5','pm10','carbon_monoxide','nitrogen_dioxide','ozone')}
    units={'temperature_2m':'°C','relative_humidity_2m':'%','precipitation':'mm','wind_speed_10m':'km/h','wind_direction_10m':'°'} if name=='weather' else {k:'μg/m³' for k in aq}
    result={'hourly':{'time':['2026-09-11T12:00'],**(weather if name=='weather' else aq)},'hourly_units':units}
    result.update(overrides)
    return result


def mock_json(monkeypatch,data=None,error=None):
    calls=[]
    async def get(*args,**kwargs):
        calls.append((args,kwargs))
        if error:raise error
        return deepcopy(data)
    monkeypatch.setattr(p,'_context_json',get)
    return calls


@pytest.mark.parametrize('name',['weather','air_quality'])
def test_hourly_success_and_cache(name,event,monkeypatch):
    calls=mock_json(monkeypatch,hourly(name))
    first=asyncio.run(p.fetch_context(name,event));second=asyncio.run(p.fetch_context(name,event))
    assert first==second and len(calls)==1 and first['status']=='available'
    assert first['observed_at']=='2026-09-11T12:00:00+00:00'
    assert calls[0][0][1]['latitude']==22 and calls[0][0][1]['start_date']=='2026-09-11'
    first['provider']='mutated'
    assert second['provider']=='open_meteo'


@pytest.mark.parametrize('name',['weather','air_quality','location','eonet','routing'])
@pytest.mark.parametrize('failure',['timeout','http','malformed'])
def test_failures_are_explicit(name,failure,event,monkeypatch):
    error=httpx.ReadTimeout('test-only-secret') if failure=='timeout' else httpx.HTTPStatusError('test-only-secret',request=httpx.Request('GET','https://example.org'),response=httpx.Response(503)) if failure=='http' else None
    mock_json(monkeypatch,{},error)
    result=asyncio.run(p.fetch_context(name,event,destination=[71,23]))
    assert result['status']=='failed'
    assert result['reason']=={'timeout':'timeout','http':'provider_error','malformed':'malformed_response'}[failure]
    assert 'test-only-secret' not in json.dumps(result)


@pytest.mark.parametrize('name',['weather','air_quality','location','eonet','routing'])
def test_disabled_no_call(name,event,monkeypatch):
    monkeypatch.setattr(settings,p.CONTEXT_PREFIX.get(name,name)+'_enabled',False)
    assert asyncio.run(p.fetch_context(name,event))['reason']=='disabled'


@pytest.mark.parametrize('name',['weather','air_quality'])
@pytest.mark.parametrize('bad',['units','null','nan','array','date'])
def test_hourly_malformed_and_missing(name,bad,event,monkeypatch):
    data=hourly(name);key='temperature_2m' if name=='weather' else 'pm2_5'
    if bad=='units':data['hourly_units'][key]='wrong'
    if bad=='null':
        for k in data['hourly']:
            if k!='time':data['hourly'][k]=[None]
    if bad=='nan':data['hourly'][key]=[float('nan')]
    if bad=='array':data['hourly'][key]=[]
    if bad=='date':data['hourly']['time']=['2026-09-10T12:00']
    mock_json(monkeypatch,data)
    result=asyncio.run(p.fetch_context(name,event))
    assert result['status']==('unavailable' if bad in ('null','date') else 'failed')


def test_geocoding_missing_optional_fields_cache_and_user_agent(event,monkeypatch):
    calls=mock_json(monkeypatch,{'display_name':'Test district','address':{'country':'India'}})
    result=asyncio.run(p.reverse_geocode_event(event))
    assert result['status']=='available' and result['city'] is None and result['country']=='India'
    assert calls[0][0][3]['User-Agent']==settings.geocoding_user_agent
    assert asyncio.run(p.reverse_geocode_event(event))==result and len(calls)==1


def test_geocoding_no_address(event,monkeypatch):
    mock_json(monkeypatch,{'error':'Unable to geocode'})
    assert asyncio.run(p.reverse_geocode_event(event))['reason']=='no_address'


@pytest.mark.parametrize('far,old,expected',[(False,False,True),(True,False,False),(False,True,False)])
def test_eonet_matching(far,old,expected,event,monkeypatch):
    mock_json(monkeypatch,{'events':[{'id':'EONET-test','title':'Test hazard','categories':[{'title':'Wildfires'}],
        'geometry':[{'type':'Point','coordinates':[80 if far else 70,22],
                     'date':'2026-08-01T12:00:00Z' if old else '2026-09-11T12:00:00Z'}]}]})
    result=asyncio.run(p.fetch_eonet_context(event))
    assert result['status']=='available' and result['matched'] is expected
    if expected:assert result['distance_km']==0 and result['event_id']=='EONET-test'


def test_route_missing_configuration_and_destination(event,monkeypatch):
    monkeypatch.setattr(settings,'openrouteservice_api_key','')
    assert asyncio.run(p.fetch_route_context(event,[71,23]))['reason']=='not_configured'
    monkeypatch.setattr(settings,'openrouteservice_api_key','test')
    assert asyncio.run(p.fetch_route_context(event))['reason']=='destination_required'


def test_route_success_lon_lat_order(event,monkeypatch):
    calls=mock_json(monkeypatch,{'features':[{'properties':{'summary':{'distance':2000,'duration':180}},'geometry':{'type':'LineString','coordinates':[[70,22],[71,23]]}}]})
    result=asyncio.run(p.fetch_route_context(event,[71,23]))
    assert result['status']=='available' and result['distance_m']==2000
    assert calls[0][0][4]['coordinates']==[[70,22],[71,23]]
    assert calls[0][0][3]['Authorization']=='test-only-secret'
    assert 'test-only-secret' not in json.dumps(result)


def test_cache_stale_preserved_after_failure_and_time_change(event,monkeypatch):
    mock_json(monkeypatch,hourly('weather'))
    old=asyncio.run(p.fetch_weather_context(event))
    old['fetched_at']=(p.utc_now()-timedelta(days=2)).isoformat();p._context_cache.clear()
    mock_json(monkeypatch,error=httpx.ReadTimeout('secret'))
    result=asyncio.run(p.fetch_weather_context(event,old))
    assert result['status']=='available' and result['refresh_status']=='failed' and result['fetched_at']==old['fetched_at']
    changed={**event,'last_seen_time':'2026-09-12T12:00:00Z'}
    assert asyncio.run(p.fetch_weather_context(changed,old))['status']=='failed'


def test_sync_budget_and_priority(event,monkeypatch):
    for name in ('air_quality','geocoding','eonet'):monkeypatch.setattr(settings,name+'_enabled',False)
    monkeypatch.setattr(settings,'weather_events_per_sync',1)
    calls=mock_json(monkeypatch,hourly('weather'))
    old={**deepcopy(event),'id':'old','last_seen_time':'2026-09-10T12:00:00Z'}
    asyncio.run(p.enrich_external_context([old,event]))
    assert len(calls)==1 and event['context']['weather']['status']=='available'
    assert old['context']['weather']['status']=='deferred'


def test_verified_packet_excludes_failed_guesses(event):
    event['context']={'weather':{'status':'failed','temperature_c':999},'location':{
        'status':'available','version':1,'provider':'nominatim','display_name':'Test location','secret':'secret'}}
    event['context']['location']['signature']=p.context_signature('location',event)
    result=main.copilot_evidence(event)
    assert result['context']['weather']=='not available'
    assert result['context']['location']['display_name']=='Test location'
    assert 'secret' not in json.dumps(result)


def test_core_provider_calls_outside_transaction_and_scores_unchanged(store,monkeypatch):
    calls=[]
    with store() as db:
        for name in ('weather','air_quality','geocoding','eonet'):monkeypatch.setattr(settings,name+'_enabled',False)
        baseline=asyncio.run(main.process(db,[observation()],create_notifications=False))[0]
        scores=deepcopy((baseline['classification'],baseline['risk'],baseline['features']))
        monkeypatch.setattr(settings,'weather_enabled',True)
        async def fail(*args,**kwargs):
            assert not db.in_transaction();calls.append(True);raise httpx.ReadTimeout('secret')
        monkeypatch.setattr(p,'_context_json',fail)
        updated=asyncio.run(main.process(db,[],create_notifications=False))[0]
        assert calls and updated['context']['weather']['status']=='failed'
        assert (updated['classification'],updated['risk'],updated['features'])==scores
        assert db.get(Event,updated['id']) is not None


def test_push_disabled_missing_and_bad_credentials(event,monkeypatch,tmp_path):
    assert p.send_push_notification('token',event)['reason']=='disabled'
    monkeypatch.setattr(settings,'push_notifications_enabled',True)
    assert p.send_push_notification('token',event)['reason']=='not_configured'
    path=tmp_path/'service-account.json';path.write_text('{broken')
    monkeypatch.setattr(settings,'firebase_credentials_path',str(path))
    assert p.send_push_notification('token',event)['reason']=='not_configured'


@pytest.mark.parametrize('fails',[False,True])
def test_push_sdk_success_and_failure(fails,event,monkeypatch):
    from firebase_admin import messaging
    monkeypatch.setattr(settings,'push_notifications_enabled',True)
    monkeypatch.setattr(p,'firebase_app',lambda:object())
    calls=[]
    def send(message,app=None):
        calls.append(message)
        if fails:raise ValueError('PRIVATE_KEY_DO_NOT_LEAK')
        return 'test-id'
    monkeypatch.setattr(messaging,'send',send)
    result=p.send_push_notification('test-device',event)
    assert result['sent'] is (not fails) and len(calls)==1
    assert calls[0].data=={'event_id':event['id']}
    assert 'PRIVATE_KEY' not in json.dumps(result)


@pytest.mark.parametrize('fails',[False,True])
def test_push_claims_after_commit_dedup_and_core_preserved(client,event,monkeypatch,fails):
    c,factory=client;headers=auth(c)
    stored=c.get('/api/v1/events',headers=headers).json()[0]
    stored['is_demo']=False;stored['risk']['risk_level']='High'
    monkeypatch.setattr(settings,'push_notifications_enabled',True)
    calls=[]
    with factory() as db:
        user=db.scalar(select(User).where(User.role=='admin'))
        user.notifications_enabled=True;user.latitude=stored['latitude'];user.longitude=stored['longitude'];user.alert_radius_km=10
        db.add(PushSubscription(user_id=user.id,token='fixture-token'))
        db.commit()
        before=[deepcopy(e.payload) for e in db.scalars(select(Event))];db.rollback()
        def send(token,event):
            assert not db.in_transaction();calls.append(event['id'])
            if fails:raise RuntimeError('test-private-key')
            return {'sent':True,'reason':None}
        monkeypatch.setattr(p,'send_push_notification',send)
        main.deliver_push_notifications(db,stored)
        main.deliver_push_notifications(db,stored)
        reclustered={**stored,'id':'changed-id'}
        main.deliver_push_notifications(db,reclustered)
        assert len(calls)==1
        claims=list(db.scalars(select(EmailNotification).where(EmailNotification.channel=='push')))
        assert len(claims)==1 and claims[0].status==('failed' if fails else 'sent')
        assert [e.payload for e in db.scalars(select(Event))]==before


def test_push_device_owned_and_diagnostics_protected(client):
    c,_=client
    assert c.put('/api/v1/auth/push-device',json={'token':'x'*30}).status_code==401
    headers=auth(c)
    assert c.put('/api/v1/auth/notifications',headers=headers,json={'notifications_enabled':True,'latitude':22,'longitude':70}).status_code==200
    assert c.put('/api/v1/auth/push-device',headers=headers,json={'token':'x'*30}).json()=={'registered':True}
    assert c.delete('/api/v1/auth/push-device',headers=headers).json()=={'registered':False}
    assert c.get('/api/v1/admin/diagnostics/context').status_code==401
    assert c.get('/api/v1/admin/diagnostics/context',headers=auth(c,operator=True)).status_code==403
    result=c.get('/api/v1/admin/diagnostics/context',headers=headers)
    assert result.status_code==200 and 'test-only-secret' not in result.text


def test_route_requires_event_scope(client,monkeypatch):
    c,_=client;headers=auth(c);event=c.get('/api/v1/events',headers=headers).json()[0]
    assert c.post('/api/v1/events/'+event['id']+'/route',json={'latitude':22,'longitude':70}).status_code==401
    monkeypatch.setattr(settings,'routing_enabled',False)
    assert c.post('/api/v1/events/'+event['id']+'/route',headers=headers,json={'latitude':22,'longitude':70}).json()['reason']=='disabled'
    assert c.post('/api/v1/events/'+event['id']+'/route',headers=headers,json={'latitude':200,'longitude':70}).status_code==422


@pytest.mark.parametrize('values',[{'weather_timeout_seconds':0},{'air_quality_events_per_sync':21},{'geocoding_provider':'unsupported'},{'eonet_api_url':'http://example.org'},{'routing_timeout_seconds':-1}])
def test_settings_reject_invalid_context(values):
    with pytest.raises(ValueError):Settings(_env_file=None,**values)


def test_push_queued_without_smtp_only_after_threshold(client,monkeypatch):
    c,factory=client;headers=auth(c)
    stored=c.get('/api/v1/events',headers=headers).json()[0]
    stored['is_demo']=False
    monkeypatch.setattr(settings,'push_notifications_enabled',True)
    monkeypatch.setattr(settings,'smtp_enabled',False)
    with factory() as db:
        low=deepcopy(stored);low['risk']['risk_score']=0
        main.create_alerts(db,low)
        assert not db.info.get('pending_notifications')
        high=deepcopy(stored);high['risk']['risk_score']=100
        main.create_alerts(db,high)
        assert len(db.info['pending_notifications'])==1
        db.rollback();db.info.clear()


def test_firebase_initialization_validates_certificate_and_reuses_app(monkeypatch,tmp_path):
    import firebase_admin
    from firebase_admin import credentials
    path=tmp_path/'service-account.json'
    path.write_text(json.dumps({'type':'service_account','project_id':'test-project','private_key':'test-only'}))
    monkeypatch.setattr(settings,'firebase_credentials_path',str(path))
    monkeypatch.setattr(settings,'firebase_project_id','test-project')
    calls=[];app=object()
    monkeypatch.setattr(credentials,'Certificate',lambda data:calls.append('certificate') or object())
    monkeypatch.setattr(firebase_admin,'initialize_app',lambda *a,**kw:calls.append('initialize') or app)
    assert p.firebase_app() is app and p.firebase_app() is app
    assert calls==['certificate','initialize']
    monkeypatch.setattr(settings,'firebase_project_id','wrong-project')
    assert p.firebase_app() is None


def test_empty_scope_never_calls_gemini(client,monkeypatch):
    c,_=client
    monkeypatch.setattr(main,'visible',lambda *args:[])
    async def forbidden(*args):raise AssertionError('No event evidence')
    monkeypatch.setattr(main,'gemini_request',forbidden)
    response=c.post('/api/v1/copilot/chat',headers=auth(c),json={'question':'Explain'})
    assert response.json()['event_ids']==[] and response.json()['reason']=='no_events'


def test_firms_ingestion_survives_new_context_failure(store,monkeypatch):
    async def firms(*args,**kwargs):return [observation()],0
    monkeypatch.setattr(p,'firms',firms)
    for name in ('weather','air_quality','geocoding','eonet'):monkeypatch.setattr(settings,name+'_enabled',True)
    mock_json(monkeypatch,error=httpx.ReadTimeout('test-only-secret'))
    with store() as db:
        result=asyncio.run(main.sync(main.SyncInput(),user=None,db=db))
        assert result['ingested']==1
        event=db.scalar(select(Event)).payload
        assert all(event['context'][name]['status']=='failed' for name in ('weather','air_quality','location','eonet'))


def test_selected_event_gemini_context_only(client,monkeypatch):
    c,_=client;headers=auth(c);events=c.get('/api/v1/events',headers=headers).json()
    captured=[]
    async def reply(prompt,*args):
        captured.append(json.loads(prompt));return {'response_ok':True,'answer':'Test answer'}
    monkeypatch.setattr(main,'gemini_request',reply)
    response=c.post('/api/v1/copilot/chat',headers=headers,json={'question':'Explain','event_id':events[0]['id']})
    assert response.json()['mode']=='gemini'
    assert [e['id'] for e in captured[0]['events']]==[events[0]['id']]


def test_demo_never_calls_external_providers(event):
    event['is_demo']=True
    for name in p.CONTEXT_NAMES:
        assert asyncio.run(p.fetch_context(name,event,destination=[71,23]))['reason']=='demo_mode'


def test_moved_event_does_not_reuse_unrelated_location_or_route(event,monkeypatch):
    location={**p.context_status('location','available',None),'signature':p.context_signature('location',event),'display_name':'Old place'}
    route={**p.context_status('routing','available',None),'signature':p.context_signature('routing',event,[71,23]),'destination':[71,23]}
    event['context']={'location':location,'routing':route};event['latitude']=23
    assert p.verified_context(event)['location']=='not available'
    for prefix in ('weather','air_quality','geocoding','eonet'):monkeypatch.setattr(settings,prefix+'_events_per_sync',0)
    asyncio.run(p.enrich_external_context([event]))
    assert event['context']['location']['status']=='deferred'
    assert event['context']['routing']['status']=='deferred'


# ============================================================
# PROVIDER HEALTH REGISTRY (dynamic status UI)
# ============================================================

@pytest.fixture(autouse=True)
def health_isolated():
    p._HEALTH.clear()
    yield
    p._HEALTH.clear()


def test_record_provider_call_success_and_failure_categories():
    p.record_provider_call('weather','success',1.234)
    health=p.provider_health()['providers']
    assert health['weather']['status']=='healthy'
    assert health['weather']['last_latency_ms']==1234
    p.record_provider_call('weather','failure',0.5,'timeout')
    health=p.provider_health()['providers']
    assert health['weather']['status']=='degraded'  # success recorded earlier
    assert health['weather']['last_error_category']=='timeout'
    p._HEALTH.clear()
    p.record_provider_call('weather','failure',0.1,'provider_error')
    assert p.provider_health()['providers']['weather']['status']=='failed'


def test_health_registry_never_raises_or_stores_secret_text():
    p.record_provider_call('firms','failure',None,'Authorization: Bearer sk-secret-123')
    snapshot=p.provider_health()
    assert 'sk-secret-123' not in json.dumps(snapshot)
    p.record_provider_call('weather',  # garbage arguments must not raise
        None,None,object())
    p.record_provider_call('weather','success','not-a-number')


def test_disabled_provider_is_never_reported_healthy(monkeypatch):
    monkeypatch.setattr(settings,'weather_enabled',False)
    p.record_provider_call('weather','success',0.2)
    assert p.provider_health()['providers']['weather']['status']=='disabled'


def test_not_configured_routing_stays_not_configured(monkeypatch):
    monkeypatch.setattr(settings,'routing_enabled',True)
    monkeypatch.setattr(settings,'openrouteservice_api_key','')
    assert p.provider_health()['providers']['routing']['status']=='not_configured'


def test_osm_wrapper_records_outcome(event,monkeypatch):
    async def ok(ev):return {'osm_context_available':True,'landuse_class':'industrial'}
    monkeypatch.setattr(p,'_osm_request',ok)
    asyncio.run(p.osm(event))
    assert p.provider_health()['providers']['osm']['status']=='healthy'
    async def boom(ev):raise ValueError('Invalid Overpass response')
    monkeypatch.setattr(p,'_osm_request',boom)
    with pytest.raises(ValueError):
        asyncio.run(p.osm(event))
    assert p.provider_health()['providers']['osm']['status']=='degraded'


def test_satellite_wrapper_records_outcome(monkeypatch):
    async def ok(ev):return {'satellite_context_available':True,'ndvi':0.4}
    monkeypatch.setattr(p,'_satellite_request',ok)
    asyncio.run(p.satellite({'latitude':22.0,'longitude':70.0}))
    assert p.provider_health()['providers']['copernicus']['status']=='healthy'
    async def boom(ev):raise TimeoutError()
    monkeypatch.setattr(p,'_satellite_request',boom)
    with pytest.raises(TimeoutError):
        asyncio.run(p.satellite({'latitude':22.0,'longitude':70.0}))
    assert p.provider_health()['providers']['copernicus']['last_error_category']=='timeout'


def test_firms_wrapper_records_success(monkeypatch):
    async def ok():return [{'id':'VIIRS_NOAA20_NRT','min_date':'2026-09-01','max_date':'2026-09-12','kind':'NRT'}]
    monkeypatch.setattr(p,'_firms_sources_impl',ok)
    assert asyncio.run(p.firms_sources())[0]['id']=='VIIRS_NOAA20_NRT'
    assert p.provider_health()['providers']['firms']['status']=='healthy'


def test_eonet_active_events_maps_open_point_hazards(monkeypatch):
    async def payload(url,params=None,timeout=None,headers=None,body=None,provider=None):
        assert params['status']=='open'
        return {'events':[{'id':'EONET-1','title':'Wildfire test','categories':[{'title':'Wildfires'}],
                           'geometry':[{'date':'2026-09-10T00:00:00Z','type':'Point','coordinates':[70.0,22.0]}]}]}
    monkeypatch.setattr(p,'_context_json',payload)
    result=asyncio.run(p.eonet_active_events())
    assert result['available'] and result['count']==1
    row=result['events'][0]
    assert row['category']=='Wildfires' and row['latitude']==22.0 and row['longitude']==70.0


def test_eonet_active_events_skips_non_point_geometry(monkeypatch):
    async def payload(url,params=None,timeout=None,headers=None,body=None,provider=None):
        return {'events':[{'id':'EONET-2','title':'Storm polygon','categories':[],
                           'geometry':[{'date':'2026-09-10T00:00:00Z','type':'Polygon','coordinates':[[[0,0],[1,1],[2,2],[0,0]]]}]}]}
    monkeypatch.setattr(p,'_context_json',payload)
    result=asyncio.run(p.eonet_active_events())
    assert result['available'] and result['count']==0


def test_eonet_active_events_safe_failure(monkeypatch):
    async def payload(url,params=None,timeout=None,headers=None,body=None,provider=None):
        raise httpx.ConnectError('down')
    monkeypatch.setattr(p,'_context_json',payload)
    result=asyncio.run(p.eonet_active_events())
    assert result['available'] is False and result['events']==[]
    assert p.provider_health()['providers']['eonet']['last_error_category']=='network_error'


def test_providers_status_endpoint_requires_auth(client):
    c,factory=client
    assert c.get('/api/v1/providers/status').status_code==401


def test_providers_status_endpoint_is_secret_free(client):
    c,factory=client;headers=auth(c)
    response=c.get('/api/v1/providers/status',headers=headers)
    assert response.status_code==200
    body=response.json()
    assert 'providers' in body and 'note' in body
    assert 'key' not in json.dumps(body).lower() or 'key' in body['providers']
    text=json.dumps(body)
    for forbidden in ('api_key','Authorization','Bearer','secret','password'):
        assert forbidden not in text


def test_eonet_events_endpoint(monkeypatch,client):
    async def payload(url,params=None,timeout=None,headers=None,body=None,provider=None):
        return {'events':[{'id':'E1','title':'T','categories':[{'title':'Wildfires'}],
                           'geometry':[{'date':'2026-09-10T00:00:00Z','type':'Point','coordinates':[70.0,22.0]}]}]}
    monkeypatch.setattr(p,'_context_json',payload)
    c,factory=client;headers=auth(c)
    response=c.get('/api/v1/eonet/events',headers=headers)
    assert response.status_code==200
    assert response.json()['available'] is True


def test_alerts_payload_reports_coordinates_and_admin_delivery(client):
    # Authenticated organization/admin request surfaces event coordinates;
    # per-attempt delivery audit rows carry only channel/status/timestamp.
    c,factory=client;headers=auth(c)
    response=c.get('/api/v1/alerts',headers=headers)
    assert response.status_code==200
    for alert in response.json():
        assert 'latitude' in alert and 'longitude' in alert
        if alert.get('delivery') is not None:
            for row in alert['delivery']:
                assert set(row)=={'channel','status','sent_at'}
                assert 'email' not in json.dumps(row) or row.get('channel')
