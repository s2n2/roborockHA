"""Explicit switch requests run as a bounded per-job batch, not a whole-home override.
All telemetry is simulated. No Home Assistant instance or vacuum is contacted.
"""
import pytest
from test_engine import setup, step, start, finish_record, Engine, LOCAL, NOW, m


def request(e, rooms, t, area):
    uid=e.enqueue(area,rooms,t['now'],urgent=True,source='dobby_room_toggle')
    e.request_immediate(uid,t['now'])
    return uid


def complete_next(e,c,r,t,expected):
    assert step(e,c,r,t)[0]['kind']=='set_mode'
    assert e.active['area_id']==expected
    mode=e.active['mode'];uid=e.active['uid']
    effects=step(e,c,r,t,mode=mode)
    assert effects and effects[0]['kind']=='clean'
    at=e.active['command_at']
    step(e,c,r,t,vacuum='cleaning')
    assert e.active['seen_cleaning']
    step(e,c,r,t,seconds=200,vacuum='docked',record=finish_record(at),emptying=True)
    assert e.find(uid)['status']=='needs_action'
    step(e,c,r,t,seconds=40,emptying=False)
    assert e.find(uid)['status']=='completed' and e.active is None
    assert not e.is_immediate(uid)


@pytest.mark.parametrize('home',[True,False])
@pytest.mark.parametrize('enabled',[False,True])
def test_immediate_bypasses_home_away_delay_and_automatic_enable(home,enabled):
    e,c,r,t=setup();e.enabled=enabled;e.away_since=None;t['home']=home
    uid=request(e,r,t,'hallway')
    assert step(e,c,r,t)==[{'kind':'set_mode','option':'vac_and_mop'}]
    assert e.active['uid']==uid and e.active['start_policy']=='gesture'
    assert not e.manual and not e.allow_home


@pytest.mark.parametrize('enabled',[True,False])
def test_all_switch_requested_rooms_run_at_home_but_daily_rooms_do_not(enabled):
    e,c,r,t=setup();e.enabled=enabled;t['home']=True
    request(e,r,t,'hallway');request(e,r,t,'bedroom')
    assert [j['area_id'] for j in e.immediate_jobs()]==['bedroom','hallway']
    complete_next(e,c,r,t,'bedroom')
    complete_next(e,c,r,t,'hallway')
    assert step(e,c,r,t)==[] and e.active is None
    assert not e.manual and not e.allow_home and not e.gesture_requests
    assert next(j for j in e.jobs if j['area_id']=='kitchen')['status']=='needs_action'
    if enabled:
        assert 'everyone to leave' in e.wait_reason
        assert step(e,c,r,t,home=False)==[]
        assert step(e,c,r,t,seconds=901)[0]['kind']=='set_mode'
        assert e.active['area_id']=='kitchen' and e.active['start_policy']=='automatic'
    else:assert 'disabled' in e.wait_reason.lower()


def test_ordinary_priority_or_forged_source_does_not_grant_home_permission():
    e,c,r,t=setup();t['home']=True
    e.enqueue('bedroom',r,t['now'],urgent=True,source='dobby_room_toggle')
    assert step(e,c,r,t)==[] and not e.gesture_requests


def test_explicit_requests_can_run_outside_automatic_time_window():
    e,c,r,t=setup();c.update(window_start='12:00',window_end='13:00');t['home']=True;e.enabled=False
    request(e,r,t,'bedroom');complete_next(e,c,r,t,'bedroom')
    assert step(e,c,r,t)==[]


def test_request_arrives_during_priority_job_no_interrupt_and_runs_next():
    e,c,r,t=setup();t['home']=True;e.enabled=False
    first=request(e,r,t,'kitchen');start(e,c,r,t)
    request(e,r,t,'bedroom');request(e,r,t,'hallway')
    assert e.active['uid']==first
    assert step(e,c,r,t)==[] and e.active['phase']=='cleaning'
    assert [j['area_id'] for j in e.immediate_jobs()]==['hallway','bedroom','kitchen']


def test_people_arriving_during_gesture_job_do_not_abort():
    e,c,r,t=setup();request(e,r,t,'kitchen');start(e,c,r,t)
    assert step(e,c,r,t,home=True)==[] and e.active['phase']=='cleaning'


