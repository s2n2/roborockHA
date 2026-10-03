"""Deterministic scheduler tests. All robot telemetry below is simulated."""
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta, timezone
from copy import deepcopy
import pytest

PATH = Path(__file__).parents[1] / 'custom_components/dobby_scheduler/engine.py'
spec = importlib.util.spec_from_file_location('dobby_engine_test', PATH)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
Engine, GestureDetector, DEFAULTS = m.Engine, m.GestureDetector, m.DEFAULTS
LOCAL = datetime(2026,10,3,10,0,tzinfo=timezone(timedelta(hours=13)))
NOW = LOCAL.timestamp()


def room(id='kitchen', priority=10, mode='vac_and_mop', daily=True):
    return dict(area_id=id, name=id.title(), cleanable=True, daily=daily, mode=mode,
                verified=True, segments=[29 if id=='kitchen' else 24], map_flag=0,
                map_name='Original', priority=priority, mapping_error='')


def setup():
    cfg=deepcopy(DEFAULTS)
    rooms={'kitchen':room(), 'hallway':room('hallway',20), 'bedroom':room('bedroom',100,'vacuum',False)}
    e=Engine();e.enabled=True;e.reset(m.cleaning_day(LOCAL,cfg['reset_time']),rooms,NOW)
    e.away_since=NOW-1000
    t=dict(now=NOW,home=False,connected=True,vacuum='docked',mode='vacuum',
           mode_options=['vacuum','vac_and_mop','mop'],battery=90,error='ok',
           map_name='Original',map_flag=0,emptying=False,washing=False,wet_ok=True,
           blockers=False,legacy=[],record_supported=True,record=None,empty_count=4,
           mop_intensity='medium')
    return e,cfg,rooms,t


def step(e,cfg,rooms,t,seconds=1,**values):
    t.update(values); t['now']+=seconds
    local=LOCAL+timedelta(seconds=t['now']-NOW)
    return e.tick(t,cfg,rooms,local)


def start(e,cfg,rooms,t):
    assert step(e,cfg,rooms,t)==[{'kind':'set_mode','option':'vac_and_mop'}]
    result=step(e,cfg,rooms,t,mode='vac_and_mop')
    assert result[0]['kind']=='clean'
    at=e.active['command_at']
    step(e,cfg,rooms,t,vacuum='cleaning')
    assert e.active['seen_cleaning']
    return at


def finish_record(at):
    return dict(begin=at+1,end=at+180,complete=1,error=0,area=12000000,map_flag=0)


def test_default_order_and_daily_only():
    e,c,r,t=setup();assert [j['area_id'] for j in e.jobs]==['kitchen','hallway']


def test_promote_does_not_duplicate_and_completed_can_repeat():
    e,c,r,t=setup();uid=e.enqueue('hallway',r,NOW,True,'wall_toggle')
    assert len(e.jobs)==2 and e.jobs[0]['uid']==uid
    e.manual_complete(uid,NOW,True)
    e.enqueue('hallway',r,NOW+1,True)
    assert len(e.jobs)==2 and e.jobs[0]['status']=='needs_action'


def test_promotion_keeps_current_room():
    e,c,r,t=setup();start(e,c,r,t)
    e.enqueue('bedroom',r,NOW+3,True,'wall_toggle')
    assert e.active['area_id']=='kitchen' and e.jobs[0]['area_id']=='bedroom'


def test_native_move_order():
    e,c,r,t=setup();first,second=[j['uid'] for j in e.jobs]
    e.move(second,None);assert e.jobs[0]['uid']==second
    e.move(second,first);assert e.jobs[-1]['uid']==second


def test_disabled_on_new_install():
    e,c,r,t=setup();e.enabled=False
    assert step(e,c,r,t)==[] and e.active is None


def test_away_delay():
    e,c,r,t=setup();e.away_since=None
    assert step(e,c,r,t)==[]
    assert step(e,c,r,t,seconds=899)==[]
    assert step(e,c,r,t,seconds=2)[0]['kind']=='set_mode'


@pytest.mark.parametrize('field,value',[
    ('home',True),('home',None),('connected',False),('battery',5),('battery',None),
    ('error','problem'),('map_name','Other map'),('map_flag',2),('blockers',True),
    ('record_supported',False),('legacy',[{'entity_id':'automation.old'}]),
    ('emptying',True),('emptying',None),('washing',True),('wet_ok',False),('vacuum','cleaning')
])
def test_preflight_blocks(field,value):
    e,c,r,t=setup();t[field]=value
    assert step(e,c,r,t)==[] and e.active is None


