"""Compact room-aware Activity states; simulated telemetry, no robot access."""
from copy import deepcopy
import pytest
from test_activity import activity, changed
from test_activity_adapter import setup
from test_adapter import adapter


@pytest.mark.parametrize('mode, expected, code', [
    ('vacuum', 'Vacuuming \u00b7 Kitchen', 'cleaning'),
    ('vac_and_mop', 'Vac + mop \u00b7 Kitchen', 'vacuuming_and_mopping'),
    ('mop', 'Mopping \u00b7 Kitchen', 'mopping'),
    ('custom', 'Cleaning \u00b7 Kitchen', 'cleaning'),
    ('unknown', 'Cleaning \u00b7 Kitchen', 'cleaning'),
])
def test_confirmed_short_mode_and_unchanged_codes(mode, expected, code):
    tr = activity.ActivityTracker()
    d = changed(mode=mode)
    tr.update(d, 0)
    a = tr.update(d, 60)
    assert a['text'] == expected and a['code'] == code
    assert a['room'] == a['display_room'] == 'Kitchen'
    assert a['display_room_source'] == 'confirmed'
    assert a['room_is_current']


def owned(**kw):
    d = changed(mode='vac_and_mop', scheduled_room='Kitchen', scheduled_run_id='job:100')
    d.update(kw)
    return d


def test_owned_target_is_immediate_but_not_an_observed_location():
    tr = activity.ActivityTracker()
    for now in (0, 15, 59.9):
        a = tr.update(owned(), now)
        assert a['text'] == 'Vac + mop \u2192 Kitchen'
        assert a['display_room_source'] == 'scheduled'
        assert a['room'] is None and a['confirmed_room'] is None
        assert not a['room_is_current']
    a = tr.update(owned(), 60)
    assert a['text'] == 'Vac + mop \u00b7 Kitchen'
    assert a['display_room_source'] == 'confirmed'


def test_missing_room_sensor_keeps_honest_target_indefinitely():
    tr = activity.ActivityTracker()
    d = owned(resolved_room=None, room_source='')
    for now in (0, 59, 60, 999):
        a = tr.update(d, now)
        assert a['text'] == 'Vac + mop \u2192 Kitchen'
        assert a['room'] is None and not a['room_available']
        assert 'scheduled room: Kitchen' in a['detail_text']


def test_confirmed_actual_room_wins_over_different_scheduled_target():
    tr = activity.ActivityTracker()
    d = owned(resolved_room='Hallway')
    tr.update(d, 0)
    a = tr.update(d, 60)
    assert a['text'] == 'Vac + mop \u00b7 Hallway'
    assert a['display_room_source'] == 'confirmed'


def test_room_in_transit_still_requires_one_minute():
    tr = activity.ActivityTracker()
    tr.update(owned(), 0); tr.update(owned(), 60)
    d = owned(resolved_room='Hallway')
    assert tr.update(d, 61)['text'] == 'Vac + mop \u00b7 Kitchen'
    assert not tr.update(d, 119)['room_is_current']
    assert tr.update(d, 121)['text'] == 'Vac + mop \u00b7 Hallway'


def test_new_attempt_does_not_inherit_previous_cleaning_room():
    tr = activity.ActivityTracker()
    tr.update(owned(), 0); tr.update(owned(), 60)
    new = owned(scheduled_room='Bedroom', scheduled_run_id='second:200')
    a = tr.update(new, 65)
    assert a['text'] == 'Vac + mop \u2192 Bedroom' and a['room'] is None
    assert a['confirmed_room'] == 'Kitchen'  # Independent physical history is retained.


def test_reused_job_uid_with_new_command_resets_cleaning_confirmation():
    tr = activity.ActivityTracker()
    tr.update(owned(), 0); tr.update(owned(), 60)
    a = tr.update(owned(scheduled_run_id='job:300', mode='vacuum'), 90)
    assert a['text'] == 'Vacuuming \u2192 Kitchen' and a['room'] is None


def test_unowned_scheduled_name_is_not_a_location_or_job():
    tr = activity.ActivityTracker()
    a = tr.update(changed(mode='vac_and_mop', resolved_room=None, scheduled_room='Kitchen'), 0)
    assert a['text'] == 'Vac + mop'
    assert a['display_room'] is None


