"""Conservative APP_CHARGE recovery tests; no actual Roborock commands.

The intent is not to ignore docking failures: read fresh telemetry and grant
one recovery only when a real pending job is allowed to run and hardware safe.
"""
from copy import deepcopy
import pytest
from test_engine import setup, step, start, finish_record
from test_immediate_priority import request


def fault(e, t, text="Error while calling APP_CHARGE"):
    e.fault_effect("dock", text, t["now"])
    assert e.fault


def safe_ready(t):
    t["dock_error"] = "ok"


def test_dock_error_at_rest_auto_recovers_when_scheduled_clean_is_due():
    e,c,r,t = setup(); safe_ready(t); fault(e,t)
    assert step(e,c,r,t) == []
    assert e.fault
    assert step(e,c,r,t,seconds=c['dock_settle']-1) == []
    assert step(e,c,r,t,seconds=1) == [{'kind':'set_mode','option':'vac_and_mop'}]
    assert not e.fault and e.active['area_id']=='kitchen'
    assert e.jobs[0]['dock_auto_retry_used'] is True
    assert any('Automatically cleared transient APP_CHARGE' in row['message'] for row in e.log)


def test_manual_run_does_not_need_an_extra_retry_click():
    e,c,r,t=setup();safe_ready(t); e.enabled=False; e.manual=True;e.allow_home=True;t['home']=True
    fault(e,t)
    assert step(e,c,r,t)==[]
    assert step(e,c,r,t,seconds=c['dock_settle'])[0]['kind']=='set_mode'


def test_switch_request_immediate_at_home_recovers_old_error():
    e,c,r,t=setup();safe_ready(t);e.enabled=False;t['home']=True;fault(e,t)
    request(e,r,t,'hallway')
    assert step(e,c,r,t)==[]
    assert step(e,c,r,t,seconds=c['dock_settle'])[0]['kind']=='set_mode'
    assert e.active['area_id']=='hallway'


@pytest.mark.parametrize('reason',[
    'error: main brush jammed',
    'completion: Docked without proof',
    'empty: Emptying unavailable',
    'dock: connection timeout',
    'set_mode: Error while calling APP_CHARGE',
])
def test_unrelated_error_never_auto_clears(reason):
    e,c,r,t=setup();safe_ready(t);e.fault=reason
    step(e,c,r,t);step(e,c,r,t,seconds=60)
    assert e.fault==reason and e.active is None


@pytest.mark.parametrize('field,value',[
    ('vacuum','returning'),('vacuum','cleaning'),('vacuum','idle'),
    ('vacuum','unknown'),('connected',False),('error','problem'),
    ('dock_error','problem'),('dock_error','unknown'),('emptying',True),
    ('emptying',None),('washing',True),('washing',None),
    ('blockers',True),('legacy',[{'entity_id':'automation.old'}]),
    ('record_supported',False),('map_name','different'),('battery',5),
])
def test_unsafe_telemetry_never_clears_fault(field,value):
    e,c,r,t=setup();safe_ready(t);fault(e,t);t[field]=value
    step(e,c,r,t);step(e,c,r,t,seconds=60)
    assert e.fault and e.active is None


def test_no_cleaning_request_due_leaves_error_visible():
    e,c,r,t=setup();safe_ready(t);fault(e,t);e.enabled=False
    step(e,c,r,t);step(e,c,r,t,seconds=60)
    assert e.fault


def test_at_home_default_daily_cannot_recover_until_away():
    e,c,r,t=setup();safe_ready(t);fault(e,t);t['home']=True
    step(e,c,r,t);step(e,c,r,t,seconds=60)
    assert e.fault and e.active is None
    step(e,c,r,t,home=False)
    step(e,c,r,t,seconds=c['away_minutes']*60)
    assert e.fault and e.active is None  # first settled dock reading
    assert step(e,c,r,t,seconds=c['dock_settle'])[0]['kind']=='set_mode'


def test_recovery_requires_consecutive_settled_dock_readings():
    e,c,r,t=setup();safe_ready(t);fault(e,t)
    step(e,c,r,t)
    step(e,c,r,t,seconds=6, vacuum='returning')
    assert e._recoverable_dock_since is None
    step(e,c,r,t,seconds=1, vacuum='docked')
    assert e.fault
    step(e,c,r,t,seconds=c['dock_settle']-1)
    assert e.fault
    assert step(e,c,r,t,seconds=1)[0]['kind']=='set_mode'


def test_new_fault_same_job_does_not_auto_loop_and_survives_restart():
    e,c,r,t=setup();safe_ready(t);fault(e,t)
    step(e,c,r,t);step(e,c,r,t,seconds=c['dock_settle'])
    j=e.jobs[0];assert j['dock_auto_retry_used']
    # Failed command as the same job tries to run: never auto retry indefinitely.
    fault(e,t)
    step(e,c,r,t,seconds=1)
    step(e,c,r,t,seconds=80)
    assert e.fault
    from test_engine import Engine
    reloaded=Engine(e.export());reloaded.active=None
    assert reloaded.jobs[0]['dock_auto_retry_used']
    step(reloaded,c,r,t,seconds=80)
    assert reloaded.fault


def test_new_explicit_request_resets_old_retry_limit():
    e,c,r,t=setup();safe_ready(t)
    j=e.jobs[0];j['dock_auto_retry_used']=True
    e.enqueue('kitchen',r,t['now'],urgent=True,source='dashboard')
    assert 'dock_auto_retry_used' not in j


def test_aborting_job_is_not_completed_from_dock_error():
    e,c,r,t=setup();safe_ready(t);start(e,c,r,t)
    e.abort('Returning home',t['now'])
    fault(e,t)
    step(e,c,r,t,vacuum='docked')
    assert e.fault and e.active is None
    assert e.jobs[0]['status']=='needs_action'
    step(e,c,r,t)
    assert e.fault
    assert step(e,c,r,t,seconds=c['dock_settle'])[0]['kind']=='set_mode'
    assert e.jobs[0]['status']=='needs_action'


def test_verified_clean_preserves_success_proof_if_dock_rpc_failed():
    e,c,r,t=setup();safe_ready(t);at=start(e,c,r,t)
    # Robot has provided a successful record but HA's return-to-base RPC fails.
    step(e,c,r,t,seconds=200,vacuum='idle',record=finish_record(at))
    assert e.active['proved']
    fault(e,t)
    step(e,c,r,t,seconds=2,vacuum='docked')
    assert e.fault
    step(e,c,r,t,seconds=c['dock_settle'])
    assert not e.fault and e.active['proved']
    assert e.active['phase']=='verifying'
    assert e.jobs[0]['status']=='needs_action'


def test_no_fresh_record_and_dock_cannot_mark_done():
    e,c,r,t=setup();safe_ready(t);start(e,c,r,t)
    fault(e,t)
    step(e,c,r,t,vacuum='docked')
    step(e,c,r,t,seconds=c['dock_settle'])
    assert not e.fault
    assert e.active is not None and e.active['phase']=='preparing'
    assert e.jobs[0]['status']=='needs_action'


def test_auto_recovery_is_idempotent_after_success():
    e,c,r,t=setup();safe_ready(t);fault(e,t)
    step(e,c,r,t);step(e,c,r,t,seconds=c['dock_settle'])
    initial=len([x for x in e.log if 'Automatically cleared' in x['message']])
    step(e,c,r,t)
    assert initial==1 and len([x for x in e.log if 'Automatically cleared' in x['message']])==1
