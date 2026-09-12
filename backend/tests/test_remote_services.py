"""Network AI, subscriber alerts and SMTP contracts; providers are always mocked."""
import asyncio
from copy import deepcopy
import json
import smtplib
import sys
from types import SimpleNamespace

import pytest
import requests
import httpx
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import ValidationError
from sqlalchemy import create_engine,select,text,inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# test_system must be imported first: it pins DEMO_MODE=true before app.config is loaded,
# so standalone file runs get the demo-seeded fixture database the client fixture expects.
from test_system import client,auth
from app import main
from app.config import Settings,settings
from app.database import Base,User,Event,Alert,Organization,AreaAssignment,EmailNotification,RuntimeSetting,migrate_notification_preferences


@pytest.fixture
def network(monkeypatch):
    for key,value in dict(gemini_enabled=True,gemini_api_key='TEST_API_SECRET',gemini_model='fixture-model',gemini_timeout_seconds=30,
        smtp_enabled=True,smtp_host='smtp.example',smtp_port=587,smtp_user='sender@example.org',smtp_password='TEST_SMTP_SECRET',smtp_from='sender@example.org',smtp_timeout_seconds=20).items():
        monkeypatch.setattr(settings,key,value)
    monkeypatch.setattr(main,'_gemini_client',None)
    monkeypatch.setattr(main,'_gemini_client_signature',None)
    return lambda handler: pytest.fail('Gemini is mocked at the SDK boundary; no HTTP transport is expected')


def gemini_reply(text):
    return genai_types.GenerateContentResponse.model_validate({'candidates':[{'content':{'parts':[{'text':text}]}}]})


def test_gemini_success_extracts_answer_and_model(network,monkeypatch):
    calls=[]
    class FakeModels:
        def generate_content(self,model,contents,config=None):calls.append((model,config));return gemini_reply('  OK  ')
    monkeypatch.setattr(main,'_gemini_client_instance',lambda:SimpleNamespace(models=FakeModels()))
    result=main._call_gemini('prompt',system='rules')
    assert result=={'reachable':True,'response_ok':True,'answer':'OK','reason':None}
    assert calls[0][0]=='fixture-model' and calls[0][1].system_instruction=='rules'


@pytest.mark.parametrize('failure,expected',[
    (401,'authentication_failed'),(403,'permission_denied'),(429,'quota_or_rate_limited'),
    (404,'model_unavailable'),(500,'provider_error'),('timeout','timeout'),('connection','network_error'),
    ('httpx_timeout','timeout'),('httpx_connection','network_error'),
    ('safety','empty_response'),('unexpected','unexpected_error')])
def test_gemini_failure_categories_without_secret_leak(network,monkeypatch,failure,expected):
    class FakeModels:
        def generate_content(self,model,contents,config=None):
            if failure=='httpx_timeout':raise httpx.ReadTimeout('TEST_API_SECRET')
            if failure=='httpx_connection':raise httpx.ConnectError('TEST_API_SECRET')
            if failure=='timeout':raise requests.exceptions.Timeout('TEST_API_SECRET')
            if failure=='connection':raise requests.exceptions.ConnectionError('TEST_API_SECRET')
            if failure=='unexpected':raise RuntimeError('TEST_API_SECRET')
            if failure=='safety':return genai_types.GenerateContentResponse.model_validate({'candidates':[{'finishReason':'SAFETY'}]})
            raise genai_errors.APIError(code=failure,response_json={'error':{'message':'TEST_API_SECRET'}})
    monkeypatch.setattr(main,'_gemini_client_instance',lambda:SimpleNamespace(models=FakeModels()))
    result=main._call_gemini('prompt')
    assert result['reason']==expected and result['response_ok'] is False
    assert 'TEST_API_SECRET' not in json.dumps(result)


def test_no_sdk_call_when_unconfigured(network,monkeypatch):
    monkeypatch.setattr(settings,'gemini_api_key','')
    def forbidden(prompt):raise AssertionError('Provider must not be called when unconfigured')
    monkeypatch.setattr(main,'_call_gemini',forbidden)
    result=asyncio.run(main.gemini_request('test'))
    assert result['response_ok'] is False and result['reason']=='disabled_or_unconfigured'