def test_normal_run_stops_on_arrival_but_other_fresh_switch_requests_survive():
    e,c,r,t=setup();start(e,c,r,t);request(e,r,t,'bedroom')
    assert step(e,c,r,t,home=True)==[{'kind':'dock'}]
    assert len(e.immediate_jobs())==1 and e.active['phase']=='aborting'
    assert step(e,c,r,t,vacuum='docked')==[]
    assert step(e,c,r,t)[0]['kind']=='set_mode'
    assert e.active['area_id']=='bedroom'
    assert next(j for j in e.jobs if j['area_id']=='kitchen')['status']=='needs_action'


def test_new_request_does_not_preempt_nonowned_robot_activity():
    e,c,r,t=setup();t.update(home=True,vacuum='cleaning')
    request(e,r,t,'bedroom')
    assert step(e,c,r,t)==[] and not e.active
    assert 'dock' in e.wait_reason.lower()


def test_manual_move_cannot_put_daily_work_ahead_of_immediate_requests():
    e,c,r,t=setup();k=e.jobs[0]['uid'];b=request(e,r,t,'bedroom');h=request(e,r,t,'hallway')
    e.move(k,None)
    assert [j['uid'] for j in e.immediate_jobs()]==[h,b]
    assert e.jobs[-1]['uid']==k
    e.move(b,None)
    assert [j['uid'] for j in e.immediate_jobs()]==[b,h]


def test_duplicate_request_has_one_job_and_refreshes_priority():
    e,c,r,t=setup();a=request(e,r,t,'kitchen');request(e,r,t,'hallway')
    assert request(e,r,t,'kitchen')==a
    assert len(e.jobs)==2 and len(e.immediate_jobs())==2 and e.jobs[0]['uid']==a


def test_pausing_cancels_whole_immediate_batch_but_keeps_rooms_pending():
    e,c,r,t=setup();t['home']=True;e.enabled=False
    request(e,r,t,'kitchen');request(e,r,t,'hallway');step(e,c,r,t)
    e.abort('Paused and sent to dock by user',t['now'])
    assert not e.gesture_requests
    step(e,c,r,t,vacuum='docked')
    assert step(e,c,r,t)==[] and not e.active
    assert all(j['status']=='needs_action' for j in e.jobs)
    request(e,r,t,'bedroom')
    assert step(e,c,r,t)[0]['kind']=='set_mode'
    assert e.active['area_id']=='bedroom' and len(e.immediate_jobs())==1


def test_restart_never_restores_immediate_permissions():
    e,c,r,t=setup();t['home']=True
    request(e,r,t,'hallway');request(e,r,t,'bedroom')
    saved=e.export();assert 'gesture_requests' not in saved
    new=Engine(saved)
    assert not new.gesture_requests and step(new,c,r,t)==[]
    assert len(new.jobs)==3


def test_restart_of_active_gesture_job_recovers_without_permissions():
    e,c,r,t=setup();request(e,r,t,'kitchen');start(e,c,r,t)
    new=Engine(e.export());assert new.active['phase']=='aborting'
    step(new,c,r,t,home=True,vacuum='docked')
    assert not new.active and step(new,c,r,t)==[] and not new.gesture_requests


def test_reset_clears_grants_and_restores_normal_order():
    e,c,r,t=setup();request(e,r,t,'bedroom');request(e,r,t,'hallway')
    e.reset(e.day,r,t['now'])
    assert not e.gesture_requests and [j['area_id'] for j in e.jobs]==['kitchen','hallway']


def test_removal_and_manual_completion_revoke_only_their_own_request():
    e,c,r,t=setup();a=request(e,r,t,'kitchen');b=request(e,r,t,'hallway')
    e.remove(a);assert not e.is_immediate(a) and e.is_immediate(b)
    e.manual_complete(b,t['now'],True);assert not e.gesture_requests


def test_queue_only_option_revokes_grants_without_unleashing_daily_work():
    e,c,r,t=setup();t['home']=True;request(e,r,t,'hallway');c['gesture_start_immediately']=False
    assert step(e,c,r,t)==[] and not e.gesture_requests and not e.active