@pytest.mark.parametrize('field,value',[('verified',False),('mode',None),('mapping_error','duplicate segments'),('cleanable',False)])
def test_invalid_room_blocks(field,value):
    e,c,r,t=setup();r['kitchen'][field]=value
    assert step(e,c,r,t)==[] and e.active is None


def test_mop_washing_is_not_room_completion():
    e,c,r,t=setup();start(e,c,r,t)
    step(e,c,r,t,seconds=120,vacuum='docked',washing=True)
    assert e.jobs[0]['status']=='needs_action' and e.active
    step(e,c,r,t,seconds=40,vacuum='cleaning',washing=False)
    assert e.active and e.jobs[0]['status']=='needs_action'


def test_success_requires_empty_cycle_and_dock():
    e,c,r,t=setup();at=start(e,c,r,t)
    assert step(e,c,r,t,seconds=200,vacuum='returning',record=finish_record(at))==[]
    assert e.jobs[0]['status']=='needs_action'
    assert step(e,c,r,t,vacuum='docked')==[]
    assert step(e,c,r,t,seconds=11)==[{'kind':'empty'}]
    assert step(e,c,r,t,emptying=True)==[]
    assert e.jobs[0]['status']=='needs_action'
    assert step(e,c,r,t,seconds=30,emptying=False)==[]
    assert e.jobs[0]['status']=='completed' and e.active is None


def test_observed_automatic_empty_does_not_run_twice():
    e,c,r,t=setup();at=start(e,c,r,t)
    step(e,c,r,t,seconds=200,vacuum='docked',record=finish_record(at),emptying=True)
    assert step(e,c,r,t,seconds=40,emptying=False)==[]
    assert e.jobs[0]['status']=='completed'


def test_counter_can_confirm_missed_empty_switch_cycle():
    e,c,r,t=setup();at=start(e,c,r,t)
    step(e,c,r,t,seconds=200,vacuum='docked',record=finish_record(at))
    assert step(e,c,r,t,seconds=30,empty_count=5)==[]
    assert e.jobs[0]['status']=='completed'


def test_dock_alone_never_completes():
    e,c,r,t=setup();start(e,c,r,t)
    step(e,c,r,t,seconds=200,vacuum='docked')
    step(e,c,r,t,seconds=250)
    assert e.jobs[0]['status']=='needs_action' and e.fault


@pytest.mark.parametrize('change',[{'complete':0},{'error':1},{'area':0},{'map_flag':3},{'begin':NOW-1000},{'end':NOW+90000}])
def test_bad_record_never_completes(change):
    e,c,r,t=setup();at=start(e,c,r,t);record=finish_record(at);record.update(change)
    step(e,c,r,t,seconds=200,vacuum='docked',record=record,empty_count=5)
    step(e,c,r,t,seconds=250)
    assert e.jobs[0]['status']=='needs_action'


def test_old_success_record_is_not_new_success():
    e,c,r,t=setup();t['record']={'begin':NOW-1200,'end':NOW-1000,'complete':1,'error':0,'area':3,'map_flag':0}
    start(e,c,r,t);step(e,c,r,t,seconds=200,vacuum='docked',empty_count=5)
    assert not e.active['proved']


def test_arrival_docks_and_preserves_pending():
    e,c,r,t=setup();start(e,c,r,t)
    assert step(e,c,r,t,home=True)==[{'kind':'dock'}]
    step(e,c,r,t,vacuum='docked')
    assert e.active is None and e.jobs[0]['status']=='needs_action'
    step(e,c,r,t,home=False);assert e.active is None
    assert step(e,c,r,t,seconds=901)[0]['kind']=='set_mode'


def test_reset_deferred_and_restores_order():
    e,c,r,t=setup();start(e,c,r,t);e.enqueue('bedroom',r,t['now'],True)
    assert not e.reset('2026-10-04',r,t['now'])
    assert e.reset_deferred and len(e.jobs)==3
    e.abort('test',t['now']);step(e,c,r,t,vacuum='docked')
    e.reset('2026-10-04',r,t['now'])
    assert [j['area_id'] for j in e.jobs]==['kitchen','hallway']


def test_restart_recovers_owned_job_without_success():
    e,c,r,t=setup();start(e,c,r,t);e.manual=e.allow_home=True
    new=Engine(e.export());assert not new.manual and not new.allow_home
    assert new.active['phase']=='aborting'
    step(new,c,r,t,home=False,vacuum='docked')
    assert new.active is None and new.jobs[0]['status']=='needs_action'


def test_empty_timeout_requires_attention_not_success():
    e,c,r,t=setup();at=start(e,c,r,t)
    step(e,c,r,t,seconds=200,vacuum='docked',record=finish_record(at));step(e,c,r,t,seconds=11)
    step(e,c,r,t,seconds=250)
    assert e.fault and e.jobs[0]['status']=='needs_action'
    e.retry(t['now'],True)
    assert e.active['proved'] and e.active['phase']=='verifying'
    assert step(e,c,r,t,seconds=11)==[{'kind':'empty'}]