def test_gemini_client_reused_until_key_changes(monkeypatch):
    constructed=[]
    class FakeClient:
        def __init__(self,**kwargs):constructed.append(kwargs['api_key']);self.models=SimpleNamespace(generate_content=lambda model,contents:gemini_reply('OK'))
    monkeypatch.setattr(sys.modules['google'],'genai',SimpleNamespace(Client=lambda **kw:FakeClient(**kw)))
    monkeypatch.setattr(main,'_gemini_client',None);monkeypatch.setattr(main,'_gemini_client_signature',None)
    monkeypatch.setattr(settings,'gemini_api_key','KEY_ONE');monkeypatch.setattr(settings,'gemini_model','fixture-model')
    first=main._gemini_client_instance();second=main._gemini_client_instance()
    assert first is second and constructed==['KEY_ONE']
    monkeypatch.setattr(settings,'gemini_api_key','KEY_TWO')
    assert main._gemini_client_instance() is not first and constructed==['KEY_ONE','KEY_TWO']
    main._gemini_client=None;main._gemini_client_signature=None


@pytest.mark.parametrize('failure',[401,403,410,429,500,'timeout','connection','json','missing','empty'])
def test_selected_event_network_failure_uses_fallback(client,network,monkeypatch,failure):
    c,_=client;headers=auth(c);before=c.get('/api/v1/events',headers=headers).json()
    def failing(prompt,system=None):
        if failure=='timeout':raise requests.exceptions.Timeout('TEST_API_SECRET')
        if failure=='connection':raise requests.exceptions.ConnectionError('TEST_API_SECRET')
        if failure in ('json','missing','empty'):return {'reachable':True,'response_ok':False,'reason':'empty_response'}
        raise genai_errors.APIError(code=failure,response_json={'error':{'message':'TEST_API_SECRET'}})
    monkeypatch.setattr(main,'_call_gemini',failing)
    result=c.post('/api/v1/copilot/chat',headers=headers,json={'event_id':before[0]['id'],'question':'Explain'}).json()
    assert result['mode']=='deterministic_fallback' and before[0]['id'] in result['answer']
    assert 'TEST_API_SECRET' not in json.dumps(result)
    assert c.get('/api/v1/events',headers=headers).json()==before


@pytest.mark.parametrize('selected',[False,True])
def test_copilot_sends_question_and_scoped_evidence(client,network,monkeypatch,selected):
    c,_=client;headers=auth(c)
    before=c.get('/api/v1/events',headers=headers).json()
    calls=[]
    def reply(prompt,system=None):
        calls.append((json.loads(prompt),system))
        return {'response_ok':True,'answer':'Evidence answer','reason':None}
    monkeypatch.setattr(main,'_call_gemini',reply)
    body={'question':'Which evidence is missing?'}
    if selected:body['event_id']=before[0]['id']
    result=c.post('/api/v1/copilot/chat',headers=headers,json=body).json()
    assert result['mode']=='gemini'
    packet,rules=calls[0]
    assert packet['question']==body['question']
    expected=[before[0]] if selected else sorted(before,key=lambda e:e['risk']['risk_score'],reverse=True)[:10]
    assert packet['events']==[main.copilot_evidence(e) for e in expected]
    assert rules==main.COPILOT_RULES
    assert c.get('/api/v1/events',headers=headers).json()==before


def test_single_event_packet_is_detached_and_allowlisted():
    event={'id':'one','classification':{'predicted_class':'test'},'risk':{'risk_score':3},'context':{'ndvi':None,'secret':'do not send'},'raw_secret':'do not send'}
    packet=main.copilot_evidence(event)
    packet['classification']['predicted_class']='changed'
    assert event['classification']['predicted_class']=='test'
    assert 'secret' not in json.dumps(packet)


def test_diagnostics_admin_only(client,network,monkeypatch):
    c,_=client
    for path in ('gemini','smtp'):
        assert c.post('/api/v1/admin/diagnostics/'+path).status_code==401
        assert c.post('/api/v1/admin/diagnostics/'+path,headers=auth(c,operator=True)).status_code==403
    monkeypatch.setattr(main,'_call_gemini',lambda prompt:{'reachable':True,'response_ok':True,'answer':'THERMAGUARD GEMINI OK','reason':None})
    result=c.post('/api/v1/admin/diagnostics/gemini',headers=auth(c)).json()
    assert result['response_ok'] and result['provider']=='gemini' and 'answer' not in result and 'TEST_API_SECRET' not in json.dumps(result)
    monkeypatch.setattr(main,'send_smtp_message',lambda message:{'sent':True,'reason':None})
    assert c.post('/api/v1/admin/diagnostics/smtp',headers=auth(c)).json()['sent']


