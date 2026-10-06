"""Deterministic read-only reporting tests, not a live Home Assistant instance."""
import importlib.util
from pathlib import Path
import sys

import pytest

P = Path(__file__).parents[1]/'custom_components/dobby_scheduler/activity.py'
spec = importlib.util.spec_from_file_location('dobby_activity_pure_tests', P)
activity = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = activity
spec.loader.exec_module(activity)


def data(**changes):
    return dict(vacuum_entity='vacuum.test', vacuum_state='cleaning', detail_state='unknown',
                room_source='sensor.test_current_room', resolved_room='Kitchen', map_name='Ground',
                error_raw='none', dock_error_raw='ok', mode='vacuum',
                emptying=False, washing=False, drying=False, water_problems=[], **changes)


def changed(**kw):
    d = data()
    d.update(kw)
    return d


def test_initial_full_minute_and_no_early_room():
    tr = activity.ActivityTracker()
    assert tr.update(data(), 100)['text'] == 'Cleaning'
    assert tr.update(data(), 159.999)['text'] == 'Cleaning'
    assert tr.update(data(), 160)['text'] == 'Cleaning Kitchen'


def test_passing_through_hallway_keeps_last_confirmed_room():
    tr = activity.ActivityTracker()
    tr.update(data(), 0)
    assert tr.update(data(), 60)['text'] == 'Cleaning Kitchen'
    brief = tr.update(changed(resolved_room='Hallway'), 70)
    assert brief['text'] == 'Cleaning Kitchen' and not brief['room_is_current']
    assert tr.update(changed(resolved_room='Lounge'), 95)['text'] == 'Cleaning Kitchen'
    assert tr.update(changed(resolved_room='Lounge'), 154)['text'] == 'Cleaning Kitchen'
    assert tr.update(changed(resolved_room='Lounge'), 155)['text'] == 'Cleaning Lounge'


def test_attributes_and_periodic_poll_do_not_restart_window():
    tr = activity.ActivityTracker()
    tr.update(data(), 0)
    for t in range(1,60):
        assert tr.update(changed(battery=100-t), t)['room'] is None
    assert tr.update(changed(battery=25), 60)['room'] == 'Kitchen'


@pytest.mark.parametrize('interruption',[None,'unavailable','unknown'])
def test_missing_room_restarts_confirmation(interruption):
    tr = activity.ActivityTracker()
    tr.update(data(), 0); tr.update(data(), 60)
    # resolve_room translates unknown/unavailable to None in the adapter.
    assert tr.update(changed(resolved_room=activity.resolve_room(interruption,[],'Ground')), 61)['text'] == 'Cleaning'
    tr.update(data(),70)
    assert tr.update(data(),129)['room'] is None
    assert tr.update(data(),130)['room'] == 'Kitchen'


@pytest.mark.parametrize('vacuum_state',['returning','docked','paused','error','unavailable'])
def test_new_cleaning_spell_does_not_reuse_previous_room(vacuum_state):
    tr=activity.ActivityTracker(); tr.update(data(),0); tr.update(data(),60)
    tr.update(changed(vacuum_state=vacuum_state),65)
    assert tr.update(data(),70)['text']=='Cleaning'
    assert tr.update(data(),129)['text']=='Cleaning'
    assert tr.update(data(),130)['text']=='Cleaning Kitchen'


def test_idle_room_confirmation_does_not_claim_cleaning_location():
    tr=activity.ActivityTracker()
    idle=changed(vacuum_state='docked')
    tr.update(idle,0)
    assert tr.update(idle,60)['confirmed_room']=='Kitchen'
    assert tr.update(data(),61)['text']=='Cleaning'
    assert tr.update(data(),121)['text']=='Cleaning Kitchen'


@pytest.mark.parametrize('field,value',[
    ('room_source','sensor.other_room'),('map_name','Upstairs'),('vacuum_entity','vacuum.other')])
def test_source_map_or_robot_change_resets_timers(field,value):
    tr=activity.ActivityTracker();tr.update(data(),0);tr.update(data(),60)
    fresh=changed(**{field:value})
    assert tr.update(fresh,61)['confirmed_room'] is None
    assert tr.update(fresh,121)['text']=='Cleaning Kitchen'


def test_changing_delay_restarts_proof_window():
    tr=activity.ActivityTracker();tr.update(data(),0)
    assert tr.update(data(),59,10)['room'] is None
    assert tr.update(data(),69,10)['room']=='Kitchen'


def test_poll_at_65_seconds_is_not_backdated_to_entry_time():
    tr=activity.ActivityTracker();tr.update(data(),0);tr.update(data(),59)
    tr.update(data(),65)
    assert tr.location.confirmed_at==65


@pytest.mark.parametrize('value',[float('nan'),float('inf'),0,601,-1])
def test_bad_delay_uses_default(value):
    tr=activity.ActivityTracker()
    tr.update(data(),0,value)
    assert tr.update(data(),59,value)['text']=='Cleaning'
    assert tr.update(data(),60,value)['text']=='Cleaning Kitchen'


