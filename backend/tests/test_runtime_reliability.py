"""Local SQLite/provider regression tests. Fixtures are never reviewed training data."""
import os
os.environ['DEMO_MODE'] = 'true'
import asyncio
from copy import deepcopy
import time

import httpx
import pytest
from sqlalchemy import select, event as sql_event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app import main, providers, ml
from app.config import settings, Settings
from app.database import Base, Detection, Event, Alert, RuntimeSetting, make_engine, get_db
from app.intelligence import validate


def observation(lon=70, day='2026-01-01'):
    return validate(dict(latitude='22', longitude=str(lon), acq_date=day, acq_time='1200',
                         frp='10', bright_ti4='320', satellite='N', instrument='VIIRS',
                         confidence='n', daynight='D'))


def satellite_success():
    return dict(satellite_context_available=True, ndvi=0.3, acquisition_date='2026-01-01', provider='copernicus')


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'demo_mode', False)
    monkeypatch.setattr(settings, 'smtp_host', '')
    monkeypatch.setattr(main, 'firms_sync_lock', asyncio.Lock())
    monkeypatch.setattr(ml, 'predict', lambda e: {'predicted_class':None, 'reason':'isolated test'})
    async def osm(e):
        return dict(osm_context_available=True, landuse_class='industrial')
    async def satellite(e):
        return satellite_success()
    monkeypatch.setattr(providers, 'osm', osm)
    monkeypatch.setattr(providers, 'satellite', satellite)
    engine = make_engine('sqlite:///'+str(tmp_path/'runtime.db'))
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_sqlite_connection_pragmas(store):
    with store().get_bind().connect() as connection:
        assert connection.exec_driver_sql('PRAGMA journal_mode').scalar() == 'wal'
        assert connection.exec_driver_sql('PRAGMA foreign_keys').scalar() == 1
        assert connection.exec_driver_sql('PRAGMA busy_timeout').scalar() == 30000
        assert connection.exec_driver_sql('PRAGMA synchronous').scalar() == 2


def test_provider_await_has_no_transaction_and_other_writer_works(store, monkeypatch):
    with store() as db:
        async def satellite(e):
            assert not db.in_transaction()
            with store() as writer:
                writer.add(RuntimeSetting(key='during-provider', value={'ok':True}))
                writer.commit()
            await asyncio.sleep(0)
            return satellite_success()
        monkeypatch.setattr(providers, 'satellite', satellite)
        events = asyncio.run(main.process(db, [observation()]))
        assert len(events) == 1
        assert db.get(RuntimeSetting, 'during-provider') is not None


def test_repeat_sync_no_updates_no_provider_no_duplicates(store, monkeypatch):
    async def fetched(*args, **kwargs):
        return [observation()], 0
    monkeypatch.setattr(providers, 'firms', fetched)
    with store() as db:
        first = asyncio.run(main.sync(main.SyncInput(), user=None, db=db))
        assert first['ingested'] == 1
        statements = []
        def record(conn, cursor, statement, params, context, many):
            if statement.lstrip().upper().startswith('UPDATE EVENTS'):
                statements.append(statement)
        sql_event.listen(db.get_bind(), 'before_cursor_execute', record)
        async def forbidden(e):
            raise AssertionError('Unchanged successful context must be reused')
        monkeypatch.setattr(providers, 'satellite', forbidden)
        monkeypatch.setattr(providers, 'osm', forbidden)
        second = asyncio.run(main.sync(main.SyncInput(), user=None, db=db))
        assert second['ingested'] == 0 and second['unchanged_events'] == 1
        assert second['updated_events'] == 0 and second['satellite_requests_attempted'] == 0
        assert not statements
        assert len(list(db.scalars(select(Detection)))) == 1
        assert len(list(db.scalars(select(Event)))) == 1
        assert not list(db.scalars(select(Alert)))
        sql_event.remove(db.get_bind(), 'before_cursor_execute', record)


