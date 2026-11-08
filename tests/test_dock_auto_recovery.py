"""Self-healing fault tests (0.2.0); simulated telemetry, no Roborock commands.

A latched fault clears itself only after Dobby has been observed docked and
healthy for the recovery delay. Each room gets a small daily retry budget, then
it is skipped for today so the rest of the queue can continue. Clearing a fault
never starts work by itself and never marks a room complete.
"""
import pytest
from test_engine import setup, step, start, finish_record, Engine
from test_immediate_priority import request


def fault(e, t, text="Error while calling APP_CHARGE", effect="dock"):
    e.fault_effect(effect, text, t["now"])
    assert e.fault


def wait_recovery(e, c, r, t):
    """First healthy reading starts the timer; the delay later it may clear."""
    first = step(e, c, r, t)
    assert e.fault and first == []
    return step(e, c, r, t, seconds=c['recovery_delay'])


def fail_running_room(e, c, r, t):
    """Start (or continue starting) the next room, latch a robot error mid-clean, re-dock."""
    if e.active is None:
        assert step(e, c, r, t)[0]['kind'] == 'set_mode'
    assert step(e, c, r, t, mode=e.active['mode'])[0]['kind'] == 'clean'
    step(e, c, r, t, vacuum='cleaning')
    step(e, c, r, t, error='main brush jammed')
    assert e.fault and e.active['phase'] == 'aborting'
    step(e, c, r, t, error='ok', vacuum='docked')
    assert e.active is None and e.fault


def test_dock_error_at_rest_recovers_after_delay():
    e, c, r, t = setup(); fault(e, t)
    assert step(e, c, r, t) == []
    assert step(e, c, r, t, seconds=c['recovery_delay'] - 1) == []
    assert 'retrying automatically' in e.wait_reason
    # Cleared, and the normal gates allow the next room in the same tick.
    assert step(e, c, r, t, seconds=1) == [{'kind': 'set_mode', 'option': 'vac_and_mop'}]
    assert not e.fault
    assert e.active['area_id'] == 'kitchen'


@pytest.mark.parametrize('reason', [
    'error: main brush jammed',
    'completion: Docked without a confirmed successful clean.',
    'empty: No observed dust-emptying on/off cycle.',
    'dock: connection timeout',
    'set_mode: Requested mode did not confirm',
    'Room time limit reached',
    'Dobby never confirmed cleaning; check the command/map',
])
def test_any_robot_fault_self_heals_when_docked_and_healthy(reason):
    e, c, r, t = setup(); e.fault = reason; e.fault_at = t['now']
    wait_recovery(e, c, r, t)
    assert not e.fault


def test_internal_scheduler_fault_never_auto_clears_and_asks_for_help():
    e, c, r, t = setup(); fault(e, t, 'boom', effect='scheduler')
    step(e, c, r, t); step(e, c, r, t, seconds=c['recovery_delay'] * 3)
    assert e.fault.startswith('scheduler:')
    assert {'kind': 'attention', 'fault': e.fault} in e.events


@pytest.mark.parametrize('field,value', [
    ('vacuum', 'returning'), ('vacuum', 'cleaning'), ('vacuum', 'idle'),
    ('vacuum', 'unknown'), ('connected', False), ('error', 'problem'),
    ('dock_error', 'problem'), ('dock_error', 'unknown'), ('emptying', True),
    ('washing', True), ('blockers', True), ('legacy', [{'entity_id': 'automation.old'}]),
])
def test_unhealthy_telemetry_never_clears_fault(field, value):
    e, c, r, t = setup(); fault(e, t); t[field] = value
    step(e, c, r, t); step(e, c, r, t, seconds=c['recovery_delay'] * 2)
    assert e.fault and e.active is None


