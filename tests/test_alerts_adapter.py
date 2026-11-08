"""HA adapter simulations for 0.2.0 notifications and Repairs; no live HA."""
import asyncio
import sys
from enum import Enum
from types import ModuleType, SimpleNamespace as NS
import pytest
from test_adapter import adapter, run


@pytest.fixture
def issues(monkeypatch):
    created, deleted = {}, []
    ir = ModuleType('homeassistant.helpers.issue_registry')
    ir.IssueSeverity = Enum('IssueSeverity', 'WARNING ERROR')
    ir.async_create_issue = lambda hass, domain, issue_id, **kw: created.__setitem__(issue_id, kw)
    ir.async_delete_issue = lambda hass, domain, issue_id: deleted.append(issue_id)
    monkeypatch.setitem(sys.modules, 'homeassistant.helpers.issue_registry', ir)
    helpers = sys.modules['homeassistant.helpers']
    monkeypatch.setattr(helpers, 'issue_registry', ir, raising=False)
    return created, deleted


def deliver(c, *events):
    c.engine.events.extend(events)
    asyncio.run(c.deliver_alerts())


def test_attention_raises_repair_and_phone_notification_with_retry(adapter, issues):
    m, c, h, calls = adapter; created, deleted = issues
    c.settings['notify_service'] = 'notify.mobile_app_phone'
    deliver(c, {'kind': 'attention', 'fault': 'error: main brush jammed'})
    assert created['needs_attention_test']['translation_placeholders']['fault'] == 'error: main brush jammed'
    (domain, name, data), kw = calls[-1]
    assert (domain, name) == ('notify', 'mobile_app_phone')
    assert data['data']['actions'][0]['action'] == 'DOBBY_SCHEDULER_RETRY'
    assert c.engine.events == []


def test_resolved_clears_repair(adapter, issues):
    m, c, h, calls = adapter; created, deleted = issues
    deliver(c, {'kind': 'resolved'})
    assert deleted == ['needs_attention_test']


def test_skipped_room_notifies_without_repair(adapter, issues):
    m, c, h, calls = adapter; created, deleted = issues
    c.settings['notify_service'] = 'notify.family'
    deliver(c, {'kind': 'skipped', 'room': 'Kitchen', 'reason': 'Room time limit reached'})
    assert not created
    (domain, name, data), kw = calls[-1]
    assert name == 'family' and 'Kitchen' in data['message'] and 'data' not in data


def test_no_notify_target_is_quiet_but_repair_still_raised(adapter, issues):
    m, c, h, calls = adapter; created, deleted = issues
    before = len(calls)
    deliver(c, {'kind': 'attention', 'fault': 'x'})
    assert len(calls) == before and created


def test_notification_failure_never_breaks_scheduler(adapter, issues):
    m, c, h, calls = adapter
    async def boom(*a, **kw): raise RuntimeError('notify down')
    h.services = NS(async_call=boom)
    c.settings['notify_service'] = 'notify.mobile_app_phone'
    deliver(c, {'kind': 'attention', 'fault': 'x'})  # no exception


def test_phone_retry_button_runs_retry(adapter):
    m, c, h, calls = adapter
    seen = []
    async def fake_command(action, p=None): seen.append(action)
    c.command = fake_command
    c.engine.fault = 'dock: failed'
    tasks = []
    h.async_create_task = lambda coro: tasks.append(coro)
    c._notification_action(NS(data={'action': 'DOBBY_SCHEDULER_RETRY'}))
    c._notification_action(NS(data={'action': 'SOMETHING_ELSE'}))
    assert len(tasks) == 1
    asyncio.run(tasks[0])
    assert seen == ['retry']


@pytest.mark.parametrize('key,value,ok', [
    ('auto_retries', 0, True), ('auto_retries', 5, True), ('auto_retries', 6, False),
    ('recovery_delay', 30, True), ('recovery_delay', 10, False),
    ('attention_after', 240, True), ('attention_after', 0, False),
    ('notify_service', '', True), ('notify_service', 'notify.mobile_app_phone', True),
    ('notify_service', 'light.turn_on', False), ('notify_service', 'notify.', False),
    ('notify_service', 'notify.bad name', False),
])
def test_new_settings_are_validated(adapter, key, value, ok):
    m, c, h, calls = adapter
    if ok:
        assert c.validate_settings({key: value})[key] == value
    else:
        with pytest.raises(ValueError):
            c.validate_settings({key: value})


def test_unknown_notify_action_rejected_when_services_known(adapter):
    m, c, h, calls = adapter
    h.services.has_service = lambda domain, name: name == 'mobile_app_phone'
    assert c.validate_settings({'notify_service': 'notify.mobile_app_phone'})
    with pytest.raises(ValueError):
        c.validate_settings({'notify_service': 'notify.mobile_app_old_phone'})


def test_snapshot_reports_recovery_state(adapter):
    m, c, h, calls = adapter
    c.engine.fault = 'dock: failed'; c.engine.fault_at = 0
    snap = c.snapshot()
    assert snap['needs_attention'] is True          # long past the attention window
    assert snap['fault_retry']['limit'] == c.settings['auto_retries']
    assert snap['skipped_rooms'] == []
