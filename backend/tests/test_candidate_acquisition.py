"""Temporary synthetic fixtures for software tests only; no production data or training."""
import os
os.environ['DEMO_MODE'] = 'true'
import asyncio
from copy import deepcopy
import csv
import json

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main, ml
from app.config import settings
from app.database import Base, Detection, Event, Alert
from app.intelligence import validate, FEATURES, CLASSES, features
from app.ml import valid_source_reference
from acquire_review_candidates import (parse_plan, chunks, ingest_batch, acquire,
                                        ReviewConflict, verify_protected)
from candidate_inventory import inventory, cohort_for
from export_review_candidates import export_candidates, COLUMNS
from export_review_packets import export_packets
from review_common import read_csv, write_csv, reviewed_errors
from review_queue import review_queue


def plan(**changes):
    entry = dict(name='zone_one', bounds=[69, 21, 71, 23], start_date='2026-01-01',
                 end_date='2026-01-11', source='VIIRS_SNPP_NRT', max_observations=50)
    entry.update(changes)
    return {'regions': [entry], 'target_candidates': 40}


def observation(lon=70, day='2026-01-01', demo=False):
    return validate(dict(latitude='22', longitude=str(lon), acq_date=day, acq_time='1200',
                         frp='10', bright_ti4='320', satellite='N', instrument='VIIRS',
                         confidence='n', daynight='D'), is_demo=demo)


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setattr(settings, 'demo_mode', False)
    def prohibited(*args, **kwargs):
        raise AssertionError('No alerts, training or live enrichment allowed')
    monkeypatch.setattr(main, 'create_alerts', prohibited)
    monkeypatch.setattr(ml, 'train', prohibited)
    monkeypatch.setattr(main.providers, 'osm', prohibited)
    monkeypatch.setattr(main.providers, 'satellite', prohibited)
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def seed(store, path):
    with store() as db:
        asyncio.run(ingest_batch(db, [observation()], []))
        db.commit()
    export_candidates(path, store)
    columns, rows, original = read_csv(path)
    rows[0].update(reviewed='true', label=CLASSES[1], reviewer='Test reviewer',
                   source_reference='https://example.org/evidence/report-1', split_group='zone_jan_2026',
                   custom_notes='Human note\nwith a comma, preserved')
    write_csv(path, columns+['custom_notes'], rows, original)
    return rows


def test_plan_and_five_day_chunks():
    parsed = parse_plan(plan())
    assert list(chunks(parsed['regions'][0])) == [('2026-01-01',5), ('2026-01-06',5), ('2026-01-11',1)]


@pytest.mark.parametrize('bounds', [[1,2,3], [71,21,69,23], [69,23,71,21], [-181,0,0,1], [0,0,float('nan'),1], [True,0,2,1]])
def test_invalid_bounds(bounds):
    with pytest.raises(ValueError):
        parse_plan(plan(bounds=bounds))


@pytest.mark.parametrize('changes', [dict(start_date='bad'), dict(end_date='2025-12-01'),
    dict(end_date='2099-01-01'), dict(end_date='2027-01-02'), dict(source='../bad'),
    dict(max_observations=-1), dict(name='')])
def test_invalid_plan(changes):
    with pytest.raises(ValueError):
        parse_plan(plan(**changes))


def test_duplicate_handling_and_no_alerts(store):
    row = observation()
    with store() as db:
        report = asyncio.run(ingest_batch(db, [row, row], []))
        db.commit()
        assert report['new_detections'] == 1 and report['duplicate_observations'] == 1
        second = asyncio.run(ingest_batch(db, [row], []))
        db.commit()
        assert second['new_detections'] == 0 and second['existing_detections'] == 1
        assert len(list(db.scalars(select(Event)))) == 1
        assert not list(db.scalars(select(Alert)))


def test_demo_rejected(store):
    with store() as db, pytest.raises(ValueError, match='real NASA'):
        asyncio.run(ingest_batch(db, [observation(demo=True)], []))


def test_mismatched_raw_rejected(store):
    row = observation()
    row['frp'] = 999
    with store() as db, pytest.raises(ValueError, match='provenance'):
        asyncio.run(ingest_batch(db, [row], []))


def test_review_change_rolls_back_instead_of_transferring_label(store, tmp_path):
    path = tmp_path/'review.csv'
    rows = seed(store, path)
    before = path.read_bytes()
    # Close earlier observation changes ID and membership; must rollback both tables.
    with store() as db, pytest.raises(ReviewConflict):
        asyncio.run(ingest_batch(db, [observation(lon=70.001, day='2025-12-31')], rows))
    with store() as db:
        assert len(list(db.scalars(select(Detection)))) == 1
        assert db.get(Event, rows[0]['event_id']) is not None
    assert path.read_bytes() == before


