"""Water fallback regressions with deterministic robot reports; no hardware I/O."""
from copy import deepcopy
from datetime import timedelta
import pytest
from test_engine import setup, step, start, finish_record, Engine, NOW, LOCAL


def shortage(t):
    t.update(wet_ok=False, water_problem=True, water_status_known=True,
             water_problem_sources=['binary_sensor.clean_water_box'],
             water_unavailable_sources=[])


def dry_start(e,c,r,t):
    assert step(e,c,r,t)==[{'kind':'set_mode','option':'vacuum'}]
    assert e.active['water_fallback'] is True
    assert e.active['mode']=='vacuum'
    assert step(e,c,r,t,mode='vacuum')[0]['kind']=='clean'
    at=e.active['command_at']
    step(e,c,r,t,vacuum='cleaning')
    return at


def dry_finish(e,c,r,t,at):
    step(e,c,r,t,seconds=200,vacuum='returning',record=finish_record(at))
    assert e.jobs[0]['status']=='needs_action'
    step(e,c,r,t,vacuum='docked')
    assert step(e,c,r,t,seconds=11)==[{'kind':'empty'}]
    step(e,c,r,t,emptying=True)
    step(e,c,r,t,seconds=8,emptying=False)
    assert e.active is None


@pytest.mark.parametrize('requested',['mop','vac_and_mop'])
def test_tank_alert_runs_vacuum_and_never_requests_mop_flow(requested):
    e,c,r,t=setup();r['kitchen']['mode']=requested;shortage(t)
    c['mop_intensity_entity']='select.flow'
    original=deepcopy(r)
    dry_start(e,c,r,t)
    assert e.active['requested_mode']==requested
    assert 'water_setting_sent' not in e.active
    assert r==original


@pytest.mark.parametrize('requested',['mop','vac_and_mop'])
def test_completed_fallback_is_distinguished_and_requires_empty(requested):
    e,c,r,t=setup();r['kitchen']['mode']=requested;shortage(t)
    c['empty_after_mop']=False
    at=dry_start(e,c,r,t);dry_finish(e,c,r,t,at)
    j=e.jobs[0]
    assert j['status']=='completed' and j['executed_mode']=='vacuum'
    assert j['requested_mode']==requested and j['mopping_skipped'] is True
    assert j['result']=='vacuum_only_water_fallback'
    assert 'mopping skipped' in j['reason']
    assert r['kitchen']['mode']==requested
    assert step(e,c,r,t)[0]=={'kind':'set_mode','option':'vacuum'}
    assert e.active['area_id']=='hallway'


@pytest.mark.parametrize('requested',['mop','vac_and_mop'])
def test_disable_fallback_restores_original_water_block(requested):
    e,c,r,t=setup();r['kitchen']['mode']=requested;shortage(t)
    c['vacuum_on_water_problem']=False
    assert step(e,c,r,t)==[] and e.active is None
    assert 'water' in e.wait_reason.lower()


@pytest.mark.parametrize('water',[
    {'wet_ok':False},
    {'wet_ok':False,'water_problem':False,'water_status_known':False},
    {'wet_ok':False,'water_problem':True,'water_status_known':False},
    {'wet_ok':False,'water_problem':None,'water_status_known':True},
])
def test_missing_or_unknown_water_telemetry_is_not_empty_tank(water):
    e,c,r,t=setup();t.update(water)
    assert step(e,c,r,t)==[] and e.active is None


@pytest.mark.parametrize('key,value',[
    ('home',True),('home',None),('connected',False),('vacuum','error'),
    ('error','problem'),('battery',5),('battery',None),('map_name','Wrong'),
    ('map_flag',999),('blockers',True),('legacy',[{'entity_id':'automation.other'}]),
    ('record_supported',False),('emptying',True),('emptying',None),('washing',True),
])
def test_tank_fallback_never_bypasses_other_preflight_checks(key,value):
    e,c,r,t=setup();shortage(t);t[key]=value
    assert step(e,c,r,t)==[] and e.active is None


@pytest.mark.parametrize('key,value',[
    ('cleanable',False),('mode',None),('verified',False),
    ('segments',[]),('mapping_error','Duplicate room mapping')])