@pytest.mark.parametrize('other', ['current', 'history'])
def test_shared_guard_rejects_overlapping_ingestion(store, monkeypatch, other):
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        calls = 0
        async def firms(*args, **kwargs):
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return [], 0
        monkeypatch.setattr(providers, 'firms', firms)
        with store() as first, store() as second:
            task = asyncio.create_task(main.sync(main.SyncInput(), user=None, db=first))
            await started.wait()
            try:
                with pytest.raises(main.HTTPException) as error:
                    if other == 'current':
                        await main.sync(main.SyncInput(), user=None, db=second)
                    else:
                        await main.backfill_history(main.HistoricalSyncInput(bounds=[69,21,71,23],
                            start_date='2026-01-01', end_date='2026-01-01'), user=None, db=second)
                assert error.value.status_code == 409
                assert calls == 1
            finally:
                release.set()
                await task
            assert not main.firms_sync_lock.locked()
    asyncio.run(scenario())


def test_operational_error_rolls_back_and_retry_works(store, monkeypatch):
    with store() as db:
        asyncio.run(main.process(db, [observation()]))
        old = deepcopy(db.scalar(select(Event)).payload)
        db.rollback()
        original_commit = db.commit
        failed = False
        def fail_once():
            nonlocal failed
            if not failed:
                failed = True
                db.add(RuntimeSetting(key='must-rollback', value={'test':True}))
                raise OperationalError('private statement', {'secret':'must-not-appear'}, Exception('database is locked'))
            original_commit()
        async def firms(*args, **kwargs):
            return [], 0
        monkeypatch.setattr(providers, 'firms', firms)
        monkeypatch.setattr(db, 'commit', fail_once)
        with pytest.raises(main.HTTPException) as error:
            asyncio.run(main.sync(main.SyncInput(), user=None, db=db))
        assert error.value.status_code == 503
        assert error.value.detail == 'Database temporarily busy; retry synchronization.'
        assert not db.in_transaction() and db.is_active
        assert db.get(RuntimeSetting, 'must-rollback') is None
        assert db.scalar(select(Event)).payload == old
        result = asyncio.run(main.sync(main.SyncInput(), user=None, db=db))
        assert result['ingested'] == 0


def test_failed_forced_refresh_preserves_success(store, monkeypatch):
    with store() as db:
        first = asyncio.run(main.process(db, [observation()]))[0]
        async def failure(e):
            return {'satellite_context_available':False, 'ndvi':None, 'reason':'provider_unavailable'}
        monkeypatch.setattr(providers, 'satellite', failure)
        second = asyncio.run(main.process(db, [], refresh_satellite=True))[0]
        assert second['context']['ndvi'] == first['context']['ndvi']
        assert second['context']['satellite_context_available'] is True
        assert second['context']['satellite_refresh_status'] == 'failed'
        assert main.should_refresh_satellite(second, second['context'], second)


def test_material_change_refreshes_and_budget_defers(store, monkeypatch):
    monkeypatch.setattr(settings, 'satellite_events_per_sync', 1)
    with store() as db:
        first = asyncio.run(main.process(db, [observation()]))[0]
        changed = {**first, 'last_seen_time':'2026-01-02T12:00:00+00:00'}
        assert main.should_refresh_satellite(changed, first['context'], first)
        result = asyncio.run(main.process(db, [observation(71), observation(72)]))
        assert db.info['ingestion_stats']['satellite_requests_attempted'] == 1
        assert db.info['ingestion_stats']['enrichment_deferred_events'] >= 1
        assert sum(e['context'].get('satellite_refresh_status') == 'deferred' for e in result) == 1


def test_provider_timeout_keeps_ingestion_usable(store, monkeypatch):
    async def timeout(e):
        raise httpx.ReadTimeout('test transport')
    monkeypatch.setattr(providers, 'satellite', timeout)
    monkeypatch.setattr(providers, 'osm', timeout)
    with store() as db:
        result = asyncio.run(main.process(db, [observation()]))
        assert len(result) == 1 and len(list(db.scalars(select(Detection)))) == 1
        assert not result[0]['context']['satellite_context_available']
        assert db.is_active