def test_physical_low_battery_return_requeues():
    e,c,r,t=setup();at=start(e,c,r,t);rec=finish_record(at);rec['complete']=0
    step(e,c,r,t,seconds=200,vacuum='docked',record=rec,battery=15)
    step(e,c,r,t,seconds=250)
    assert not e.fault and not e.active and e.jobs[0]['status']=='needs_action'
    assert step(e,c,r,t)==[]
    assert step(e,c,r,t,battery=60)[0]['kind']=='set_mode'


def test_manual_complete_requires_dock():
    e,c,r,t=setup()
    with pytest.raises(ValueError):e.manual_complete(e.jobs[0]['uid'],NOW,False)


def test_active_cannot_be_removed():
    e,c,r,t=setup();start(e,c,r,t)
    with pytest.raises(ValueError):e.remove(e.active['uid'])


def test_manual_run_at_home_needs_explicit_permission():
    e,c,r,t=setup();e.enabled=False;e.manual=True
    assert step(e,c,r,t,home=True)==[]
    e.allow_home=True
    assert step(e,c,r,t)[0]['kind']=='set_mode'


def test_vacuum_only_does_not_require_water():
    e,c,r,t=setup();r['kitchen']['mode']='vacuum'
    assert step(e,c,r,t,wet_ok=False)==[{'kind':'set_mode','option':'vacuum'}]


def test_modes_conflict_and_safe_default():
    assert m.resolve_mode(set())[0]=='vacuum'
    assert m.resolve_mode({'dobby_vacuum','dobby_mop'})[0] is None
    assert m.resolve_mode({'dobby_vacuum_mop'})[0]=='vac_and_mop'


@pytest.mark.parametrize('values',[[],[0],[-1],[True],[1.1],['hello'],['inf']])
def test_bad_segments(values):
    with pytest.raises(ValueError):m.validate_segments(values)


def test_segments_parse_deduplicate():
    assert m.validate_segments('29, 24,29')==[24,29]


def test_gesture_four_transitions_not_three():
    g=GestureDetector();assert not g.feed('s','off','on',10)
    assert not g.feed('s','on','off',10.3)
    assert not g.feed('s','off','on',10.7)
    assert g.feed('s','on','off',11.0)
    assert not g.feed('s','off','on',11.2)


def test_gesture_opposite_direction():
    g=GestureDetector()
    for i,(a,b) in enumerate([('on','off'),('off','on'),('on','off'),('off','on')]):
        assert g.feed('s',a,b,10+i*.3)==(i==3)


def test_gesture_no_combining_switches():
    g=GestureDetector()
    for i in range(4):
        assert not g.feed('a' if i<2 else 'b','off' if i%2==0 else 'on','on' if i%2==0 else 'off',10+i*.3)


def test_gesture_reject_automation_unavailable_and_slow():
    for special in ('automation','unavailable','slow'):
        g=GestureDetector()
        for i in range(4):
            old='off' if i%2==0 else 'on';new='on' if i%2==0 else 'off'
            if special=='unavailable' and i==1:old='unavailable'
            result=g.feed('s',old,new,10+i*(1.0 if special=='slow' else .3),automation=special=='automation')
            assert not result


def test_gesture_attribute_only_not_counted():
    g=GestureDetector()
    for i in range(10):assert not g.feed('s','on','on',10+i*.1)


def test_daily_timezone_and_reset_boundary():
    assert m.cleaning_day(LOCAL.replace(hour=0,minute=4),'00:05')=='2026-10-02'
    assert m.cleaning_day(LOCAL.replace(hour=0,minute=5),'00:05')=='2026-10-03'
    assert m.in_window(LOCAL.replace(hour=23),'22:00','06:00')
    assert not m.in_window(LOCAL,'22:00','06:00')


def test_mid_job_mop_wash_does_not_start_completion_timeout():
    e,c,r,t=setup();start(e,c,r,t)
    step(e,c,r,t,seconds=100,vacuum='docked',washing=True)
    step(e,c,r,t,seconds=c['proof_timeout']+100,washing=True)
    assert not e.fault and e.active and not e.active.get('proved')
    assert 'washing' in e.wait_reason.lower()


def test_abort_waits_for_existing_dock_service():
    e,c,r,t=setup();start(e,c,r,t)
    effects=step(e,c,r,t,home=True,vacuum='docked',washing=True)
    assert effects==[] and e.active['phase']=='aborting'
