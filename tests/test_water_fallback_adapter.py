"""HA adapter simulations for the confirmed-tank-alert fallback."""
import asyncio
from types import SimpleNamespace as NS
import pytest
from test_adapter import adapter, run, prepare_room
from test_activity_adapter import setup as setup_sources


@pytest.mark.parametrize('value,known,problem,okay',[
    ('off',True,False,True), ('on',True,True,False),
    ('unknown',False,False,False), ('unavailable',False,False,False),
    ('',False,False,False), ('water_empty',False,False,False),
])
def test_water_boolean_status(adapter,value,known,problem,okay):
    m,c,h,calls=adapter
    c.settings['water_problem_entities']=['binary_sensor.clean_tank']
    h.states.add('binary_sensor.clean_tank',value)
    status=c.water_status()
    assert status['water_status_known'] is known
    assert status['water_problem'] is problem
    assert status['wet_ok'] is okay
    assert c.telemetry()['water_status_known'] is known


def test_missing_sensor_and_confirmed_problem_do_not_enable_fallback(adapter):
    m,c,h,calls=adapter
    c.settings['water_problem_entities']=['binary_sensor.clean_tank','binary_sensor.missing']
    h.states.add('binary_sensor.clean_tank','on')
    status=c.water_status()
    assert status['water_problem'] and not status['water_status_known']
    assert status['water_unavailable_sources']==['binary_sensor.missing']
    assert status['water_problem_sources']==['binary_sensor.clean_tank']
    assert not c.engine.water_fallback_allowed(status,c.settings)


def test_no_water_sources_is_no_fabricated_alert(adapter):
    m,c,h,calls=adapter
    status=c.water_status()
    assert status['wet_ok'] and status['water_status_known']
    assert not status['water_problem']


@pytest.mark.parametrize('entity',['binary_sensor.renamed_tank','input_boolean.water_empty','switch.water_fault'])
def test_explicit_renamed_water_entities_work_without_name_guessing(adapter,entity):
    m,c,h,calls=adapter
    c.settings['water_problem_entities']=[entity];h.states.add(entity,'on')
    assert c.engine.water_fallback_allowed(c.water_status(),c.settings)


def test_setting_enabled_by_default_and_false_can_be_saved(adapter):
    m,c,h,calls=adapter
    assert c.settings['vacuum_on_water_problem'] is True
    assert c.validate_settings({'vacuum_on_water_problem':False})['vacuum_on_water_problem'] is False
    run(c,'settings',{'vacuum_on_water_problem':False})
    assert c.store.saved[-1]['settings']['vacuum_on_water_problem'] is False
    assert not c.engine.enabled


@pytest.mark.parametrize('value',['yes','false',0,1,None])
def test_nonboolean_fallback_setting_rejected(adapter,value):
    m,c,h,calls=adapter
    with pytest.raises(ValueError):c.validate_settings({'vacuum_on_water_problem':value})


def make_snapshot_job(c,h):
    setup_sources(c,h)
    run(c,'save_room',prepare_room(c,h))
    c.settings['water_problem_entities']=['binary_sensor.test_clean_water_box']
    h.states.add('binary_sensor.test_clean_water_box','on')
    c.engine.enqueue('kitchen',c.rooms,100)


def test_snapshot_explains_pending_mode_without_changing_labels(adapter):
    m,c,h,calls=adapter;make_snapshot_job(c,h)
    before=set(h.regs['area_registry'].areas['kitchen'].labels)
    result=c.snapshot()
    j=result['jobs'][0]
    assert j['mode']==j['requested_mode']=='vac_and_mop'
    assert j['effective_mode']=='vacuum' and j['water_fallback']
    assert not j.get('mopping_skipped')  # Not completed yet.
    assert before==h.regs['area_registry'].areas['kitchen'].labels
    assert c.engine.active is None and not calls


def test_completed_dry_result_stays_visible_after_refill(adapter):
    m,c,h,calls=adapter;make_snapshot_job(c,h)
    c.engine.jobs[0].update(status='completed',requested_mode='vac_and_mop',executed_mode='vacuum',
        mopping_skipped=True,fallback_reason='Water tank needs attention; mopping skipped',
        result='vacuum_only_water_fallback')
    h.states.add('binary_sensor.test_clean_water_box','off')
    j=c.snapshot()['jobs'][0]
    assert j['effective_mode']=='vacuum' and j['water_fallback'] and j['mopping_skipped']


def test_active_dry_attempt_is_not_upgraded_to_mop_midroom(adapter):
    m,c,h,calls=adapter;make_snapshot_job(c,h)
    c.engine.active=dict(uid=c.engine.jobs[0]['uid'],name='Kitchen',mode='vacuum',
        requested_mode='vac_and_mop',phase='cleaning',water_fallback=True,
        fallback_reason='Water tank needs attention; mopping skipped')
    h.states.add('binary_sensor.test_clean_water_box','off')
    assert c.snapshot()['jobs'][0]['effective_mode']=='vacuum'


def test_refill_changes_only_pending_preview(adapter):
    m,c,h,calls=adapter;make_snapshot_job(c,h)
    h.states.add('binary_sensor.test_clean_water_box','off')
    j=c.snapshot()['jobs'][0]
    assert j['effective_mode']=='vac_and_mop' and not j['water_fallback']


def test_fallback_command_is_select_vacuum_only(adapter):
    m,c,h,calls=adapter;setup_sources(c,h)
    asyncio.run(c.execute({'kind':'set_mode','option':'vacuum'}))
    assert calls[0][0]==('select','select_option',{'entity_id':'select.test_cleaning_mode','option':'vacuum'})
    assert len(calls)==1