def test_missing_review_export_refused(store, tmp_path):
    path = tmp_path/'review.csv'
    rows = seed(store, path)
    before = path.read_bytes()
    with store() as db:
        db.delete(db.get(Event, rows[0]['event_id']))
        db.commit()
    with pytest.raises(ValueError, match='Reviewed event IDs disappeared'):
        export_candidates(path, store)
    assert path.read_bytes() == before


def test_preserved_context_review_backup_and_export_idempotency(store, tmp_path):
    path = tmp_path/'review.csv'
    reviewed = seed(store, path)[0]
    # Prove successful saved context survives subsequent historical processing.
    with store() as db:
        item = db.get(Event, reviewed['event_id'])
        updated = deepcopy(item.payload)
        updated['context'].update(osm_context_available=True, satellite_context_available=True,
                                  ndvi=0.3, acquisition_date='2026-01-01')
        item.payload = updated
        db.commit()
        asyncio.run(main.process(db, [], enrich=False, create_notifications=False))
    # Refresh this temporary test snapshot explicitly to match its newly seeded context.
    columns, rows, original = read_csv(path)
    with store() as db:
        fresh = ml.candidate_row(db.get(Event, reviewed['event_id']).payload)
    for k in FEATURES+ml.ASSISTANCE_COLUMNS:
        rows[0][k] = '' if fresh.get(k) is None else str(fresh[k])
    write_csv(path, columns, rows, original)
    before_row = read_csv(path)[1][0]
    async def provider(**kwargs):
        return [observation(lon=70.8)], 0
    result = asyncio.run(acquire(plan(end_date='2026-01-01'), candidates=path,
                                 session_factory=store, provider=provider))
    assert result['batches'][0]['new_detections'] == 1
    assert result['no_alerts'] and not result['training_performed']
    after = {r['event_id']:r for r in read_csv(path)[1]}
    assert after[before_row['event_id']] == before_row
    assert len(after) == 2
    assert list((tmp_path/'backups').glob('review.pre_acquisition.*.csv'))
    content = path.read_bytes()
    assert export_candidates(path, store)['backup'] is None
    assert path.read_bytes() == content


def test_dry_run_does_not_fetch_or_write(tmp_path):
    async def provider(**kwargs):
        raise AssertionError('Dry-run must not fetch')
    report = asyncio.run(acquire(plan(), dry_run=True, candidates=tmp_path/'absent.csv', provider=provider))
    assert report['provider_requests'] == 0 and report['planned_requests'] == 3
    assert not list(tmp_path.iterdir())


def test_real_mode_required(store, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'demo_mode', True)
    with pytest.raises(ValueError, match='DEMO_MODE=false'):
        asyncio.run(acquire(plan(), candidates=tmp_path/'absent.csv'))


@pytest.mark.parametrize('reference', ['REAL_SOURCE_OR_EVIDENCE_HERE', 'your verified evidence source',
    'TODO', 'TBD', 'test', 'placeholder', 'N/A', '', 's', 'abc', '        ', 'TEST_ONLY_NOT_REAL',
    'TODO: find evidence', 'xxxxxxxxxxxxx'])
def test_placeholder_rejected(reference):
    assert not valid_source_reference(reference)
    assert any('source_reference' in e for e in reviewed_errors({'source_reference':reference}))


@pytest.mark.parametrize('reference', ['https://example.org/incident/report-2026-01',
    'District archive: incident register 123, 2026-01-01, page 12', 'doi:10.1234/thermal.2026'])
def test_meaningful_reference_syntax_accepted(reference):
    assert valid_source_reference(reference)


def test_placeholder_ineligible_in_ml_and_finalization(store, tmp_path):
    path = tmp_path/'review.csv'
    seed(store, path)
    columns, rows, original = read_csv(path)
    rows[0]['source_reference'] = 'REAL_SOURCE_OR_EVIDENCE_HERE'
    write_csv(path, columns, rows, original)
    assert ml.dataset(path) == []
    assert any('placeholder' in p for p in ml.candidate_report(path)['problems'])
    from finalize_reviewed_labels import finalize
    with pytest.raises(ValueError, match='source_reference'):
        finalize(path, tmp_path/'labels.csv')
    assert not (tmp_path/'labels.csv').exists()