@pytest.mark.parametrize('failure',[None,'auth','connect','send'])
def test_smtp_flow_and_safe_errors(network,monkeypatch,caplog,failure):
    calls=[]
    class SMTP:
        def __init__(self,host,port,timeout):
            assert (host,port,timeout)==('smtp.example',587,20)
            if failure=='connect':raise OSError('TEST_SMTP_SECRET')
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def ehlo(self):calls.append('ehlo')
        def starttls(self,context):assert context.check_hostname;calls.append('tls')
        def login(self,user,password):
            assert (user,password)==('sender@example.org','TEST_SMTP_SECRET');calls.append('login')
            if failure=='auth':raise smtplib.SMTPAuthenticationError(535,b'TEST_SMTP_SECRET')
        def send_message(self,message):
            calls.append('send')
            if failure=='send':raise smtplib.SMTPDataError(554,b'TEST_SMTP_SECRET')
    monkeypatch.setattr(main.smtplib,'SMTP',SMTP)
    result=main.send_smtp_message(main.EmailMessage())
    assert result['sent']==(failure is None)
    if failure is None:assert calls==['ehlo','tls','ehlo','login','send']
    assert 'TEST_SMTP_SECRET' not in caplog.text+json.dumps(result)


def test_smtp_disabled_never_connects(network,monkeypatch):
    monkeypatch.setattr(settings,'smtp_enabled',False)
    monkeypatch.setattr(main.smtplib,'SMTP',lambda *a,**kw:pytest.fail('must not connect'))
    assert main.send_smtp_message(main.EmailMessage())['reason']=='smtp_disabled'


@pytest.mark.parametrize('change,eligible',[
    ({},True),({'latitude':23},False),({'notifications_enabled':False},False),({'email':''},False),
    ({'email':'bad\n@example.org'},False),({'latitude':None},False),({'longitude':None},False),
    ({'latitude':22.1,'alert_radius_km':20},True),({'latitude':22.1,'alert_radius_km':1},False),
    ({'latitude':22.05,'alert_radius_km':None},True),({'latitude':float('nan')},False)])
def test_subscriber_radius_eligibility(change,eligible,monkeypatch):
    monkeypatch.setattr(settings,'default_alert_radius_km',10)
    user=SimpleNamespace(**{'email':'user@example.org','latitude':22,'longitude':70,'alert_radius_km':None,'notifications_enabled':True,**change})
    assert (main.subscriber_distance(user,{'latitude':22,'longitude':70}) is not None)==eligible


@pytest.fixture
def store(network):
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine);factory=sessionmaker(engine,expire_on_commit=False)
    with factory() as db:
        org=Organization(name='Fixture',email='org@example.org');db.add(org);db.flush()
        db.add(AreaAssignment(organization_id=org.id,area_name='fixture',bounds=[69,21,71,23],minimum_alert_level='Normal'))
        db.add(User(email='subscriber@example.org',password='test-only',role='admin',latitude=22,longitude=70,notifications_enabled=True))
        db.add(RuntimeSetting(key='alert_threshold',value={'threshold':80}));db.commit()
    yield factory
    engine.dispose()


def fixture_event(score=90):
    return {'id':'fixture-event','is_demo':False,'latitude':22,'longitude':70,'start_time':'2026-01-01T12:00:00+00:00',
        'detection_ids':['one','two'],'detection_count':2,'risk':{'risk_score':score,'risk_level':'High'},
        'classification':{'predicted_class':None,'classification_confidence':None},'context':{}}


@pytest.mark.parametrize('failure',[False,True])
def test_email_after_commit_failure_preserves_core_and_deduplicates(store,monkeypatch,failure):
    sent=[]
    with store() as db:
        event=fixture_event();db.add(Event(id=event['id'],is_demo=False,payload=event));main.create_alerts(db,event)
        def send(message):
            assert not db.in_transaction()
            with store() as check:assert check.get(Event,event['id']) and check.scalar(select(Alert))
            assert message['To']=='subscriber@example.org'
            assert 'not an official emergency warning' in message.get_content()
            sent.append(message)
            return {'sent':not failure,'reason':'SMTP authentication failed' if failure else None}
        monkeypatch.setattr(main,'send_smtp_message',send)
        db.commit();main.deliver_notifications(db)
        main.create_alerts(db,event);db.commit();main.deliver_notifications(db)
        assert len(sent)==1 and len(list(db.scalars(select(Alert))))==1
        note=db.scalar(select(EmailNotification));assert note.status==('failed' if failure else 'sent')
        assert db.get(Event,event['id']).payload==event
        assert len(list(db.scalars(select(EmailNotification))))==1