@pytest.mark.parametrize('delta, expected', [
    ({'error_raw':'main_brush_jammed'},'Main brush jammed'),
    ({'error_raw':'wheels_suspended'},'Wheels suspended'),
    ({'vacuum_state':'returning'},'Returning to dock'),
    ({'vacuum_state':'paused'},'Paused'),
    ({'vacuum_state':'docked','emptying':True},'Emptying dustbin'),
    ({'vacuum_state':'docked','washing':True},'Washing mop'),
    ({'vacuum_state':'docked','drying':True},'Drying mop'),
    ({'vacuum_state':'docked'},'Docked'),
    ({'vacuum_state':'charging'},'Charging'),
    ({'vacuum_state':'idle'},'Idle'),
    ({'vacuum_state':'error'},'Vacuum error'),
    ({'vacuum_state':'docked','dock_error_raw':'dust_bag_missing'},'Dust bag missing'),
    ({'vacuum_state':'docked','water_problems':['Refill/reseat clean-water tank']},'Refill/reseat clean-water tank'),
    ({'vacuum_entity':''},'Not configured'),
    ({'vacuum_state':'unavailable','error_raw':'main_brush_jammed'},'Unavailable'),
])
def test_non_room_activity_is_not_delayed(delta,expected):
    tr=activity.ActivityTracker();tr.update(data(),0);tr.update(data(),60)
    assert tr.update(changed(**delta),60.01)['text']==expected


@pytest.mark.parametrize('mode,text',[
    ('vacuum','Cleaning Kitchen'),('mop','Mopping Kitchen'),
    ('vac_and_mop','Vacuuming and mopping Kitchen'),('custom','Cleaning Kitchen')])
def test_live_modes(mode,text):
    tr=activity.ActivityTracker();tr.update(changed(mode=mode),0)
    assert tr.update(changed(mode=mode),60)['text']==text


@pytest.mark.parametrize('state',['returning_home','returning_to_wash','going_to_wash_the_mop','returning_to_charge'])
def test_detailed_return_variants(state):
    assert activity.classify(changed(vacuum_state='idle',detail_state=state))[1]=='Returning to dock'


def test_stale_dock_operation_cannot_override_robot_moving():
    assert activity.classify(changed(vacuum_state='cleaning',detail_state='washing_the_mop',washing=True))[1]=='Cleaning'
    assert activity.classify(changed(vacuum_state='returning',detail_state='emptying_the_bin',emptying=True))[1]=='Returning to dock'
    assert activity.classify(changed(vacuum_state='docked',detail_state='cleaning'))[1]=='Docked'


def test_scheduled_target_and_enabled_flag_not_used_as_location_or_activity():
    tr=activity.ActivityTracker()
    d=changed(scheduled_room='Bathroom',scheduler_enabled=False)
    tr.update(d,0)
    assert tr.update(d,60)['text']=='Cleaning Kitchen'


@pytest.mark.parametrize('value',['unknown','unavailable','','not_in_a_room','0','-1',None])
def test_invalid_location_not_a_room(value):
    assert activity.resolve_room(value,[], 'Ground') is None


def test_numeric_segments_need_selected_map():
    maps=[{'flag':0,'name':'Ground','rooms':{'17':'Kitchen'}},{'flag':1,'name':'Upper','rooms':{'17':'Bedroom'}}]
    assert activity.resolve_room('17',maps,'Ground')=='Kitchen'
    assert activity.resolve_room('17.0',maps,'0')=='Kitchen'
    assert activity.resolve_room('17',maps,'Upper')=='Bedroom'
    assert activity.resolve_room('17',maps,'unknown') is None
    assert activity.resolve_room('29',maps,'Ground') is None
    assert activity.resolve_room('Kitchen',maps,'unknown')=='Kitchen'


def test_long_room_name_cannot_exceed_ha_state_limit():
    tr=activity.ActivityTracker(); d=changed(resolved_room='x'*300,mode='vac_and_mop')
    tr.update(d,0)
    assert len(tr.update(d,60)['text'])<=255


def test_restart_starts_new_confirmation_not_restored_history():
    tr=activity.ActivityTracker();tr.update(data(),0);tr.update(data(),60)
    reloaded=activity.ActivityTracker()
    assert reloaded.update(data(),1000)['room'] is None


@pytest.mark.parametrize('native,detail,expected',[
    ('paused','cleaning','Paused'),
    ('paused','emptying_the_bin','Paused'),
    ('cleaning','returning_home','Cleaning'),
    ('cleaning','going_to_target','Moving to target'),
    ('cleaning','mapping','Mapping'),
    ('docked','attaching_the_mop','Attaching mop'),
    ('docked','detaching_the_mop','Detaching mop'),
    ('docked','updating','Updating firmware'),
])
def test_native_state_and_compatible_details(native,detail,expected):
    assert activity.classify(changed(vacuum_state=native,detail_state=detail))[1]==expected