def test_room_validation_still_blocks(key,value):
    e,c,r,t=setup();shortage(t);r['kitchen'][key]=value
    assert step(e,c,r,t)==[] and e.active is None


def test_vacuum_mode_support_and_confirmation_required():
    e,c,r,t=setup();shortage(t)
    t['mode_options']=['mop','vac_and_mop']
    assert step(e,c,r,t)==[] and e.active is None
    t['mode_options'].append('vacuum')
    assert step(e,c,r,t)[0]['option']=='vacuum'
    assert step(e,c,r,t,mode='vac_and_mop')==[]
    assert e.active['command_at'] is None
    assert step(e,c,r,t,seconds=c['start_timeout']+1)==[]
    assert e.fault.startswith('set_mode:')


def test_mop_wash_sensor_unknown_is_not_ready_to_launch_fallback():
    e,c,r,t=setup();shortage(t);c['wash_entity']='switch.wash';t['washing']=None
    assert step(e,c,r,t)==[] and e.active is None
    assert 'Mop' in e.wait_reason or 'mop' in e.wait_reason


def test_regular_dry_room_does_not_acquire_false_skipped_result():
    e,c,r,t=setup();r['kitchen']['mode']='vacuum';shortage(t)
    assert step(e,c,r,t)[0]['option']=='vacuum'
    assert not e.active['water_fallback']
    assert e.active['requested_mode']=='vacuum'


def test_water_returns_before_next_job_next_job_uses_label_mode():
    e,c,r,t=setup();shortage(t)
    at=dry_start(e,c,r,t);dry_finish(e,c,r,t,at)
    t.update(wet_ok=True,water_problem=False,water_status_known=True)
    assert step(e,c,r,t)[0]['option']=='vac_and_mop'
    assert not e.active['water_fallback']
    assert e.jobs[0]['mopping_skipped']


def test_refill_does_not_change_already_started_dry_attempt():
    e,c,r,t=setup();shortage(t)
    assert step(e,c,r,t)[0]['option']=='vacuum'
    t.update(wet_ok=True,water_problem=False,water_status_known=True)
    effects=step(e,c,r,t,mode='vacuum')
    assert effects[0]['kind']=='clean'
    assert e.active['mode']=='vacuum' and e.active['water_fallback']


def test_refill_and_manual_repeat_clear_old_fallback():
    e,c,r,t=setup();shortage(t)
    at=dry_start(e,c,r,t);dry_finish(e,c,r,t,at)
    e.enqueue('kitchen',r,t['now'],urgent=True)
    assert 'mopping_skipped' not in e.jobs[0] and 'result' not in e.jobs[0]
    t.update(wet_ok=True,water_problem=False,water_status_known=True)
    assert step(e,c,r,t)[0]['option']=='vac_and_mop'


def test_water_failure_before_dispatch_changes_mode_without_docking():
    e,c,r,t=setup();c['mop_intensity_entity']='select.flow'
    assert step(e,c,r,t)[0]['option']=='vac_and_mop'
    shortage(t)
    assert step(e,c,r,t,mode='vac_and_mop')==[{'kind':'set_mode','option':'vacuum'}]
    assert e.active['command_at'] is None and not e.fault
    assert step(e,c,r,t,mode='vacuum')[0]['kind']=='clean'
    assert e.active['requested_mode']=='vac_and_mop'


def test_mid_preparation_fallback_requires_empty_for_original_mop_only():
    e,c,r,t=setup();r['kitchen']['mode']='mop';c['empty_after_mop']=False
    t['emptying']=None
    assert step(e,c,r,t)[0]['option']=='mop'
    shortage(t)
    assert step(e,c,r,t,mode='mop')[0]['option']=='vacuum'
    assert step(e,c,r,t,mode='vacuum')==[]
    assert e.active['command_at'] is None and 'emptying' in e.wait_reason