def test_below_threshold_and_demo_never_send(store,monkeypatch):
    monkeypatch.setattr(main,'send_smtp_message',lambda message:pytest.fail('No notification allowed'))
    with store() as db:
        for event in [fixture_event(79),{**fixture_event(),'id':'demo','is_demo':True}]:
            db.add(Event(id=event['id'],is_demo=event['is_demo'],payload=event));main.create_alerts(db,event)
        db.commit();main.deliver_notifications(db)
        assert not list(db.scalars(select(EmailNotification)))


def test_user_preference_api_requires_valid_opt_in(client):
    c,_=client;headers=auth(c)
    assert c.put('/api/v1/auth/notifications',headers=headers,json={'notifications_enabled':True}).status_code==422
    payload={'notifications_enabled':True,'latitude':22,'longitude':70,'alert_radius_km':None}
    assert c.put('/api/v1/auth/notifications',headers=headers,json=payload).json()==payload
    assert c.get('/api/v1/auth/notifications',headers=headers).json()==payload


def test_additive_migration_preserves_existing_users():
    engine=create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)'))
        connection.execute(text("INSERT INTO users VALUES (1, 'existing@example.org')"))
    migrate_notification_preferences(engine);migrate_notification_preferences(engine)
    with engine.connect() as connection:
        row=connection.execute(text('SELECT email, notifications_enabled, latitude FROM users')).one()
        assert tuple(row)==('existing@example.org',0,None)
    engine.dispose()


@pytest.mark.parametrize('values',[
    {'gemini_enabled':True},
    {'gemini_enabled':True,'gemini_api_key':'TEST_SECRET'},
    {'gemini_enabled':True,'gemini_model':'fixture-model'},
    {'gemini_timeout_seconds':0},
    {'gemini_timeout_seconds':121},
    {'smtp_enabled':True,'smtp_password':'TEST_SECRET'},
    {'smtp_timeout_seconds':0},
    {'default_alert_radius_km':-1}])
def test_service_config_validation_without_secret_disclosure(values):
    with pytest.raises(ValidationError) as error:Settings(_env_file=None,**values)
    assert 'TEST_SECRET' not in str(error.value)


def test_gemini_and_smtp_config_parsing():
    config=Settings(_env_file=None,gemini_enabled=True,gemini_api_key='TEST_SECRET',gemini_model='fixture-model',
        smtp_enabled=True,smtp_host='smtp.gmail.com',smtp_port='587',smtp_user='sender@example.org',smtp_password='TEST_SECRET',smtp_from='sender@example.org',ALERT_RISK_THRESHOLD=85)
    assert config.gemini_configured and config.smtp_configured and config.auto_alert_risk_threshold==85
    assert 'TEST_SECRET' not in repr(config)


def test_duplicate_on_reclustered_identifier_is_suppressed(store,monkeypatch):
    sent=[];monkeypatch.setattr(main,'send_smtp_message',lambda message:sent.append(message) or {'sent':True,'reason':None})
    with store() as db:
        for identity in ('original','successor'):
            event={**fixture_event(),'id':identity}
            db.add(Event(id=identity,is_demo=False,payload=event));main.create_alerts(db,event)
            db.commit();main.deliver_notifications(db)
        assert len(sent)==1


def test_no_delivery_before_commit(store,monkeypatch):
    monkeypatch.setattr(main,'send_smtp_message',lambda message:pytest.fail('Uncommitted data must not send'))
    with store() as db:
        event=fixture_event();db.add(Event(id=event['id'],is_demo=False,payload=event))
        with db.no_autoflush:main.create_alerts(db,event)
        with pytest.raises(RuntimeError,match='committed'):main.deliver_notifications(db)
        db.rollback()


def test_transactional_notification_uniqueness(store):
    from sqlalchemy.exc import IntegrityError
    with store() as db:
        user=db.scalar(select(User))
        for _ in range(2):db.add(EmailNotification(event_id='same',user_id=user.id,risk_level='High',channel='email',evidence={}))
        with pytest.raises(IntegrityError):db.commit()
        db.rollback()