def test_zero_rows_success_and_secret_safe_operational_log(store, monkeypatch, caplog):
    async def firms(*args, **kwargs):
        return [], 0
    monkeypatch.setattr(providers, 'firms', firms)
    with store() as db:
        assert asyncio.run(main.sync(main.SyncInput(), user=None, db=db))['ingested'] == 0
    assert 'secret' not in caplog.text


@pytest.mark.parametrize('field', ['satellite_events_per_sync', 'firms_timeout_seconds', 'osm_timeout_seconds',
                                  'copernicus_token_timeout_seconds', 'copernicus_stats_timeout_seconds'])
def test_positive_provider_settings(field):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **{field:0})


def test_both_local_cors_origins():
    config = Settings(_env_file=None, cors_origins='http://localhost:3000')
    assert set(config.allowed_cors_origins) == {'http://localhost:3000','http://127.0.0.1:3000'}
    assert '*' not in config.allowed_cors_origins


@pytest.fixture
def oauth(monkeypatch):
    original = httpx.AsyncClient
    providers._token_cache.clear()
    monkeypatch.setattr(providers, '_token_lock', asyncio.Lock())
    def install(handler):
        monkeypatch.setattr(providers.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    yield install
    providers._token_cache.clear()


def test_valid_cached_token_no_network(oauth):
    providers._token_cache.update(token='fixture', expires=time.monotonic()+60)
    def forbidden(req):
        raise AssertionError('Must reuse token')
    oauth(forbidden)
    assert asyncio.run(providers._copernicus_token({}))[0] == 'fixture'


def test_expired_and_concurrent_token_refresh_once(oauth):
    calls = 0
    async def handler(req):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return httpx.Response(200, json={'access_token':'fixture-new','expires_in':300})
    oauth(handler)
    providers._token_cache.update(token='fixture-old', expires=time.monotonic()-1)
    async def scenario():
        return await asyncio.gather(*[providers._copernicus_token({}) for _ in range(5)])
    assert all(token == 'fixture-new' and error is None for token,error in asyncio.run(scenario()))
    assert calls == 1


@pytest.mark.parametrize('last_status', [200, 401, 403])
def test_statistics_auth_refresh_once(oauth, last_status):
    token_calls = 0
    stats_calls = 0
    def handler(req):
        nonlocal token_calls, stats_calls
        if 'openid-connect' in str(req.url):
            token_calls += 1
            return httpx.Response(200,json={'access_token':'fixture-new','expires_in':300})
        stats_calls += 1
        return httpx.Response(401 if stats_calls == 1 else last_status,json={'data':[]})
    oauth(handler)
    providers._token_cache.update(token='fixture-old', expires=time.monotonic()+60)
    coroutine = providers._statistics_response('https://example.org/statistics', {}, 'fixture-old', {})
    if last_status == 200:
        assert asyncio.run(coroutine) == ({'data':[]}, None)
    else:
        with pytest.raises(httpx.HTTPStatusError):
            asyncio.run(coroutine)
    assert token_calls == 1 and stats_calls == 2


@pytest.mark.parametrize('response', [httpx.Response(503,text='secret-marker'), httpx.Response(200,text='not json'),
                                    httpx.Response(200,json={'access_token':'','expires_in':300})])
def test_oauth_failure_is_safe(oauth, response, caplog):
    oauth(lambda req: response)
    token,error = asyncio.run(providers._copernicus_token({'satellite_context_available':False}))
    assert token is None and error['reason'] == 'provider_unavailable'
    assert 'secret-marker' not in caplog.text


def test_failed_dependency_rolls_back(store, monkeypatch):
    import app.database as database
    monkeypatch.setattr(database, 'Session', store)
    dependency = get_db()
    db = next(dependency)
    db.add(RuntimeSetting(key='failed',value={}))
    db.flush()
    with pytest.raises(RuntimeError):
        dependency.throw(RuntimeError('test failure'))
    with store() as check:
        assert check.get(RuntimeSetting, 'failed') is None


def test_event_update_operational_error_preserves_old_event(store, monkeypatch):
    with store() as db:
        original = asyncio.run(main.process(db, [observation()]))[0]
        old = deepcopy(original)
        async def changed(e):
            return {**satellite_success(), 'ndvi':0.4}
        monkeypatch.setattr(providers, 'satellite', changed)
        def locked(conn, cursor, statement, params, context, many):
            if statement.lstrip().upper().startswith('UPDATE EVENTS'):
                raise OperationalError('UPDATE events', {}, Exception('database is locked'))
        sql_event.listen(db.get_bind(), 'before_cursor_execute', locked)
        with pytest.raises(OperationalError):
            asyncio.run(main.process(db, [], refresh_satellite=True))
        assert db.is_active and not db.in_transaction()
        sql_event.remove(db.get_bind(), 'before_cursor_execute', locked)
        assert db.get(Event, old['id']).payload == old
        result = asyncio.run(main.process(db, [], refresh_satellite=True))
        assert result[0]['context']['ndvi'] == 0.4


def test_alert_acknowledgement_and_smtp_outside_transaction(store, monkeypatch):
    from app.database import Organization, AreaAssignment, User
    with store() as db:
        org = Organization(name='Test organization', email='fixture@example.invalid')
        db.add(org)
        db.flush()
        db.add(AreaAssignment(organization_id=org.id, area_name='test', bounds=[69,21,71,23], minimum_alert_level='Normal'))
        db.add(RuntimeSetting(key='alert_threshold', value={'threshold':0}))
        db.add(User(email='subscriber@example.invalid',password='test-only',role='admin',notifications_enabled=True,latitude=22,longitude=70))
        db.commit()
        monkeypatch.setattr(settings, 'smtp_host', 'test.invalid')
        monkeypatch.setattr(settings, 'smtp_from', 'fixture@example.invalid')
        monkeypatch.setattr(settings,'smtp_enabled',True)
        monkeypatch.setattr(settings,'smtp_user','fixture@example.invalid')
        monkeypatch.setattr(settings,'smtp_password','test-only')
        sent = []
        class SMTP:
            def __init__(self, *args, **kwargs):
                assert not db.in_transaction()
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def ehlo(self): pass
            def starttls(self, **kwargs): pass
            def login(self, *args): pass
            def send_message(self, message): sent.append(True)
        monkeypatch.setattr(main.smtplib, 'SMTP', SMTP)
        asyncio.run(main.process(db, [observation()]))
        alert = db.scalar(select(Alert))
        assert alert.notification_status.endswith('email_sent')
        alert.status = 'acknowledged'
        db.commit()
        asyncio.run(main.process(db, [observation()]))
        assert len(list(db.scalars(select(Alert)))) == 1
        assert db.scalar(select(Alert)).status == 'acknowledged'
        assert len(sent) == 1


def test_satellite_exhausted_auth_retry_returns_reason(oauth, monkeypatch):
    monkeypatch.setattr(settings, 'copernicus_client_id', 'fixture-id')
    monkeypatch.setattr(settings, 'copernicus_client_secret', 'fixture-secret')
    stats = []
    def handler(req):
        if 'openid-connect' in str(req.url):
            return httpx.Response(200,json={'access_token':'fixture-new','expires_in':300})
        stats.append(True)
        return httpx.Response(401,json={'detail':'rejected'})
    oauth(handler)
    providers._token_cache.update(token='fixture-old',expires=time.monotonic()+60)
    result = asyncio.run(providers.satellite({'latitude':22,'longitude':70,'last_seen_time':'2026-01-01T12:00:00+00:00'}))
    assert result['reason'] == 'provider_auth_failed'
    assert len(stats) == 2
