"""Mocked multi-source FIRMS contracts; no external provider requests or training."""
import os
os.environ['DEMO_MODE'] = 'true'
import asyncio
import csv
import io
import json
import math
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main, providers, ml
from app.config import FIRMS_SOURCES, settings
from app.database import Base, Detection, Event
from app.intelligence import validate, cluster, features, FEATURES
from test_system import client, auth


def raw(source='VIIRS_SNPP_NRT', **changes):
    modis = source.startswith('MODIS')
    row = dict(latitude='22', longitude='70', acq_date='2026-01-01', acq_time='1200',
               frp='10', instrument='MODIS' if modis else 'VIIRS',
               satellite='A' if modis else 'N20' if 'NOAA20' in source else 'N',
               confidence='75' if modis else 'n', daynight='D', version='2.0', scan='0.4', track='0.5')
    row.update({'brightness':'320','bright_t31':'290'} if modis else {'bright_ti4':'330','bright_ti5':'295'})
    row.update(changes)
    return row


def obs(source='VIIRS_SNPP_NRT', **changes):
    return validate(raw(source, **changes), source_dataset=source)


@pytest.fixture
def transport(monkeypatch):
    providers._availability_cache.clear()
    monkeypatch.setattr(providers, '_availability_lock', asyncio.Lock())
    monkeypatch.setattr(settings, 'firms_map_key', 'fixture-key')
    original = httpx.AsyncClient
    def install(handler):
        monkeypatch.setattr(providers.httpx, 'AsyncClient', lambda **kwargs:
                            original(transport=httpx.MockTransport(handler), **kwargs))
    yield install
    providers._availability_cache.clear()


def catalog(sources=None):
    return 'data_id,min_date,max_date\n'+''.join(source+',2000-01-01,2099-12-31\n' for source in (sources or FIRMS_SOURCES))


def csv_rows(rows):
    out=io.StringIO(); writer=csv.DictWriter(out, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return out.getvalue()


@pytest.mark.parametrize('source', list(FIRMS_SOURCES))
def test_sensor_schema_provenance_and_missing_values(source):
    row=obs(source)
    assert row['source_dataset']==source and row['provider']=='NASA FIRMS'
    assert row['acquired_at']==row['observed_at'] and row['version']=='2.0'
    assert row['thermal_primary']==(320 if source.startswith('MODIS') else 330)
    assert row['thermal_secondary']==(290 if source.startswith('MODIS') else 295)
    assert row['scan']==0.4 and row['track']==0.5 and row['is_demo'] is False
    secondary='bright_t31' if source.startswith('MODIS') else 'bright_ti5'
    missing=obs(source, **{secondary:'', 'scan':''})
    assert missing['thermal_secondary'] is None and missing['scan'] is None
    assert ('bright_ti4' not in row['raw']) if source.startswith('MODIS') else ('brightness' not in row['raw'])


@pytest.mark.parametrize('field,value', [('latitude','nan'),('frp','-1'),('scan','nan'),('track','-1'),('bright_ti5','inf'),('instrument','MODIS')])
def test_invalid_sensor_rows_rejected(field,value):
    with pytest.raises((ValueError,TypeError)):
        obs(**{field:value})


def test_source_identity_and_cross_sensor_cluster():
    a=obs(); same=obs(latitude='22.0',longitude='70.000',acq_time='1200')
    b=obs('VIIRS_NOAA20_NRT');c=obs('MODIS_NRT');sp=obs('VIIRS_SNPP_SP')
    assert a['id']==same['id']
    assert len({r['id'] for r in (a,b,c,sp)})==4
    event=cluster([a,b,c,sp])[0]
    assert event['detection_count']==4 and len(cluster([a,b,c,sp]))==1
    assert event['source_counts']=={source:1 for source in ('VIIRS_SNPP_NRT','VIIRS_NOAA20_NRT','MODIS_NRT','VIIRS_SNPP_SP')}
    assert event['sensor_summary']['unique_satellite_count']==3
    assert event['sensor_summary']['unique_sensor_count']==2
    assert event['sensor_summary']['modis_primary_mean']==320
    assert event['sensor_summary']['viirs_primary_mean']==330
    assert math.isnan(features(event)[FEATURES.index('mean_brightness')])
    assert ml.predict(event)['predicted_class'] is None


def test_availability_cache_and_safe_metadata(transport):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,text=catalog()+'BA_MODIS,2000-01-01,2099-01-01\n')
    transport(handler)
    async def run():
        first=await providers.firms_sources();first[0]['id']='tampered'
        return await providers.firms_sources()
    result=asyncio.run(run())
    assert len(calls)==1 and {r['id'] for r in result}==set(FIRMS_SOURCES)
    assert all(set(r)=={'id','kind','min_date','max_date'} for r in result)
    assert 'fixture-key' not in json.dumps(result)


