"""0.2.0: no error ever needs acknowledging. Simulated telemetry only.

Dobby-level problems are logged, the room stays pending and the queue carries
on. Only an error the Roborock itself reports pauses Dobby, and only until the
vacuum clears it.
"""
import pytest
from test_engine import setup, step, start, finish_record, Engine, m


def pending(e, area='kitchen'):
    return next(j for j in e.jobs if j['area_id'] == area)


def fail_once(e, c, r, t):
    """Start the next room and have its mode command fail, then dock."""
    assert step(e, c, r, t)[0]['kind'] == 'set_mode'
    e.fault_effect('set_mode', 'Error while calling SET_MODE', t['now'])
    step(e, c, r, t)
    assert e.active is None


def test_command_failure_clears_itself_and_next_run_starts():
    e, c, r, t = setup()
    fail_once(e, c, r, t)
    assert not e.fault and e.issue['message'].startswith('set_mode:')
    assert pending(e)['status'] == 'needs_action' and pending(e)['failed_attempts'] == 1
    # Short pause, never a block; no retry()/OK call anywhere.
    assert step(e, c, r, t) == [] and 'Carrying on' in e.wait_reason
    assert step(e, c, r, t, seconds=m.RETRY_DELAY)[0]['kind'] == 'set_mode'
    assert e.issue is None


def test_internal_error_does_not_disable_schedule():
    e, c, r, t = setup()
    e.fault_effect('scheduler', 'boom', t['now'])
    assert e.enabled and not e.fault
    assert step(e, c, r, t, seconds=m.RETRY_DELAY + 1)[0]['kind'] == 'set_mode'


def test_repeatedly_failing_room_is_skipped_and_queue_carries_on():
    e, c, r, t = setup()
    for _ in range(m.MAX_ATTEMPTS):
        fail_once(e, c, r, t)
        t['now'] += m.RETRY_DELAY
    kitchen = pending(e)
    assert kitchen['status'] == 'needs_action' and 'Skipped after' in kitchen['reason']
    assert step(e, c, r, t)[0]['kind'] == 'set_mode'
    assert e.active['area_id'] == 'hallway'


def test_all_rooms_skipped_reports_without_blocking():
    e, c, r, t = setup()
    for _ in range(2 * m.MAX_ATTEMPTS):
        fail_once(e, c, r, t)
        t['now'] += m.RETRY_DELAY
    assert step(e, c, r, t) == [] and 'skipped' in e.wait_reason and not e.fault


def test_new_request_gives_skipped_room_another_chance():
    e, c, r, t = setup()
    for _ in range(m.MAX_ATTEMPTS):
        fail_once(e, c, r, t)
        t['now'] += m.RETRY_DELAY
    e.enqueue('kitchen', r, t['now'], urgent=True)
    assert 'failed_attempts' not in pending(e)
    assert step(e, c, r, t)[0]['kind'] == 'set_mode' and e.active['area_id'] == 'kitchen'


def test_retired_retry_clears_skip_counter_and_notice():
    e, c, r, t = setup()
    fail_once(e, c, r, t)
    e.retry(t['now'])
    assert e.issue is None and 'failed_attempts' not in pending(e)
    assert step(e, c, r, t)[0]['kind'] == 'set_mode'


def test_daily_reset_clears_skips():
    e, c, r, t = setup()
    for _ in range(m.MAX_ATTEMPTS):
        fail_once(e, c, r, t)
        t['now'] += m.RETRY_DELAY
    e.reset('tomorrow', r, t['now'])
    assert all('failed_attempts' not in j for j in e.jobs)


def test_roborock_error_mirrors_and_clears_automatically_while_idle():
    e, c, r, t = setup()
    assert step(e, c, r, t, error='problem', error_raw='main_brush_jammed') == []
    assert e.fault == 'Roborock reports a vacuum error: main_brush_jammed'
    assert 'waiting for it to clear' in e.wait_reason and e.active is None
    # Vacuum clears its own error: Dobby clears and carries on, no delay.
    assert step(e, c, r, t, error='ok', error_raw='none')[0]['kind'] == 'set_mode'
    assert e.fault == ''


def test_roborock_error_mid_clean_docks_and_resumes_without_counting_failure():
    e, c, r, t = setup()
    start(e, c, r, t)
    step(e, c, r, t, error='problem', error_raw='wheel_stuck')
    assert e.fault and e.active['phase'] == 'aborting'
    assert step(e, c, r, t) == [{'kind': 'dock'}]
    step(e, c, r, t, vacuum='docked')
    assert e.active is None and 'failed_attempts' not in pending(e)
    assert step(e, c, r, t) == []
    assert step(e, c, r, t, error='ok', error_raw='none')[0]['kind'] == 'set_mode'


def test_roborock_dock_error_pauses_and_clears():
    e, c, r, t = setup()
    assert step(e, c, r, t, dock_error='problem', dock_error_raw='duct_blockage') == []
    assert 'dock error: duct_blockage' in e.fault
    assert step(e, c, r, t, dock_error='ok', dock_error_raw='ok')[0]['kind'] == 'set_mode'


@pytest.mark.parametrize('raw', ['unavailable', 'unknown'])
def test_unavailable_error_sensor_waits_but_is_not_a_roborock_fault(raw):
    e, c, r, t = setup()
    assert step(e, c, r, t, error='problem', error_raw=raw) == []
    assert e.fault == '' and 'unavailable' in e.wait_reason
    assert step(e, c, r, t, error='ok', error_raw='none')[0]['kind'] == 'set_mode'


def test_roborock_error_after_proved_clean_keeps_completion():
    e, c, r, t = setup()
    at = start(e, c, r, t)
    step(e, c, r, t, seconds=200, vacuum='docked', record=finish_record(at))
    assert e.active['proved']
    step(e, c, r, t, dock_error='problem', dock_error_raw='duct_blockage')
    assert pending(e)['status'] == 'completed' and e.active is None


def test_failed_finishing_dock_command_keeps_proved_clean():
    e, c, r, t = setup()
    at = start(e, c, r, t)
    assert step(e, c, r, t, seconds=200, vacuum='idle', record=finish_record(at)) == [{'kind': 'dock'}]
    e.fault_effect('dock', 'Error while calling APP_CHARGE', t['now'])
    assert pending(e)['status'] == 'completed' and not e.fault
    # The next room still needs a real docked reading before it starts.
    assert step(e, c, r, t, seconds=m.RETRY_DELAY) == [] and 'dock' in e.wait_reason


def test_unproved_dock_failure_never_marks_done():
    e, c, r, t = setup()
    start(e, c, r, t)
    e.fault_effect('dock', 'Error while calling APP_CHARGE', t['now'])
    step(e, c, r, t, vacuum='docked')
    assert e.active is None and pending(e)['status'] == 'needs_action'


def test_old_saved_fault_is_not_restored_and_issue_does_not_block():
    e, c, r, t = setup()
    saved = e.export()
    saved['fault'] = 'dock: Error while calling APP_CHARGE'
    saved['issue'] = {'at': t['now'] - 10 * m.RETRY_DELAY, 'message': 'old'}
    e2 = Engine(saved); e2.enabled = True; e2.away_since = e.away_since
    assert e2.fault == ''
    assert step(e2, c, r, t)[0]['kind'] == 'set_mode'


def test_repeated_same_issue_is_logged_once():
    e, c, r, t = setup()
    for _ in range(5):
        e.report_issue('scheduler: boom', t['now'])
    assert sum(1 for row in e.log if row['message'] == 'scheduler: boom') == 1