def test_mid_run_water_loss_docks_before_fresh_dry_attempt():
    e,c,r,t=setup();old_at=start(e,c,r,t);shortage(t)
    assert step(e,c,r,t)==[] and not e.fault
    assert e.active['phase']=='aborting'
    assert step(e,c,r,t)==[{'kind':'dock'}]
    assert step(e,c,r,t,vacuum='returning')==[]
    assert e.jobs[0]['status']=='needs_action'
    step(e,c,r,t,vacuum='docked')
    step(e,c,r,t,seconds=c['dock_settle']+1)
    assert e.active is None
    # A transient/cleared water alert cannot bounce this same retry to wet mode.
    t.update(wet_ok=True,water_problem=False)
    assert step(e,c,r,t)[0]['option']=='vacuum'
    assert e.active['requested_mode']=='vac_and_mop'
    assert step(e,c,r,t,mode='vacuum')[0]['kind']=='clean'
    assert e.active['command_at']>old_at and not e.active['proved']
    assert not e.active['seen_cleaning']


def test_water_failure_during_failed_start_never_marks_job_complete():
    e,c,r,t=setup()
    step(e,c,r,t);step(e,c,r,t,mode='vac_and_mop')
    shortage(t);step(e,c,r,t)
    assert not e.active['proved'] and e.jobs[0]['status']=='needs_action'
    assert step(e,c,r,t,vacuum='docked')==[{'kind':'dock'}]
    step(e,c,r,t)
    step(e,c,r,t,seconds=c['dock_settle']+1)
    assert e.active is None and e.jobs[0]['status']=='needs_action'


def test_arrival_wins_over_water_fallback_and_waits_for_new_absence():
    e,c,r,t=setup();start(e,c,r,t);shortage(t)
    step(e,c,r,t,home=True)
    assert 'arrived' in e.active['reason']
    assert not e.jobs[0].get('force_vacuum_reason')
    step(e,c,r,t,vacuum='docked')
    assert e.active is None
    assert step(e,c,r,t,home=False)==[]
    assert step(e,c,r,t,seconds=c['away_minutes']*60+1)[0]['option']=='vacuum'


def test_arrival_during_water_redock_still_blocks_new_job():
    e,c,r,t=setup();start(e,c,r,t);shortage(t);step(e,c,r,t)
    step(e,c,r,t,home=True,vacuum='docked')
    step(e,c,r,t)
    step(e,c,r,t,seconds=c['dock_settle']+1)
    assert e.active is None
    assert step(e,c,r,t)==[]
    assert step(e,c,r,t,home=False)==[]


def test_existing_manual_permission_survives_internal_water_redock_only():
    e,c,r,t=setup();e.enabled=False;e.manual=True;e.allow_home=True;t['home']=True
    start(e,c,r,t);shortage(t);step(e,c,r,t)
    assert e.manual and e.allow_home
    step(e,c,r,t,vacuum='docked')
    step(e,c,r,t)
    step(e,c,r,t,seconds=c['dock_settle']+1)
    assert step(e,c,r,t)[0]['option']=='vacuum'
    restored=Engine(e.export())
    assert not restored.manual and not restored.allow_home


def test_faulted_old_version_requires_retry_then_uses_fallback():
    e,c,r,t=setup();shortage(t);e.fault='Water system needs attention'
    assert step(e,c,r,t)==[] and e.active is None
    e.retry(t['now'],docked=True)
    assert step(e,c,r,t)[0]['option']=='vacuum'


def test_restart_preserves_completed_result_but_never_completes_inflight():
    e,c,r,t=setup();shortage(t)
    at=dry_start(e,c,r,t);saved=e.export();restored=Engine(saved)
    assert restored.active['phase']=='aborting'
    assert restored.active['water_fallback']
    assert restored.jobs[0]['status']=='needs_action'
    dry_finish(e,c,r,t,at)
    restored=Engine(e.export())
    assert restored.jobs[0]['mopping_skipped'] is True
    assert restored.jobs[0]['executed_mode']=='vacuum'


def test_nightly_reset_removes_only_todays_fallback_metadata():
    e,c,r,t=setup();shortage(t)
    at=dry_start(e,c,r,t);dry_finish(e,c,r,t,at)
    e.reset('2026-10-04',r,t['now'])
    assert all('mopping_skipped' not in j for j in e.jobs)
    assert r['kitchen']['mode']=='vac_and_mop'