@pytest.mark.parametrize('field', ['emptying', 'washing'])
def test_configured_dock_service_unknown_counts_as_busy(field):
    e, c, r, t = setup()
    c['empty_entity'] = 'switch.dobby_dock_dust_emptying'
    c['wash_entity'] = 'switch.dobby_dock_mop_washing'
    fault(e, t); t[field] = None
    step(e, c, r, t); step(e, c, r, t, seconds=c['recovery_delay'] * 2)
    assert e.fault


def test_recovery_timer_restarts_if_robot_leaves_dock():
    e, c, r, t = setup(); fault(e, t)
    step(e, c, r, t)
    step(e, c, r, t, seconds=c['recovery_delay'] - 5, vacuum='returning')
    assert e._recover_since is None
    step(e, c, r, t, seconds=1, vacuum='docked')
    step(e, c, r, t, seconds=c['recovery_delay'] - 1)
    assert e.fault
    step(e, c, r, t, seconds=1)
    assert not e.fault


@pytest.mark.parametrize('field,value', [
    ('home', True), ('battery', 5), ('map_name', 'different'), ('record_supported', False),
])
def test_clearing_fault_does_not_bypass_normal_start_checks(field, value):
    e, c, r, t = setup(); fault(e, t); t[field] = value
    wait_recovery(e, c, r, t)
    assert not e.fault
    assert step(e, c, r, t, seconds=60) == [] and e.active is None


def test_disabled_scheduler_still_clears_fault_but_starts_nothing():
    e, c, r, t = setup(); e.enabled = False; fault(e, t)
    wait_recovery(e, c, r, t)
    assert not e.fault
    assert step(e, c, r, t, seconds=60) == [] and e.wait_reason == 'Scheduler disabled'


def test_room_failure_retries_then_skips_and_queue_continues():
    e, c, r, t = setup()
    kitchen = e.jobs[0]
    for attempt in range(1, c['auto_retries'] + 1):
        fail_running_room(e, c, r, t)
        wait_recovery(e, c, r, t)
        assert not e.fault and kitchen['auto_retries'] == attempt
        assert kitchen['status'] == 'needs_action' and not kitchen.get('skipped')
    fail_running_room(e, c, r, t)
    wait_recovery(e, c, r, t)
    assert not e.fault
    assert kitchen['skipped'] and kitchen['status'] == 'needs_action'
    assert 'Skipped for today' in kitchen['reason']
    assert any(ev['kind'] == 'skipped' and ev['room'] == 'Kitchen' for ev in e.events)
    # The next room runs instead of the whole day being blocked.
    assert e.active['area_id'] == 'hallway'


def test_zero_retries_skips_room_on_first_fault():
    e, c, r, t = setup(); c['auto_retries'] = 0
    fail_running_room(e, c, r, t)
    wait_recovery(e, c, r, t)
    assert e.jobs[0]['skipped'] and not e.fault


def test_new_day_requeues_skipped_rooms_with_fresh_budget():
    e, c, r, t = setup(); c['auto_retries'] = 0
    r['hallway']['daily'] = False; e.jobs = e.jobs[:1]
    fail_running_room(e, c, r, t); wait_recovery(e, c, r, t)
    assert e.jobs[0]['skipped'] and e.active is None
    step(e, c, r, t, seconds=86400, home=True)
    assert [j['area_id'] for j in e.jobs] == ['kitchen']
    assert not any(j.get('skipped') or j.get('auto_retries') for j in e.jobs)


def test_fault_survives_restart_and_retry_budget_persists():
    e, c, r, t = setup()
    fail_running_room(e, c, r, t); wait_recovery(e, c, r, t)
    fail_running_room(e, c, r, t)
    reloaded = Engine(e.export())
    assert reloaded.fault and reloaded.fault_uid == e.jobs[0]['uid']
    assert reloaded.jobs[0]['auto_retries'] == 1
    wait_recovery(reloaded, c, r, t)
    assert not reloaded.fault and reloaded.jobs[0]['auto_retries'] == 2


