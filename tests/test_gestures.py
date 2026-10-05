"""Gesture and Locate regressions; simulated HA, no hardware commands."""
import asyncio
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from test_adapter import adapter, prepare_room, run

ROOT=Path(__file__).parents[1]/'custom_components/dobby_scheduler'
spec=importlib.util.spec_from_file_location('gesture_unit',ROOT/'gestures.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
spec=importlib.util.spec_from_file_location('gesture_engine',ROOT/'engine.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
NOW=1791154800.0

def ts(t):return datetime.fromtimestamp(t,timezone.utc).isoformat()

@pytest.mark.parametrize('label,expected',[
 ('dobby_room_toggle','dobby_room_toggle'),('dobby_room_double_toggle','dobby_room_double_toggle'),
 ('dobby_room_press','dobby_room_press'),('room_press','dobby_room_press')])
def test_labels(label,expected):assert g.resolve_gesture({label,'unrelated'})==(expected,'')

def test_alias_and_canonical_not_conflict():
 assert g.resolve_gesture({'room_press','dobby_room_press'})==('dobby_room_press','')

@pytest.mark.parametrize('other',['dobby_room_press','dobby_room_double_toggle','room_press'])
def test_conflict_no_shortest_wins(other):assert g.resolve_gesture({'dobby_room_toggle',other})[0] is None

@pytest.mark.parametrize('changes',[2,4])
@pytest.mark.parametrize('initial',['on','off'])
def test_full_switch_cycles(changes,initial):
 d=e.GestureDetector();state=initial
 for i in range(changes):
  new='on' if state=='off' else 'off'
  assert d.feed('switch.test',state,new,10+i*.3,transitions=changes)==(i==changes-1)
  state=new
 assert state==initial
 assert not d.feed('switch.test',state,'on' if state=='off' else 'off',12,transitions=changes)

def test_length_change_clears_inflight_sequence():
 d=e.GestureDetector();assert not d.feed('x','off','on',10,transitions=4)
 assert not d.feed('x','on','off',10.3,transitions=2)
 assert d.feed('x','off','on',10.6,transitions=2)

def test_slow_single_cycle_does_not_count():
 d=e.GestureDetector();assert not d.feed('x','off','on',10,transitions=2)
 assert not d.feed('x','on','off',12.1,transitions=2)

def press(entity='event.remote',old=None,new=None,kind='single',**kw):
 d=g.PressDetector()
 return d.feed(entity,ts(NOW-30) if old is None else old,ts(NOW) if new is None else new,
  {'event_type':kind},10,NOW,NOW-10,**kw)

@pytest.mark.parametrize('kind',['single','single_press','press','press_end','ring','single_short_release'])
def test_supported_event_short_press(kind):assert press(kind=kind)
@pytest.mark.parametrize('kind',['long_press','double','hold','release','repeat','unknown_vendor'])
def test_other_event_types_not_single(kind):assert not press(kind=kind)

def test_explicit_vendor_type():assert press(kind='initial_press',event_type='initial_press')
def test_explicit_type_rejects_others():assert not press(kind='single',event_type='initial_press')
@pytest.mark.parametrize('domain',['button','input_button'])
def test_fresh_button_timestamp(domain):assert press(entity=domain+'.test',old='unknown')
def test_missing_initial_state_not_press():
 assert not g.PressDetector().feed('input_button.test',None,ts(NOW),{},10,NOW,NOW-10)
@pytest.mark.parametrize('new',[ts(NOW-50),ts(NOW+100),'garbage','unknown','unavailable'])
def test_stale_restored_bad_timestamps(new):assert not press(new=new)
def test_event_recovery_not_press():assert not press(old='unavailable')
def test_event_attributes_only_not_press():assert not press(old=ts(NOW),new=ts(NOW))
def test_momentary_rising_edge_and_release():
 d=g.PressDetector()
 assert d.feed('binary_sensor.button','off','on',{},10,NOW,NOW-10)
 assert not d.feed('binary_sensor.button','on','off',{},16,NOW+6,NOW-10)
 assert not d.feed('binary_sensor.button','unknown','on',{},17,NOW+7,NOW-10)
def test_event_cooldown():
 d=g.PressDetector()
 assert d.feed('event.button',ts(NOW-20),ts(NOW),{'event_type':'single'},10,NOW,NOW-10)
 assert not d.feed('event.button',ts(NOW),ts(NOW+1),{'event_type':'single'},11,NOW+1,NOW-10)
def test_automation_filter_and_intentional_bridge():
 assert not press(entity='button.test',automation=True)
 assert not press(automation=True)
 assert press(entity='input_button.test',automation=True)

def configured(adapter,label='dobby_room_press',entity='binary_sensor.wall'):
 m,c,h,calls=adapter;run(c,'save_room',prepare_room(c,h))
 h.regs['entity_registry'].entities[entity]=NS(entity_id=entity,labels={'unrelated'},area_id='kitchen',device_id=None,disabled_by=None)
 run(c,'set_gesture',{'entity_id':entity,'enabled':True,'label':label})
 c.settings['vacuum_entity']='vacuum.test';c.started_at=NOW-10
 return m,c,h,calls

@pytest.mark.parametrize('mode,changes', [('dobby_room_press',1),('dobby_room_toggle',2),('dobby_room_double_toggle',4)])
def test_state_dispatch_queues_and_locates_once(adapter,monkeypatch,mode,changes):
 m,c,h,calls=configured(adapter,mode);clock=[NOW]
 monkeypatch.setattr(m,'time',NS(time=lambda:clock[0],monotonic=lambda:clock[0]))
 async def scenario():
  tasks=[]
  def create(coro):
   task=asyncio.create_task(coro);tasks.append(task);return task
  h.async_create_task=create
  state='off'
  for i in range(changes):
   clock[0]=NOW+i*.3;new='on' if state=='off' else 'off'
   c._state_changed(NS(data={'entity_id':'binary_sensor.wall','old_state':NS(state=state),'new_state':NS(state=new,attributes={},context=NS(id='physical',parent_id=None))}))
   state=new
  await asyncio.gather(*tasks)
 asyncio.run(scenario())
 assert len(c.engine.jobs)==1 and c.engine.jobs[0]['urgent']
 assert c.engine.jobs[0]['source']==mode
 assert len(calls)==1 and calls[0][0]==('vacuum','locate',{'entity_id':'vacuum.test'})
 assert not c.engine.enabled and not c.engine.active

@pytest.mark.parametrize('domain',['input_button','button','event'])
def test_button_dispatch_first_fresh_press(adapter,monkeypatch,domain):
 entity=domain+'.remote';m,c,h,calls=configured(adapter,entity=entity)
 monkeypatch.setattr(m,'time',NS(time=lambda:NOW,monotonic=lambda:10))
 async def scenario():
  tasks=[];h.async_create_task=lambda coro:tasks.append(asyncio.create_task(coro))
  c._state_changed(NS(data={'entity_id':entity,'old_state':NS(state='unknown'),'new_state':NS(state=ts(NOW),attributes={'event_type':'single'},context=NS(id='physical',parent_id='bridge' if domain=='input_button' else None))}))
  await asyncio.gather(*tasks)
 asyncio.run(scenario())
 assert len(c.engine.jobs)==1 and len(calls)==1

def test_changing_label_keeps_other_labels(adapter):
 m,c,h,calls=configured(adapter,'dobby_room_double_toggle')
 run(c,'set_gesture',{'entity_id':'binary_sensor.wall','enabled':True,'label':'dobby_room_toggle'})
 assert h.regs['entity_registry'].entities['binary_sensor.wall'].labels=={'unrelated','dobby_room_toggle'}

def test_conflict_exposed_not_watched(adapter):
 m,c,h,calls=configured(adapter)
 h.regs['entity_registry'].entities['binary_sensor.wall'].labels.add('dobby_room_toggle');c.refresh_registry()
 assert 'binary_sensor.wall' not in c.gesture_entities and c.gesture_issues

def test_registry_room_change_clears_half_cycle(adapter):
 m,c,h,calls=configured(adapter,'dobby_room_toggle')
 c.gestures.feed('binary_sensor.wall','off','on',10,transitions=2)
 h.regs['entity_registry'].entities['binary_sensor.wall'].area_id='other';c.refresh_registry()
 assert 'binary_sensor.wall' not in c.gestures.windows

def test_event_type_settings_persist(adapter):
 m,c,h,calls=configured(adapter,entity='event.remote')
 run(c,'set_gesture',{'entity_id':'event.remote','enabled':True,'label':'dobby_room_press','event_type':'initial_press'})
 assert c.store.saved[-1]['gesture_options']['event.remote']['event_type']=='initial_press'

def test_new_press_promotes_pending_without_duplicate(adapter):
 m,c,h,calls=configured(adapter)
 asyncio.run(c._gesture('binary_sensor.wall'));uid=c.engine.jobs[0]['uid']
 asyncio.run(c._gesture('binary_sensor.wall'))
 assert len(c.engine.jobs)==1 and c.engine.jobs[0]['uid']==uid and len(calls)==2

def test_active_room_not_requeued_or_acknowledged(adapter):
 m,c,h,calls=configured(adapter);uid=c.engine.enqueue('kitchen',c.rooms,NOW)
 c.engine.active={'uid':uid};asyncio.run(c._gesture('binary_sensor.wall'))
 assert len(c.engine.jobs)==1 and not calls

def test_missing_area_no_false_acknowledgement(adapter):
 m,c,h,calls=configured(adapter);c.gesture_entities['binary_sensor.wall']['area_id']=None
 asyncio.run(c._gesture('binary_sensor.wall'));assert not calls and not c.engine.jobs

def test_no_ack_before_successful_save(adapter):
 m,c,h,calls=configured(adapter);c.store.fail=True
 with pytest.raises(OSError):asyncio.run(c._gesture('binary_sensor.wall'))
 assert not calls

def test_ack_error_does_not_lose_job(adapter):
 m,c,h,calls=configured(adapter)
 async def bad(*a,**kw):raise TimeoutError('no response')
 c.call=bad;asyncio.run(c._gesture('binary_sensor.wall'))
 assert len(c.engine.jobs)==1 and 'Locate acknowledgement failed' in c.engine.log[-1]['message']

def test_explicit_ack_optout_is_preserved(adapter):
 m,c,h,calls=configured(adapter);c.settings['acknowledge']=False
 asyncio.run(c._gesture('binary_sensor.wall'));assert c.engine.jobs and not calls

def test_relabel_between_detection_and_task_ignored(adapter):
 m,c,h,calls=configured(adapter);captured=dict(c.gesture_entities['binary_sensor.wall'])
 c.gesture_entities['binary_sensor.wall']['area_id']='hall'
 asyncio.run(c._gesture('binary_sensor.wall',captured));assert not calls and not c.engine.jobs
