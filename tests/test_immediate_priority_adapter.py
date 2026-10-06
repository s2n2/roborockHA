"""HA adapter contract simulations for explicit gesture dispatch. No robot I/O."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from test_adapter import adapter, run
from test_gestures import configured, NOW
from test_engine import setup as engine_setup, LOCAL


@pytest.mark.parametrize('label',['dobby_room_press','dobby_room_toggle','dobby_room_double_toggle'])
def test_each_gesture_grants_only_its_job_and_acknowledges(adapter,label):
    m,c,h,calls=configured(adapter,label)
    asyncio.run(c._gesture('binary_sensor.wall'))
    assert len(c.engine.immediate_jobs())==1
    assert c.engine.immediate_jobs()[0]['source']==label
    assert not c.engine.enabled and not c.engine.manual and not c.engine.allow_home
    assert len(calls)==1 and calls[0][0][0:2]==('vacuum','locate')
    assert 'gesture_requests' not in c.store.saved[-1]['engine']


def test_explicit_queue_only_setting_keeps_legacy_behaviour(adapter):
    m,c,h,calls=configured(adapter)
    c.settings['gesture_start_immediately']=False
    asyncio.run(c._gesture('binary_sensor.wall'))
    assert len(c.engine.jobs)==1 and not c.engine.gesture_requests
    assert calls[0][0][0:2]==('vacuum','locate')


def test_create_missing_daily_baseline_before_queuing_not_after(adapter):
    m,c,h,calls=configured(adapter)
    assert not c.engine.day
    asyncio.run(c._gesture('binary_sensor.wall'))
    uid=c.engine.jobs[0]['uid'];assert c.engine.day
    c.telemetry=lambda:dict(now=NOW,home=True,connected=False)
    asyncio.run(c.async_tick())
    assert c.engine.jobs[0]['uid']==uid and c.engine.is_immediate(uid)


def test_storage_failure_rolls_back_grant_and_queue(adapter):
    m,c,h,calls=configured(adapter);before=c.engine.export();c.store.fail=True
    with pytest.raises(OSError):asyncio.run(c._gesture('binary_sensor.wall'))
    assert not c.engine.gesture_requests and c.engine.export()==before and not calls


def test_storage_failure_preserves_previous_grants(adapter):
    m,c,h,calls=configured(adapter)
    asyncio.run(c._gesture('binary_sensor.wall'))
    grants=dict(c.engine.gesture_requests);before=c.engine.export();count=len(calls)
    c.store.fail=True
    with pytest.raises(OSError):asyncio.run(c._gesture('binary_sensor.wall'))
    assert c.engine.gesture_requests==grants and c.engine.export()==before and len(calls)==count


def test_locate_timeout_does_not_revoke_immediate_request(adapter):
    m,c,h,calls=configured(adapter)
    async def fail(*args,**kw):raise TimeoutError('robot sound unavailable')
    c.call=fail
    asyncio.run(c._gesture('binary_sensor.wall'))
    assert len(c.engine.immediate_jobs())==1


def test_locate_does_not_hold_up_actual_scheduler_dispatch(adapter,monkeypatch):
    m,c,h,calls=configured(adapter,'dobby_room_toggle')
    e,cfg,rooms,t=engine_setup()
    c.rooms=rooms;c.settings.update(cfg)
    c.settings.update(vacuum_entity='vacuum.test',mode_entity='select.mode')
    c.engine.day=e.day;c.engine.enabled=False;t['home']=True
    c.telemetry=lambda:t;c.publish=lambda:None
    monkeypatch.setattr(m,'time',NS(time=lambda:t['now']))
    monkeypatch.setattr(m.dt_util,'now',lambda:LOCAL)
    events=[]
    real_save=c.persist
    async def save():
        await real_save();events.append('saved')
    c.persist=save
    async def scenario():
        release=asyncio.Event();sound_started=asyncio.Event();tasks=[]
        async def call(domain,service,entity,**data):
            events.append(service)
            if service=='locate':sound_started.set();await release.wait()
        c.call=call
        def create(coro):
            task=asyncio.create_task(coro);tasks.append(task);return task
        h.async_create_task=create
        c.kick=m.DobbyController.kick.__get__(c,type(c))
        gesture=asyncio.create_task(c._gesture('binary_sensor.wall'))
        await asyncio.wait_for(sound_started.wait(),1)
        for _ in range(30):
            if c.engine.active:break
            await asyncio.sleep(0)
        assert c.engine.active and c.engine.active['area_id']=='kitchen'
        assert c.engine.active['start_policy']=='gesture'
        assert not gesture.done()  # Locate is still waiting.
        assert 'select_option' in events
        assert events.index('saved') < events.index('select_option')
        release.set();await gesture
        await asyncio.gather(*tasks)
    asyncio.run(scenario())


def test_setting_default_true_and_explicit_false_revokes_permission(adapter):
    m,c,h,calls=configured(adapter)
    assert c.settings['gesture_start_immediately'] is True
    asyncio.run(c._gesture('binary_sensor.wall'))
    run(c,'settings',{'gesture_start_immediately':False})
    assert not c.engine.gesture_requests
    assert c.store.saved[-1]['settings']['gesture_start_immediately'] is False


@pytest.mark.parametrize('value',[0,1,None,'true','false'])
def test_setting_boolean_type_is_validated(adapter,value):
    m,c,h,calls=adapter
    with pytest.raises(ValueError):c.validate_settings({'gesture_start_immediately':value})


@pytest.mark.parametrize('command,data',[
    ('enqueue',{'area_id':'kitchen','urgent':True}),
    ('enqueue',{'area_id':'kitchen'})])
def test_dashboard_priority_does_not_create_gesture_grant(adapter,command,data):
    m,c,h,calls=configured(adapter)
    run(c,command,data)
    assert c.engine.jobs and not c.engine.gesture_requests and not calls


def test_snapshot_reports_request_batch_separately_from_auto_enable(adapter):
    m,c,h,calls=configured(adapter)
    asyncio.run(c._gesture('binary_sensor.wall'))
    snapshot=c.snapshot()
    assert snapshot['immediate_rooms']==['Kitchen']
    assert snapshot['jobs'][0]['immediate_request'] is True
    assert snapshot['gesture_start_immediately'] is True and not snapshot['enabled']
    run(c,'pause');snapshot=c.snapshot()
    assert snapshot['immediate_rooms']==[] and not snapshot['jobs'][0]['immediate_request']


def test_disabling_auto_explicitly_clears_requests(adapter):
    m,c,h,calls=configured(adapter)
    asyncio.run(c._gesture('binary_sensor.wall'))
    run(c,'enable',{'enabled':False})
    assert not c.engine.gesture_requests


def test_source_settings_do_not_mutate_labels_when_starting(adapter):
    m,c,h,calls=configured(adapter)
    labels=set(h.regs['entity_registry'].entities['binary_sensor.wall'].labels)
    rooms=deepcopy(c.room_config)
    asyncio.run(c._gesture('binary_sensor.wall'))
    assert labels==h.regs['entity_registry'].entities['binary_sensor.wall'].labels
    assert rooms==c.room_config