@pytest.mark.parametrize('delta, expected, code', [
    ({'vacuum_state': 'returning'}, 'Returning', 'returning'),
    ({'vacuum_state': 'docked', 'emptying': True}, 'Emptying', 'emptying'),
    ({'vacuum_state': 'docked', 'washing': True}, 'Washing mop', 'washing_mop'),
    ({'vacuum_state': 'docked', 'drying': True}, 'Drying mop', 'drying_mop'),
    ({'vacuum_state': 'docked'}, 'Docked', 'docked'),
    ({'vacuum_state': 'paused'}, 'Paused', 'paused'),
    ({'error_raw': 'main_brush_jammed'}, 'Main brush jammed', 'error'),
    ({'dock_error_raw': 'dust_bag_missing'}, 'Dust bag missing', 'dock_error'),
    ({'vacuum_state': 'unavailable'}, 'Unavailable', 'unavailable'),
    ({'detail_state': 'going_to_target'}, 'Moving', 'moving'),
])
def test_non_cleaning_states_never_append_scheduled_target(delta, expected, code):
    tr = activity.ActivityTracker()
    tr.update(owned(), 0); tr.update(owned(), 60)
    a = tr.update(owned(**delta), 60.01)
    assert a['text'] == expected and a['code'] == code
    assert a['room'] is None and a['display_room'] is None


def active(c, **kw):
    c.engine.active = dict(uid='a', name='Kitchen', phase='cleaning', command_at=100,
                           interrupted=False, area_id='kitchen', mode='vac_and_mop')
    c.engine.active.update(kw)


def test_adapter_supplies_dispatched_job_without_observed_room(adapter):
    m, c, h, calls = adapter; setup(c, h)
    active(c)
    h.states.add('select.test_cleaning_mode', 'vac_and_mop')
    h.states.add('sensor.test_current_room', 'unknown')
    before = deepcopy(c.engine.export())
    c.update_activity()
    assert c.activity['text'] == 'Vac + mop \u2192 Kitchen'
    assert c.activity['display_room_source'] == 'scheduled'
    assert c.activity['room'] is None
    assert c.engine.export() == before and not calls and not c.store.saved


@pytest.mark.parametrize('values', [
    {'phase': 'preparing'}, {'phase': 'aborting'}, {'phase': 'verifying'},
    {'phase': 'emptying'}, {'command_at': None}, {'uid': None}, {'interrupted': True},
])
def test_non_dispatched_or_interrupted_job_not_used(adapter, values):
    m, c, h, calls = adapter; setup(c, h); active(c, **values)
    h.states.add('sensor.test_current_room', 'unknown')
    c.update_activity()
    assert c.activity['text'] == 'Vacuuming'
    assert c.activity['display_room'] is None
    assert not calls


def test_saved_fault_does_not_grant_scheduled_display(adapter):
    m, c, h, calls = adapter; setup(c, h); active(c)
    c.engine.fault = 'Previous command failed'
    c.update_activity()
    assert c.activity['display_room_source'] is None


def test_pending_daily_queue_is_not_mistaken_for_active_job(adapter):
    m, c, h, calls = adapter; setup(c, h)
    c.engine.jobs = [dict(uid='q', name='Kitchen', area_id='kitchen', status='needs_action')]
    c.update_activity()
    assert c.activity['text'] == 'Vacuuming' and c.activity['display_room'] is None


def test_actual_mode_wins_over_requested_mopping_on_water_fallback(adapter):
    m, c, h, calls = adapter; setup(c, h)
    active(c, mode='vacuum', requested_mode='vac_and_mop', water_fallback=True)
    c.update_activity()
    assert c.activity['text'] == 'Vacuuming \u2192 Kitchen'
    assert c.activity['code'] == 'cleaning'


def test_target_does_not_leak_into_confirmed_room_sensor(adapter):
    m, c, h, calls = adapter; setup(c, h); active(c)
    c.update_activity()
    assert c.activity['display_room'] == 'Kitchen'
    assert c.activity['confirmed_room'] is None and c.activity['room'] is None


def test_long_target_name_is_bounded():
    a = activity.ActivityTracker().update(owned(scheduled_room='x' * 600, resolved_room=None), 0)
    assert len(a['text']) <= 250 and len(a['detail_text']) <= 250