def test_successful_wet_record_then_empty_water_does_not_repeat_clean():
    e,c,r,t=setup();at=start(e,c,r,t)
    shortage(t)
    step(e,c,r,t,seconds=200,vacuum='docked',record=finish_record(at))
    assert e.active['proved'] and not e.fault
    assert step(e,c,r,t,seconds=11)==[{'kind':'empty'}]
    step(e,c,r,t,emptying=True);step(e,c,r,t,emptying=False)
    assert e.jobs[0]['status']=='completed' and not e.jobs[0]['mopping_skipped']
    assert e.jobs[0]['executed_mode']=='vac_and_mop'


def test_uncertain_water_during_wet_run_still_latches_fault():
    e,c,r,t=setup();start(e,c,r,t)
    step(e,c,r,t,wet_ok=False,water_problem=False,water_status_known=False)
    assert e.active['phase']=='aborting' and e.fault


def test_emptying_failure_still_latches_and_no_false_done():
    e,c,r,t=setup();shortage(t);at=dry_start(e,c,r,t)
    step(e,c,r,t,seconds=200,vacuum='docked',record=finish_record(at))
    step(e,c,r,t,seconds=11)
    step(e,c,r,t,seconds=c['empty_timeout']+1)
    assert e.fault.startswith('empty:') and e.jobs[0]['status']=='needs_action'


def test_manual_confirmation_of_fallback_is_explicit_not_robot_proof():
    e,c,r,t=setup();shortage(t);dry_start(e,c,r,t)
    e.manual_complete(e.active['uid'],t['now'],True)
    j=e.jobs[0]
    assert j['result']=='manual_confirmation' and j['mopping_skipped']
    assert 'not automatic robot proof' in j['reason']


def test_dry_fallback_does_not_accept_failed_clean_record():
    e,c,r,t=setup();shortage(t);at=dry_start(e,c,r,t)
    bad=finish_record(at);bad['complete']=0
    step(e,c,r,t,seconds=200,vacuum='docked',record=bad)
    step(e,c,r,t,seconds=c['proof_timeout']+1)
    assert e.jobs[0]['status']=='needs_action' and e.fault.startswith('completion:')


def test_real_robot_error_during_dry_fallback_still_aborts():
    e,c,r,t=setup();shortage(t);dry_start(e,c,r,t)
    step(e,c,r,t,error='problem')
    assert e.fault and e.active['phase']=='aborting'
    assert e.jobs[0]['status']=='needs_action'


def test_stale_docked_state_after_wet_command_is_cancelled_before_retry():
    e,c,r,t=setup()
    step(e,c,r,t);step(e,c,r,t,mode='vac_and_mop')
    assert e.active['command_at']
    shortage(t);step(e,c,r,t)
    assert step(e,c,r,t)==[{'kind':'dock'}]
    assert e.active and e.jobs[0]['status']=='needs_action'
    assert step(e,c,r,t)==[]
    assert step(e,c,r,t,seconds=c['dock_settle']-1)==[] and e.active
    step(e,c,r,t,seconds=2)
    assert e.active is None
    assert step(e,c,r,t)==[{'kind':'set_mode','option':'vacuum'}]


def test_failed_dock_cancel_does_not_automatically_start_replacement():
    e,c,r,t=setup();start(e,c,r,t);shortage(t);step(e,c,r,t)
    assert step(e,c,r,t)==[{'kind':'dock'}]
    e.fault_effect('dock','no acknowledgement',t['now'])
    assert step(e,c,r,t,vacuum='docked',seconds=100)==[]
    assert e.fault and e.active and e.jobs[0]['status']=='needs_action'


def test_configured_unknown_wash_blocks_redock_completion():
    e,c,r,t=setup();c['wash_entity']='switch.wash';start(e,c,r,t)
    shortage(t);step(e,c,r,t);step(e,c,r,t)
    assert step(e,c,r,t,vacuum='docked',washing=None,seconds=60)==[]
    assert e.active['phase']=='aborting'