def test_packets_inventory_queue_and_no_feature_leak(store, tmp_path):
    path = tmp_path/'review.csv'
    reviewed = seed(store, path)
    with store() as db:
        asyncio.run(ingest_batch(db, [observation(lon=70.8)], reviewed))
        db.commit()
    export_candidates(path, store)
    before = path.read_bytes()
    paths = export_packets(path, tmp_path/'packets', store)
    assert len(paths) == 1
    text = paths[0].read_text()
    assert 'NASA FIRMS' in text and 'VIIRS' in text
    assert 'Potential evidence to verify manually' in text
    assert 'NOT verified incident evidence' in text
    assert all(label not in text for label in CLASSES)
    assert 'predicted_class' not in text and 'class_probabilities' not in text
    zones = tmp_path/'plan.json'
    zones.write_text(json.dumps(plan()))
    rows, summary = inventory(path, zones)
    assert summary['total'] == 2 and summary['reviewed'] == 1
    assert summary['distinct_geographic_cohorts'] == 1
    assert len({r['suggested_cohort'] for r in rows}) == 1
    assert len(review_queue(rows)) == 1
    assert len(review_queue(rows, reviewed='all', region='zone_one', start_date='2026-01-01', end_date='2026-01-01')) == 2
    assert not review_queue(rows, region='other')
    assert not review_queue(rows, landuse='forest')
    assert len(review_queue(rows, reviewed='true', cohort='zone_jan_2026')) == 1
    assert path.read_bytes() == before
    for row in rows:
        parsed = {**row, **{k: float(row[k]) if row.get(k) else None for k in FEATURES}}
        assert len(features(parsed)) == len(FEATURES)
        assert 'suggested_cohort' not in FEATURES and 'region' not in FEATURES
    assert all(not r['split_group'] for r in rows if r['reviewed'] == 'false')


def test_gate_unchanged():
    rows = [dict(label=CLASSES[i%5],split_group=f'group-{i%10}') for i in range(30)]
    assert ml.readiness(rows)['training_ready']
    assert not ml.readiness(rows[:29])['training_ready']
    assert not ml.readiness([{**r,'split_group':'one'} for r in rows])['training_ready']
    assert not ml.readiness([{**r,'label':CLASSES[0]} for r in rows])['training_ready']


def test_id_reconciliation_requires_identical_evidence():
    verify_protected([{'id':'TG-one','value':1}], {'TG-one':{'id':'TG-one','value':1}})
    with pytest.raises(ReviewConflict):
        verify_protected([{'id':'TG-two','value':1}], {'TG-one':{'id':'TG-one','value':1}})


def test_frozen_stale_review_is_preserved_and_new_overlap_refused(store, tmp_path):
    path=tmp_path/'candidates.csv'
    rows=seed(store,path)
    with store() as db:
        item=db.get(Event,rows[0]['event_id'])
        changed=deepcopy(item.payload);changed['context']['landuse_class']='forest'
        item.payload=changed;db.commit()
        protected=deepcopy(item.payload)
        asyncio.run(ingest_batch(db,[observation(lon=73)],rows,freeze_reviewed=True));db.commit()
        assert db.get(Event,item.id).payload==protected
        with pytest.raises(ValueError,match='Frozen reviewed event'):
            asyncio.run(ingest_batch(db,[observation(lon=70.001)],rows,freeze_reviewed=True))
        assert len(list(db.scalars(select(Detection))))==2
    export_candidates(path,store,freeze_reviewed=True)
    actual={r['event_id']:r for r in read_csv(path)[1]}
    assert all(actual[rows[0]['event_id']][k]==v for k,v in rows[0].items())


def test_enrichment_outside_transaction_and_review_preservation(store,tmp_path,monkeypatch):
    from acquire_review_candidates import enrich_unreviewed
    path=tmp_path/'candidates.csv';rows=seed(store,path)
    with store() as db:
        asyncio.run(ingest_batch(db,[observation(lon=73)],rows));db.commit()
        before=deepcopy(db.get(Event,rows[0]['event_id']).payload)
    export_candidates(path,store)
    async def osm(event):
        # An independent writer can reserve SQLite while provider work runs.
        with store() as db:db.connection().exec_driver_sql('BEGIN IMMEDIATE');db.rollback()
        return {'osm_context_available':True,'facilities':[]}
    async def satellite(event):return {'satellite_context_available':False,'reason':'fixture_unavailable'}
    monkeypatch.setattr(main.providers,'osm',osm);monkeypatch.setattr(main.providers,'satellite',satellite)
    monkeypatch.setattr(main,'firms_sync_lock',asyncio.Lock())
    result=asyncio.run(enrich_unreviewed(candidates=path,session_factory=store))
    assert result['updated_events']==1 and result['osm_available']==1
    with store() as db:assert db.get(Event,rows[0]['event_id']).payload==before