@pytest.mark.parametrize('body', ['wrong,header\na,b\n','data_id,min_date,max_date\nVIIRS_SNPP_NRT,2026-02-01,2026-01-01\n'])
def test_malformed_availability_no_cached_success(transport,body):
    transport(lambda request:httpx.Response(200,text=body))
    with pytest.raises(ValueError):asyncio.run(providers.firms_sources())
    assert not providers._availability_cache


@pytest.mark.parametrize('source', ['VIIRS_SNPP_NRT','VIIRS_NOAA20_NRT','MODIS_NRT','VIIRS_SNPP_SP','MODIS_SP'])
def test_real_provider_flow_mocked(transport,source):
    calls=[]
    def handler(request):
        calls.append(request.url.path)
        if 'data_availability' in request.url.path:return httpx.Response(200,text=catalog())
        assert '/'+source+'/' in request.url.path
        return httpx.Response(200,text=csv_rows([raw(source),raw(source,latitude='999')]))
    transport(handler)
    rows,rejected=asyncio.run(providers.firms([69,21,71,23],1,'2026-01-01',source))
    assert len(calls)==2 and len(rows)==1 and rejected==1
    assert rows[0]['source_dataset']==source and not rows[0]['is_demo']


@pytest.mark.parametrize('source,start', [('VIIRS_NOAA20_NRT','2026-01-01'),('VIIRS_SNPP_NRT','1999-01-01')])
def test_unavailable_source_or_date_stops_before_area(transport,source,start):
    def handler(request):
        assert 'data_availability' in request.url.path
        return httpx.Response(200,text=catalog(['VIIRS_SNPP_NRT']))
    transport(handler)
    with pytest.raises(providers.SourceUnavailable):
        asyncio.run(providers.firms([69,21,71,23],1,start,source))


def test_invalid_source_http_422(client):
    c,_=client;headers=auth(c)
    assert c.post('/api/v1/firms/sync',headers=headers,json={'sources':['../bad']}).status_code==422
    assert c.post('/api/v1/firms/sync',headers=headers,json={'sources':['MODIS_SP']}).status_code==422
    assert c.post('/api/v1/firms/history/backfill',headers=headers,
                  json={'bounds':[69,21,71,23],'start_date':'2026-01-01','end_date':'2026-01-01','source':'BA_MODIS'}).status_code==422
    assert main.SyncInput().sources is None


def test_ingestion_exact_duplicate_and_legacy_reconciliation(monkeypatch):
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);factory=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(settings,'demo_mode',False)
    with factory() as db:
        a,b=obs(),obs('VIIRS_NOAA20_NRT')
        asyncio.run(main.process(db,[a,a,b],enrich=False,create_notifications=False))
        before=list(db.scalars(select(Detection)));assert len(before)==2
        asyncio.run(main.process(db,[a,b],enrich=False,create_notifications=False))
        assert len(list(db.scalars(select(Detection))))==2
        assert len(list(db.scalars(select(Event))))==1
        legacy=validate(raw(longitude='71'))
        legacy['acquisition_query']={'source':'VIIRS_SNPP_NRT'}
        db.add(Detection(id=legacy['id'],is_demo=False,payload=legacy));db.commit()
        asyncio.run(main.process(db,[obs(longitude='71')],enrich=False,create_notifications=False))
        assert len(list(db.scalars(select(Detection))))==3
        unknown=validate(raw(longitude='72'));db.add(Detection(id=unknown['id'],is_demo=False,payload=unknown));db.commit()
        with pytest.raises(ValueError,match='legacy'):
            asyncio.run(main.process(db,[obs(longitude='72')],enrich=False,create_notifications=False))
        assert len(list(db.scalars(select(Detection))))==4
    engine.dispose()


