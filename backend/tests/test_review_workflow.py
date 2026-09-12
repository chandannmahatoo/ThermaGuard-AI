"""Isolated deterministic test fixtures only; never training data or real labels."""
import os
os.environ['DEMO_MODE'] = 'true'

import csv
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sklearn.impute import SimpleImputer

from app import ml
from app.database import Base, Event
from app.intelligence import FEATURES, CLASSES, features
from export_review_candidates import COLUMNS, export_candidates
from finalize_reviewed_labels import finalize
from prepare_review_row import update_review_row, main as prepare_main
from review_common import read_csv, write_csv
from review_event_summary import load_event, render_summary, main as summary_main
from review_progress import review_progress, main as progress_main


def write_rows(path, rows, columns=None):
    columns = columns or list(dict.fromkeys(COLUMNS + [key for row in rows for key in row]))
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def candidate(event_id='TG-test-one', **updates):
    row = {key: '' for key in COLUMNS}
    row.update(event_id=event_id, is_demo='false', reviewed='false', mean_frp='12.5')
    row.update(updates)
    return row


def reviewed(event_id='TG-test-one', **updates):
    row = candidate(event_id, label=CLASSES[0], reviewed='true', reviewer='TEST_ONLY_REVIEWER',
                    source_reference='https://example.org/evidence/record-1', split_group='TEST_ONLY_GROUP', reviewed_at='2026-01-02T00:00:00+00:00')
    row.update(updates)
    return row


def event(event_id='TG-test-one', demo=False):
    return dict(id=event_id, is_demo=demo, latitude=22.0, longitude=70.0,
                start_time='2026-01-01T00:00:00+00:00', last_seen_time='2026-01-01T01:00:00+00:00',
                detection_count=2, mean_frp=12.5, max_frp=15, mean_brightness=310, max_brightness=320,
                persistence_days=1, duration_hours=1, night_fraction=0,
                features={key: 12.5 if key == 'mean_frp' else None for key in FEATURES},
                context={'osm_context_available':False,'satellite_context_available':False,'ndvi':None,
                         'facilities':[{'name':'TEST_ONLY_FACILITY'}]},
                history={'recurrence_count':0,'historical_baseline_available':False,'historical_mean_frp':None},
                risk={'risk_score':8,'risk_level':'Normal','abnormality':{'abnormality_score':None,
                     'abnormality_status':'unavailable','baseline_available':False}})


@pytest.fixture
def store():
    engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread':False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory() as db:
        for item in [event(), event('TG-test-two'), event('TG-test-demo', True)]:
            db.add(Event(id=item['id'], is_demo=item['is_demo'], payload=item))
        db.commit()
    yield factory
    engine.dispose()


def test_summary_known_event_is_neutral_and_read_only(store):
    with store() as db:
        result = load_event('TG-test-one', db)
        summary = render_summary(result)
        assert 'event_id: TG-test-one' in summary
        assert 'mean_frp: 12.5' in summary and 'night_fraction: 0' in summary
        assert 'historical_baseline_available: No' in summary
        assert 'ndvi: Unavailable' in summary
        assert 'TEST_ONLY_FACILITY' in summary
        assert summary.count('[ ]') == 7 and '[x]' not in summary
        assert 'predicted_class' not in summary
        assert not db.dirty


@pytest.mark.parametrize('event_id', ['../../etc/passwd', 'TG-does-not-exist', 'TG-test-demo'])
def test_summary_invalid_missing_or_demo_event(store, event_id):
    with store() as db, pytest.raises(ValueError):
        load_event(event_id, db)


def test_summary_cli_missing_event_safe(monkeypatch, capsys):
    monkeypatch.setattr('review_event_summary.load_event', Mock(side_effect=ValueError('Event not found')))
    assert summary_main(['TG-missing']) == 1
    assert 'Event not found' in capsys.readouterr().err


def test_export_preserves_manual_fields_notes_and_exact_feature_order(tmp_path, store):
    path = tmp_path / 'candidates.csv'
    export_candidates(path, store)
    columns, rows, _ = read_csv(path)
    rows[0].update(label=CLASSES[1], reviewer='Human', split_group='region_period', source_reference='HUMAN_TEST_REFERENCE', reviewed='')
    rows[0]['review_notes'] = 'Keep commas, Unicode Δ and\nnewlines exactly'
    rows[1]['review_notes'] = ''
    write_rows(path, rows, columns + ['review_notes'])
    snapshot = path.read_bytes()
    result = export_candidates(path, store)
    header, actual, _ = read_csv(path)
    assert len(actual) == 2 and len({r['event_id'] for r in actual}) == 2
    assert header[:len(ml.TRAINING_COLUMNS)] == ml.TRAINING_COLUMNS
    assert header[7:7+len(FEATURES)] == FEATURES
    assert actual[0]['review_notes'] == rows[0]['review_notes']
    for key in ('label','reviewer','split_group','source_reference','reviewed'):
        assert actual[0][key] == rows[0][key]
    assert result['preserved'] == 2
    export_candidates(path, store)
    assert path.read_bytes() == snapshot