def test_old_saved_fault_without_metadata_still_recovers():
    e, c, r, t = setup()
    saved = e.export(); saved['fault'] = 'dock: Error while calling APP_CHARGE'
    saved.pop('fault_at'); saved.pop('fault_uid')
    e = Engine(saved)
    wait_recovery(e, c, r, t)
    assert not e.fault


def test_unattached_faults_are_bounded():
    e, c, r, t = setup(); e.jobs = []
    for _ in range(3):
        fault(e, t); wait_recovery(e, c, r, t)
        assert not e.fault
    fault(e, t); wait_recovery(e, c, r, t)
    assert e.fault


def test_new_explicit_request_resets_retry_budget_and_skip():
    e, c, r, t = setup()
    j = e.jobs[0]; j.update(auto_retries=3, skipped=True, skipped_reason='x', dock_auto_retry_used=True)
    e.enqueue('kitchen', r, t['now'], urgent=True, source='dashboard')
    assert not any(k in j for k in ('auto_retries', 'skipped', 'skipped_reason', 'dock_auto_retry_used'))


def test_skipped_room_is_not_run_by_switch_request_unless_requeued():
    e, c, r, t = setup(); c['auto_retries'] = 0
    fail_running_room(e, c, r, t); wait_recovery(e, c, r, t)
    assert e.active['area_id'] == 'hallway'          # queue moved on
    step(e, c, r, t, home=True)                       # ordinary job stops at arrival
    step(e, c, r, t, vacuum='docked')
    assert e.active is None
    uid = request(e, r, t, 'kitchen')  # a fresh request is a fresh attempt
    assert not e.find(uid).get('skipped')
    assert step(e, c, r, t)[0]['kind'] == 'set_mode' and e.active['area_id'] == 'kitchen'


def test_attention_event_once_when_stuck_and_resolved_when_cleared():
    e, c, r, t = setup(); fault(e, t); t['vacuum'] = 'idle'   # stranded off the dock
    step(e, c, r, t)
    step(e, c, r, t, seconds=c['recovery_delay'] + c['attention_after'] * 60 - 2)
    assert not [ev for ev in e.events if ev['kind'] == 'attention']
    step(e, c, r, t, seconds=2)
    step(e, c, r, t, seconds=30)
    assert len([ev for ev in e.events if ev['kind'] == 'attention']) == 1
    t['vacuum'] = 'docked'
    wait_recovery(e, c, r, t)
    assert not e.fault and e.events[-1] == {'kind': 'resolved'}


def test_aborting_job_is_not_completed_from_dock_error():
    e, c, r, t = setup(); start(e, c, r, t)
    e.abort('Returning home', t['now'])
    fault(e, t)
    step(e, c, r, t, vacuum='docked')
    assert e.fault and e.active is None
    assert e.jobs[0]['status'] == 'needs_action'
    wait_recovery(e, c, r, t)
    assert not e.fault and e.jobs[0]['status'] == 'needs_action'


def test_verified_clean_preserves_success_proof_if_dock_rpc_failed():
    e, c, r, t = setup(); at = start(e, c, r, t)
    step(e, c, r, t, seconds=200, vacuum='idle', record=finish_record(at))
    assert e.active['proved']
    fault(e, t)
    step(e, c, r, t, seconds=2, vacuum='docked')
    step(e, c, r, t, seconds=c['recovery_delay'])
    assert not e.fault and e.active['proved'] and e.active['phase'] == 'verifying'
    assert e.jobs[0]['status'] == 'needs_action'


def test_no_fresh_record_and_dock_cannot_mark_done():
    e, c, r, t = setup(); start(e, c, r, t)
    fault(e, t)
    wait_recovery(e, c, r, t.update(vacuum='docked') or t)
    assert not e.fault
    assert e.jobs[0]['status'] == 'needs_action'


def test_manual_retry_still_works_immediately():
    e, c, r, t = setup(); fault(e, t)
    e.retry(t['now'], docked=True)
    assert not e.fault and e.fault_uid is None