def test_candidate_is_one_unreviewed_event_and_keeps_sensor_evidence(tmp_path):
    event=cluster([obs(),obs('VIIRS_NOAA20_NRT')])[0]
    event['features']={key:None if math.isnan(value) else value for key,value in zip(FEATURES,features(event))}
    row=ml.candidate_row(event)
    assert row['reviewed']=='false' and row['label']=='' and row['detection_count']==2
    assert json.loads(row['source_counts'])==event['source_counts']
    assert not set(ml.SENSOR_COLUMNS)&set(FEATURES)
    path=tmp_path/'candidates.csv'
    with path.open('w') as file:
        writer=csv.DictWriter(file,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    assert ml.dataset(path)==[]
    row.update(reviewed='true',label=ml.CLASSES[0],reviewer='human',source_reference='https://example.org/verified',split_group='facility_january')
    with path.open('w') as file:
        writer=csv.DictWriter(file,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    assert len(ml.dataset(path))==1
    assert not ml.readiness(ml.dataset(path))['training_ready']


def test_raw_endpoint_requires_auth_and_scope(client):
    c,_=client
    assert c.get('/api/v1/firms/detections').status_code==401
    result=c.get('/api/v1/firms/detections?limit=2',headers=auth(c)).json()
    assert len(result['detections'])==2 and result['total']>=2
    operator=auth(c,operator=True)
    allowed={identity for event in c.get('/api/v1/events',headers=operator).json() for identity in event['detection_ids']}
    scoped=c.get('/api/v1/firms/detections?limit=500',headers=operator).json()
    assert {row['id'] for row in scoped['detections']}==allowed
    assert scoped['total']==len(allowed)



def test_multisource_sync_and_historical_sp_route(monkeypatch):
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);factory=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(settings,'demo_mode',False)
    monkeypatch.setattr(main,'firms_sync_lock',asyncio.Lock())
    monkeypatch.setattr(settings,'osm_events_per_sync',0)
    monkeypatch.setattr(settings,'satellite_events_per_sync',1)
    calls=[]
    async def firms(bounds,days=1,start_date=None,source='VIIRS_SNPP_NRT'):
        calls.append((source,days,start_date))
        return [obs(source)],0
    async def check(source,days,start_date=None):
        assert source=='MODIS_SP' and days==1
    async def satellite(event):return {'satellite_context_available':False,'reason':'mock_no_imagery'}
    monkeypatch.setattr(providers,'firms',firms)
    monkeypatch.setattr(providers,'check_firms_window',check)
    monkeypatch.setattr(providers,'satellite',satellite)
    with factory() as db:
        body=main.SyncInput(bounds=[69,21,71,23],sources=['VIIRS_SNPP_NRT','VIIRS_NOAA20_NRT'])
        result=asyncio.run(main.sync(body,user=None,db=db))
        assert result['observations_received']==2 and result['new_detections']==2 and result['events']==1
        assert result['provider_requests']==2
        assert asyncio.run(main.sync(body,user=None,db=db))['new_detections']==0
        def prohibited(*args,**kwargs):raise AssertionError('Historical backfill must not create alerts')
        monkeypatch.setattr(main,'create_alerts',prohibited)
        history=main.HistoricalSyncInput(bounds=[69,21,71,23],start_date='2026-01-01',end_date='2026-01-01',source='MODIS_SP')
        result=asyncio.run(main.backfill_history(history,user=None,db=db))
        assert result['observations_ingested']==1
        assert asyncio.run(main.backfill_history(history,user=None,db=db))['observations_ingested']==0
        assert len(list(db.scalars(select(Detection))))==3
    engine.dispose()


def test_combined_budget_does_not_insert_partial_sources(monkeypatch):
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);factory=sessionmaker(engine,expire_on_commit=False)
    monkeypatch.setattr(settings,'demo_mode',False)
    monkeypatch.setattr(settings,'max_sync_observations',1)
    monkeypatch.setattr(main,'firms_sync_lock',asyncio.Lock())
    async def firms(bounds,days=1,source='VIIRS_SNPP_NRT'):return [obs(source)],0
    monkeypatch.setattr(providers,'firms',firms)
    with factory() as db:
        with pytest.raises(main.HTTPException) as error:
            asyncio.run(main.sync(main.SyncInput(sources=['VIIRS_SNPP_NRT','VIIRS_NOAA20_NRT']),user=None,db=db))
        assert error.value.status_code==422
        assert not list(db.scalars(select(Detection)))
    engine.dispose()