def test_export_appends_and_backs_up_removed_rows(tmp_path, store):
    path = tmp_path / 'candidates.csv'
    write_rows(path, [candidate('TG-removed')])
    before = path.read_bytes()
    result = export_candidates(path, store)
    assert result['removed'] == ['TG-removed']
    assert result['added'] == ['TG-test-one','TG-test-two']
    assert result['backup'].read_bytes() == before
    assert [row['event_id'] for row in read_csv(path)[1]] == result['added']


def test_export_rejects_duplicate_without_touching_file(tmp_path, store):
    path = tmp_path / 'candidates.csv'
    write_rows(path, [candidate(), candidate()])
    before = path.read_bytes()
    with pytest.raises(ValueError, match='Duplicate event_id'):
        export_candidates(path, store)
    assert path.read_bytes() == before


def test_export_refuses_changed_reviewed_evidence(tmp_path, store):
    path = tmp_path / 'candidates.csv'
    export_candidates(path, store)
    columns, rows, _ = read_csv(path)
    rows[0].update({k:v for k,v in reviewed().items() if k in ('label','reviewer','source_reference','split_group','reviewed')})
    write_rows(path, rows, columns)
    before = path.read_bytes()
    with store() as db:
        saved = db.get(Event, 'TG-test-one')
        saved.payload = {**saved.payload, 'features':{**saved.payload['features'], 'mean_frp':99}}
        db.commit()
    with pytest.raises(ValueError, match='reviewed evidence changed'):
        export_candidates(path, store)
    assert path.read_bytes() == before


def test_progress_counts_only_eligible_rows(tmp_path, capsys):
    path = tmp_path / 'candidates.csv'
    write_rows(path, [reviewed(), reviewed('TG-test-two',label=CLASSES[1],split_group='TEST_ONLY_GROUP_2'),
                      candidate('TG-test-three'), reviewed('TG-test-four',is_demo='true')])
    report = review_progress(path)
    assert report['total_candidates'] == 4 and report['reviewed_rows'] == 3
    assert report['eligible_rows'] == 2 and report['remaining_rows'] == 28
    assert report['class_counts'][CLASSES[0]] == 1 and report['class_counts'][CLASSES[1]] == 1
    assert len(report['missing_classes']) == 3
    assert report['split_groups'] == 2 and report['remaining_groups'] == 8
    assert report['row_completion_percent'] == pytest.approx(100 * 2 / 30)
    assert report['training_ready'] is False
    assert progress_main(['--candidates', str(path)]) == 0
    assert 'Training ready: NO' in capsys.readouterr().out