@pytest.mark.parametrize('key,value',[
    ('home',None),('connected',False),('battery',5),('battery',None),('error','problem'),
    ('map_name','Other'),('map_flag',2),('blockers',True),('record_supported',False),
    ('legacy',[{'entity_id':'automation.old'}]),('emptying',True),('emptying',None),
    ('washing',True),('wet_ok',False),('vacuum','returning')])
def test_immediate_is_not_a_hardware_or_configuration_safety_bypass(key,value):
    e,c,r,t=setup();t['home']=True;e.enabled=False;request(e,r,t,'kitchen');t[key]=value
    assert step(e,c,r,t)==[] and e.active is None
    assert e.wait_reason


@pytest.mark.parametrize('key,value',[('verified',False),('segments',[]),('mode',None),('mapping_error','duplicate'),('cleanable',False)])
def test_mapping_and_mode_checks_still_block(key,value):
    e,c,r,t=setup();t['home']=True;request(e,r,t,'kitchen');r['kitchen'][key]=value
    assert step(e,c,r,t)==[] and e.active is None


def test_water_fallback_at_home_keeps_batch_and_marks_only_vacuum_result():
    e,c,r,t=setup();e.enabled=False;t['home']=True
    request(e,r,t,'hallway');request(e,r,t,'kitchen')
    t.update(wet_ok=False,water_problem=True,water_status_known=True)
    complete_next(e,c,r,t,'kitchen')
    assert next(j for j in e.jobs if j['area_id']=='kitchen')['mopping_skipped']
    complete_next(e,c,r,t,'hallway')
    assert not e.gesture_requests and not e.manual


def test_midroom_water_loss_preserves_other_immediate_requests_after_redock():
    e,c,r,t=setup();e.enabled=False;t['home']=True
    request(e,r,t,'hallway');request(e,r,t,'kitchen');start(e,c,r,t)
    t.update(wet_ok=False,water_problem=True,water_status_known=True)
    assert step(e,c,r,t)==[] and e.active['fallback_redock']
    assert len(e.immediate_jobs())==2
    assert step(e,c,r,t)==[{'kind':'dock'}]
    step(e,c,r,t,vacuum='docked');step(e,c,r,t,seconds=c['dock_settle']+1)
    assert not e.active and len(e.immediate_jobs())==2
    assert step(e,c,r,t)==[{'kind':'set_mode','option':'vacuum'}]
    assert e.active['area_id']=='kitchen' and e.active['start_policy']=='gesture'


def test_empty_timeout_still_faults_not_done():
    e,c,r,t=setup();e.enabled=False;t['home']=True
    request(e,r,t,'kitchen');at=start(e,c,r,t)
    step(e,c,r,t,seconds=200,vacuum='docked',record=finish_record(at))
    assert step(e,c,r,t,seconds=11)==[{'kind':'empty'}]
    step(e,c,r,t,seconds=250)
    assert e.fault and not any(j['status']=='completed' for j in e.jobs)


@pytest.mark.parametrize('updates',[{'blockers':True},{'home':None},{'map_name':'Wrong map'}])
def test_active_priority_still_stops_for_real_blockers(updates):
    e,c,r,t=setup();t['home']=True;e.enabled=False
    request(e,r,t,'kitchen');start(e,c,r,t);request(e,r,t,'bedroom')
    assert step(e,c,r,t,**updates)==[{'kind':'dock'}]
    assert e.active['phase']=='aborting' and not e.gesture_requests


def test_low_battery_retry_keeps_priority_permission_not_daily_permission():
    e,c,r,t=setup();t['home']=True;e.enabled=False
    request(e,r,t,'kitchen');at=start(e,c,r,t)
    record=finish_record(at);record['complete']=0
    step(e,c,r,t,seconds=200,vacuum='docked',record=record,battery=15)
    step(e,c,r,t,seconds=250)
    assert not e.active and not e.fault and len(e.immediate_jobs())==1
    assert step(e,c,r,t)==[]
    assert step(e,c,r,t,battery=90)[0]['kind']=='set_mode'
    assert e.active['area_id']=='kitchen' and e.active['start_policy']=='gesture'