def test_published_sensor_provenance_stays_outside_model_vector(tmp_path):
    from finalize_reviewed_labels import finalize
    from review_common import read_csv
    event=cluster([obs()])[0]
    event['features']={k:None if math.isnan(v) else v for k,v in zip(FEATURES,features(event))}
    row=ml.candidate_row(event)
    row.update(reviewed='true',label=ml.CLASSES[0],reviewer='human',source_reference='https://example.org/verified',split_group='one_facility',reviewed_at='2026-01-02T00:00:00+00:00')
    path=tmp_path/'input.csv';out=tmp_path/'published.csv'
    with path.open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader();writer.writerow(row)
    finalize(path,out)
    header,rows,_=read_csv(out)
    assert header[:len(ml.TRAINING_COLUMNS)]==ml.TRAINING_COLUMNS
    assert json.loads(rows[0]['source_counts'])=={'VIIRS_SNPP_NRT':1}
    assert len(ml.dataset(out))==1 and 'source_counts' not in FEATURES


def test_v2_independent_evidence_excludes_nrt_sp_copies():
    from app.intelligence import sensor_evidence
    a, b = obs(), obs('VIIRS_SNPP_SP')
    summary = sensor_evidence([a, b])['sensor_summary']
    assert summary['independent_detection_count'] == 1
    assert summary['nrt_sp_representation_count'] == 1
    assert summary['cross_sensor_confirmed'] is False
    assert summary['modis_primary_thermal_mean'] is None
    summary = sensor_evidence([a, b, obs('MODIS_NRT')])['sensor_summary']
    assert summary['cross_sensor_confirmed'] is True
    assert summary['viirs_primary_thermal_mean'] == 330
    assert summary['modis_primary_thermal_mean'] == 320


def test_v2_legacy_resolution_requires_consistent_evidence():
    from review_progress import resolve_legacy_source
    row = validate(raw(version='2.0NRT'))
    assert resolve_legacy_source(row) == ('VIIRS_SNPP_NRT', 'documented_sensor_version')
    row['acquisition_query'] = {'source':'VIIRS_NOAA20_NRT'}
    assert resolve_legacy_source(row) == (None, 'ambiguous')
    unknown = validate(raw(version='2.0'))
    assert resolve_legacy_source(unknown) == (None, 'unresolved')
    unknown['latitude'] += 1
    unknown['acquisition_query'] = {'source':'VIIRS_SNPP_NRT'}
    assert resolve_legacy_source(unknown) == (None, 'ambiguous')


@pytest.fixture
def v2_store(monkeypatch):
    monkeypatch.setattr(settings,'demo_mode',False)
    monkeypatch.setattr(main,'firms_sync_lock',asyncio.Lock())
    def prohibited(*args,**kwargs):raise AssertionError('No training or alerts during acquisition')
    monkeypatch.setattr(ml,'train',prohibited);monkeypatch.setattr(main,'create_alerts',prohibited)
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine);factory=sessionmaker(engine,expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.mark.parametrize('source',list(FIRMS_SOURCES))
def test_v2_actual_ingested_counts_and_no_model_mutation(source,v2_store,tmp_path):
    import hashlib
    from acquire_review_candidates import ingest_batch
    from export_review_candidates import export_candidates
    from review_progress import model_v2_report
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ml.ARTIFACT,ml.META) if p.exists()}
    with v2_store() as db:
        asyncio.run(ingest_batch(db,[obs(source)],[]));db.commit()
    path=tmp_path/'candidates.csv';export_candidates(path,v2_store)
    report=model_v2_report(path,v2_store,tmp_path/'absent.csv')
    assert report['inventory_by_source'][source]['detections']==1
    assert report['inventory_by_source'][source]['events']==1
    assert report['totals']['v2_eligible']==0 and report['MODEL_V2_READY'] is False
    assert report['totals']['unreviewed']==1
    assert {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in before}==before