def test_prepare_read_only_does_not_write(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'candidates.csv'
    write_rows(path, [candidate()])
    before = path.read_bytes()
    monkeypatch.setattr('prepare_review_row.load_event', lambda _: event())
    assert prepare_main(['TG-test-one','--candidates',str(path)]) == 0
    assert path.read_bytes() == before and not (tmp_path/'backups').exists()
    assert 'No label selected' in capsys.readouterr().out


@pytest.mark.parametrize(('updates', 'message'), [
    ({'label':'invented_class','reviewer':'human','split_group':'region'}, 'Invalid label'),
    ({'reviewed':'yes','reviewer':'human','split_group':'region'}, 'reviewed must'),
    ({'reviewed':'true','label':CLASSES[0],'split_group':'region','source_reference':'TEST_ONLY'}, 'reviewer'),
    ({'reviewed':'true','label':CLASSES[0],'reviewer':'human','source_reference':'TEST_ONLY'}, 'split_group'),
    ({'reviewed':'true','label':CLASSES[0],'reviewer':'human','split_group':'region'}, 'source_reference'),
    ({'reviewed':'true','reviewer':'human','split_group':'region','source_reference':'TEST_ONLY'}, 'label'),
    ({'mean_frp':'99'}, 'Only label'),
])
def test_invalid_update_rejected_without_write(tmp_path, updates, message):
    path = tmp_path / 'candidates.csv'
    write_rows(path, [candidate()])
    before = path.read_bytes()
    with pytest.raises(ValueError, match=message):
        update_review_row(path, 'TG-test-one', updates)
    assert path.read_bytes() == before and not (tmp_path/'backups').exists()


def test_explicit_update_only_changes_target_metadata_and_creates_backup(tmp_path):
    path = tmp_path / 'candidates.csv'
    rows = [candidate(), candidate('TG-test-two')]
    write_rows(path, rows)
    before = path.read_bytes()
    changes = {'label':CLASSES[1],'reviewed':'true','reviewer':'Human','split_group':'region_period', 'source_reference':'https://example.org/evidence/record-2'}
    _, backup = update_review_row(path, 'TG-test-one', changes)
    after = read_csv(path)[1]
    assert backup.read_bytes() == before
    assert after[1] == {**rows[1], 'reviewed_at': ''}
    assert ml.valid_review_timestamp(after[0]['reviewed_at'])
    for key in COLUMNS:
        assert after[0][key] == changes.get(key, rows[0][key])
    with pytest.raises(ValueError, match='explicit --reviewed'):
        update_review_row(path,'TG-test-one',{'label':CLASSES[2]})


def test_review_only_columns_do_not_enter_features_and_missing_values_imputed(tmp_path):
    path = tmp_path / 'candidates.csv'
    write_rows(path, [reviewed(latitude='99',risk_score='100',nearby_facility_names='Not a numeric feature')])
    row = ml.dataset(path)[0]
    vector = features(row)
    assert len(vector) == len(FEATURES) == 31
    assert vector[FEATURES.index('mean_frp')] == 12.5
    assert all(np.isnan(v) for i,v in enumerate(vector) if FEATURES[i] != 'mean_frp')
    # This is an imputer-only unit check, never model training.
    imputed = SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True).fit_transform([vector])
    assert np.isfinite(imputed).all()
    assert not set(ml.ASSISTANCE_COLUMNS) & set(FEATURES)


def test_finalizer_exact_schema_and_backup_no_model_training(tmp_path, monkeypatch):
    path, out = tmp_path/'candidates.csv', tmp_path/'reviewed.csv'
    write_rows(path,[reviewed(),candidate('TG-test-two')])
    out.write_text('prior output must survive in backup\n')
    train = Mock(side_effect=AssertionError('Training forbidden in review workflow'))
    monkeypatch.setattr(ml,'train',train)
    result = finalize(path,out)
    assert result['published_rows'] == 1 and result['training_ready'] is False
    assert result['backup'].read_text() == 'prior output must survive in backup\n'
    assert read_csv(out)[0] == ml.TRAINING_COLUMNS + ['reviewed_at']
    assert len(ml.dataset(out)) == 1
    train.assert_not_called()


@pytest.mark.parametrize('values', [
    {'is_demo':'unknown'}, {'is_demo':''}, {'is_demo':'true'}, {'reviewer':' '},
    {'reviewed':' true '}, {'mean_frp':'NaN'}, {'mean_frp':''}, {'split_group':' group '},
])
def test_finalizer_refuses_rows_ml_would_skip_or_ambiguous_review(tmp_path, values):
    path, out = tmp_path/'candidates.csv', tmp_path/'reviewed.csv'
    write_rows(path,[reviewed(**values)])
    out.write_text('prior published data')
    with pytest.raises(ValueError):
        finalize(path,out)
    assert out.read_text() == 'prior published data'


def test_training_gate_unchanged():
    # In-memory gate counters only, not synthetic training records or a CSV.
    counters = [{'label':CLASSES[i % 5],'split_group':f'group-{i % 10}'} for i in range(30)]
    assert ml.readiness(counters)['training_ready']
    assert not ml.readiness(counters[:29])['training_ready']
    assert not ml.readiness([{**r,'split_group':f'group-{i % 9}'} for i,r in enumerate(counters)])['training_ready']
    assert not ml.readiness([{**r,'label':CLASSES[0]} for r in counters])['training_ready']


def test_safe_csv_replacement_detects_intervening_edit(tmp_path):
    path = tmp_path/'candidates.csv'
    write_rows(path,[candidate()])
    columns, rows, original = read_csv(path)
    edited = path.read_bytes() + b'\n'
    path.write_bytes(edited)
    with pytest.raises(ValueError, match='changed since'):
        write_csv(path,columns,rows,original)
    assert path.read_bytes() == edited