def test_v2_reconciliation_preserves_raw_identity(v2_store):
    from copy import deepcopy
    from review_progress import reconcile_legacy
    known=validate(raw(version='2.0NRT'));unknown=validate(raw(version='2.0',longitude='71'))
    snapshot=deepcopy(known)
    with v2_store() as db:
        db.add_all([Detection(id=r['id'],is_demo=False,payload=r) for r in (known,unknown)]);db.commit()
    report=reconcile_legacy(True,v2_store)
    assert report['resolved']==1 and report['unresolved']==1
    with v2_store() as db:
        result=db.get(Detection,known['id']).payload
        assert result['raw']==snapshot['raw'] and result['id']==snapshot['id']
        assert db.get(Detection,unknown['id']).payload==unknown


def test_v2_review_matrix_missingness_and_geographic_leakage(v2_store,tmp_path):
    from acquire_review_candidates import ingest_batch
    from export_review_candidates import export_candidates
    from review_common import read_csv,write_csv
    from review_progress import model_v2_report
    with v2_store() as db:
        asyncio.run(ingest_batch(db,[obs(),obs('MODIS_NRT'),obs(acq_date='2026-01-03')],[]));db.commit()
    path=tmp_path/'candidates.csv';export_candidates(path,v2_store)
    columns,rows,original=read_csv(path)
    for index,row in enumerate(rows):row.update(reviewed='true',reviewer='Fixture human',label=ml.CLASSES[0],source_reference='https://example.org/evidence',split_group=f'group_{index}',reviewed_at='2026-01-04T00:00:00+00:00')
    write_csv(path,columns+['reviewed_at'],rows,original)
    report=model_v2_report(path,v2_store,tmp_path/'absent.csv')
    assert report['class_sensor_matrix'][ml.CLASSES[0]]=={'SNPP':2,'NOAA20':0,'NOAA21':0,'MODIS':1}
    assert report['totals']['v2_eligible']==2
    assert report['reviewed_cross_sensor_events']==1
    assert report['reviewed_processing_kind']=={'nrt_only':2}
    assert report['missingness']['by_sensor']['MODIS']['missing']['ndvi']==1
    assert report['quality']['nearby_site_split_conflicts']
    assert report['MODEL_V2_READY'] is False


@pytest.mark.parametrize('timestamp',['','2026-01-02','2099-01-01T00:00:00+00:00','not-a-date'])
def test_v2_rejects_missing_invalid_or_future_review_timestamp(timestamp):
    from review_common import reviewed_errors
    row=ml.candidate_row(cluster([obs()])[0])
    row.update(reviewed='true',label=ml.CLASSES[0],reviewer='human',split_group='facility',source_reference='https://example.org/evidence',reviewed_at=timestamp)
    assert any('reviewed_at' in error for error in reviewed_errors(row,require_timestamp=True))


def test_v2_satellite_aliases_are_not_independent_sensors():
    from app.intelligence import sensor_evidence
    a=obs('VIIRS_NOAA20_NRT',satellite='1');b=obs('VIIRS_NOAA20_SP',satellite='N20')
    summary=sensor_evidence([a,b])['sensor_summary']
    assert summary['unique_satellite_count']==1
    assert summary['independent_detection_count']==1
    assert summary['cross_sensor_confirmed'] is False


def test_canonical_evidence_extension_preserves_labels_and_requires_new_review(v2_store,tmp_path):
    from acquire_review_candidates import ingest_batch
    from export_review_candidates import export_candidates
    from finalize_reviewed_labels import extend_sensor_evidence,finalize
    from review_common import read_csv,write_csv
    with v2_store() as db:
        asyncio.run(ingest_batch(db,[obs()],[]));db.commit()
    path=tmp_path/'canonical.csv';export_candidates(path,v2_store)
    _,rows,_=read_csv(path)
    original={key:rows[0][key] for key in ml.TRAINING_COLUMNS}
    original.update(reviewed='true',label=ml.CLASSES[0],reviewer='human',source_reference='https://example.org/evidence',split_group='facility')
    write_csv(path,ml.TRAINING_COLUMNS,[original],path.read_bytes())
    result=extend_sensor_evidence(path,v2_store)
    _,after,_=read_csv(path)
    assert all(after[0][key]==value for key,value in original.items())
    assert result['reapproved']==0 and after[0]['reviewed_at']==''
    assert after[0]['viirs_snpp_count']=='1'
    with pytest.raises(ValueError,match='reviewed_at'):finalize(path,tmp_path/'no_publish.csv')
