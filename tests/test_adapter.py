"""HA-adapter contract simulations, NOT a real Home Assistant runtime test."""
from copy import deepcopy
from datetime import datetime, timezone
from enum import IntEnum
import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import pytest

ROOT=Path(__file__).parents[1]/'custom_components/dobby_scheduler'

class FakeStore:
    def __init__(self,*a): self.saved=[]; self.fail=False
    async def async_load(self): return None
    async def async_save(self,data):
        if self.fail: raise OSError('test storage failure')
        self.saved.append(deepcopy(data))

class Labels:
    def __init__(self): self.labels={}
    def async_get_label(self,k): return self.labels.get(k)
    def async_get_label_by_name(self,k): return next((x for x in self.labels.values() if x.name==k),None)
    def async_create(self,name,**kw): self.labels[name]=NS(label_id=name,name=name);return self.labels[name]

class Areas:
    def __init__(self): self.areas={}
    def async_get_area(self,k): return self.areas.get(k)
    def async_update(self,k,**kw):
        for n,v in kw.items():setattr(self.areas[k],n,v)
        return self.areas[k]

class Entities:
    def __init__(self):self.entities={}
    def async_get(self,k):return self.entities.get(k)
    def async_update_entity(self,k,**kw):
        for n,v in kw.items():setattr(self.entities[k],n,v)
        return self.entities[k]

class States:
    def __init__(self):self.states={}
    def get(self,e):return self.states.get(e)
    def add(self,e,s='off',**attrs):self.states[e]=NS(entity_id=e,state=s,attributes=attrs,domain=e.split('.')[0]);return self.states[e]
    def async_all(self,domain=None):return [s for s in self.states.values() if not domain or s.domain==domain]

@pytest.fixture
def adapter(monkeypatch):
    def mod(name,**attrs):
        m=ModuleType(name);m.__dict__.update(attrs);monkeypatch.setitem(sys.modules,name,m);return m
    mod('homeassistant');mod('homeassistant.helpers');mod('homeassistant.util')
    mod('homeassistant.core',Context=lambda: NS(id='ctx-own'),callback=lambda f:f)
    mod('homeassistant.exceptions',HomeAssistantError=RuntimeError)
    for reg in ['area_registry','entity_registry','device_registry','label_registry']:
        mod('homeassistant.helpers.'+reg,async_get=lambda hass,r=reg:hass.regs[r])
    mod('homeassistant.helpers.event',async_track_time_interval=lambda *a:lambda:None)
    mod('homeassistant.helpers.storage',Store=FakeStore)
    mod('homeassistant.util.dt',now=lambda:datetime(2026,10,3,10,0,tzinfo=timezone.utc))
    pkg=mod('dobby_testpkg');pkg.__path__=[str(ROOT)]
    for name in ['engine','controller']:
        spec=importlib.util.spec_from_file_location('dobby_testpkg.'+name,ROOT/(name+'.py'))
        m=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,spec.name,m);spec.loader.exec_module(m)
    hass=NS(data={},states=States(),regs={},config_entries=NS(async_get_entry=lambda x:None))
    hass.regs={'area_registry':Areas(),'entity_registry':Entities(),'label_registry':Labels(),'device_registry':NS(async_get=lambda x:None)}
    calls=[]
    async def call(*a,**kw):calls.append((a,kw));return {'vacuum.test':{'maps':[{'flag':0,'name':'Ground','rooms':{'17':'Kitchen','24':'Hall'}}]}}
    hass.services=NS(async_call=call)
    c=m.DobbyController(hass,NS(entry_id='test',title='Test Scheduler'));c.kick=lambda:None
    c.refresh_registry()
    return m,c,hass,calls


def run(c,a,d=None):return asyncio.run(c.command(a,d))

def prepare_room(c,h,area='kitchen'):
    h.regs['area_registry'].areas[area]=NS(id=area,name=area.title(),labels={'unrelated'})
    run(c,'create_labels');c.maps=[{'flag':0,'name':'Ground','rooms':{'17':'Kitchen','24':'Hall'}}];c.refresh_registry()
    data=dict(area_id=area,cleanable=True,daily=True,mode_label='dobby_vacuum_mop',priority=10,map_flag=0,segments=[17],verified=True)
    return data

@pytest.mark.parametrize('response',[
    {'maps':[{'flag':0,'name':'Ground','rooms':{'17':'Kitchen'}}]},
    {'vacuum.test':{'maps':[{'flag':0,'name':'Ground','rooms':{'17':'Kitchen'}}]}}
])
def test_get_maps_response_shapes(adapter,response):
    m,c,h,calls=adapter
    assert m.normalize_maps(response,'vacuum.test')==[{'flag':0,'name':'Ground','rooms':{'17':'Kitchen'}}]

@pytest.mark.parametrize('response',[None,[],{}, {'maps':'oops'},{'maps':[{},None,{'flag':'bad','rooms':{}}]}])
def test_invalid_maps_not_invented(adapter,response):
    m,c,h,calls=adapter
    assert m.normalize_maps(response,'vacuum.test')==[]


def test_create_labels_idempotent(adapter):
    m,c,h,calls=adapter;run(c,'create_labels');run(c,'create_labels')
    assert len(c.label_ids())==6


def test_room_save_preserves_unrelated_labels(adapter):
    m,c,h,calls=adapter;d=prepare_room(c,h);run(c,'save_room',d)
    assert h.regs['area_registry'].areas['kitchen'].labels=={'unrelated','dobby_cleanable','dobby_daily','dobby_vacuum_mop'}
    assert c.rooms['kitchen']['verified'] and c.rooms['kitchen']['mode']=='vac_and_mop'


def test_wrong_segment_rejected_without_changes(adapter):
    m,c,h,calls=adapter;d=prepare_room(c,h);d['segments']=[29]
    with pytest.raises(ValueError):run(c,'save_room',d)
    assert not c.room_config and h.regs['area_registry'].areas['kitchen'].labels=={'unrelated'}


def test_room_rename_and_renumber_revalidation(adapter):
    m,c,h,calls=adapter;run(c,'save_room',prepare_room(c,h))
    c.maps[0]['rooms']['17']='Different room';c.refresh_registry()
    assert 'names changed' in c.rooms['kitchen']['mapping_error']
    del c.maps[0]['rooms']['17'];c.refresh_registry()
    assert 'missing' in c.rooms['kitchen']['mapping_error']


def test_overlap_detected(adapter):
    m,c,h,calls=adapter;run(c,'save_room',prepare_room(c,h));run(c,'save_room',prepare_room(c,h,'hall'))
    assert 'also assigned' in c.rooms['hall']['mapping_error'] and 'also assigned' in c.rooms['kitchen']['mapping_error']


def test_entity_area_overrides_device(adapter):
    m,c,h,calls=adapter;prepare_room(c,h)
    reg=h.regs['entity_registry'];reg.entities['binary_sensor.wall']=NS(entity_id='binary_sensor.wall',labels={'keep'},area_id='kitchen',device_id='dev',disabled_by=None)
    h.regs['device_registry'].async_get=lambda k:NS(area_id='hall')
    run(c,'set_toggle',{'entity_id':'binary_sensor.wall','enabled':True})
    assert c.toggle_entities['binary_sensor.wall']=='kitchen'
    assert reg.entities['binary_sensor.wall'].labels=={'keep','dobby_room_toggle'}
    reg.entities['binary_sensor.wall'].area_id=None;c.refresh_registry();assert c.toggle_entities['binary_sensor.wall']=='hall'
    run(c,'set_toggle',{'entity_id':'binary_sensor.wall','enabled':False});assert reg.entities['binary_sensor.wall'].labels=={'keep'}

@pytest.mark.parametrize('bad',[{'away_minutes':-1},{'minimum_battery':101},{'window_start':'25:00'},
 {'empty_after_room':'yes'},{'unknown':5},{'vacuum_entity':'switch.any'},
 {'blocking_entities':['sensor.fake']},{'room_timeout':float('nan')},{'gesture_seconds':20}])
def test_bad_settings_rejected(adapter,bad):
    m,c,h,calls=adapter
    with pytest.raises(ValueError):c.validate_settings(bad)


def test_change_vacuum_invalidates_mappings_disables_scheduler(adapter):
    m,c,h,calls=adapter;run(c,'save_room',prepare_room(c,h));c.engine.enabled=True
    run(c,'settings',{'vacuum_entity':'vacuum.new'})
    assert not c.engine.enabled and not c.maps and not c.room_config['kitchen']['verified']


def test_success_adapter_must_have_record_field(adapter):
    m,c,h,calls=adapter;c._coordinator=lambda:NS(data=NS(clean_summary=NS(other='not a completion record')))
    assert c.clean_record()[1] is False
    c._coordinator=lambda:NS(data=NS(clean_summary=NS(last_clean_record=None)))
    assert c.clean_record()[1] is True


def test_timestamp_sensor_is_not_completion_proof(adapter):
    m,c,h,calls=adapter;c.settings['completion_entity']='sensor.last_end'
    h.states.add('sensor.last_end','2026-10-03T12:00:00')
    assert c.clean_record()[1] is False


def test_complete_record_external_supported(adapter):
    m,c,h,calls=adapter;c.settings['completion_entity']='sensor.job_record'
    h.states.add('sensor.job_record','ok',begin=10,end=20,complete=1,error=0,area=55,map_flag=0)
    record,supported,_=c.clean_record();assert supported and record['area']==55


def test_enum_record_normalized(adapter):
    m,c,h,calls=adapter
    class E(IntEnum):none=0
    assert m.normalize_record(NS(begin=1,end=2,complete=1,error=E.none,area=5,map_flag=0))['error']==0


def test_maps_action_read_only_service(adapter):
    m,c,h,calls=adapter;c.settings['vacuum_entity']='vacuum.test';h.states.add('vacuum.test','docked')
    result=run(c,'maps');assert result[0]['rooms']['17']=='Kitchen'
    assert calls[0][0]==('roborock','get_maps',{'entity_id':'vacuum.test'})
    assert calls[0][1]['return_response'] is True


def test_clean_command_public_service_only(adapter):
    m,c,h,calls=adapter;c.settings['vacuum_entity']='vacuum.test'
    asyncio.run(c.execute({'kind':'clean','segments':[17,24]}))
    assert calls[0][0][0:2]==('vacuum','send_command')
    assert calls[0][0][2]['params']==[{'segments':[17,24],'repeat':1}]


def test_store_no_rewrites_without_changes(adapter):
    m,c,h,calls=adapter;asyncio.run(c.persist());asyncio.run(c.persist())
    assert len(c.store.saved)==1


def test_only_recognised_legacy_disabled(adapter):
    m,c,h,calls=adapter
    h.states.add('automation.old','on',friendly_name='Dobby - Clean daily when noone is home')
    h.states.add('automation.unrelated','on',friendly_name='Other schedule')
    run(c,'disable_legacy')
    assert len(calls)==1 and calls[0][0][2]['entity_id']=='automation.old'


def test_default_priority_changes_do_not_reorder_today(adapter):
    m,c,h,calls=adapter;run(c,'save_room',prepare_room(c,h));d=prepare_room(c,h,'hall');d['segments']=[24];run(c,'save_room',d)
    run(c,'enqueue',{'area_id':'kitchen'});run(c,'enqueue',{'area_id':'hall'})
    run(c,'default_order',{'area_ids':['hall','kitchen']})
    assert c.rooms['hall']['priority']==10 and c.rooms['kitchen']['priority']==20
    assert [j['area_id'] for j in c.engine.jobs]==['kitchen','hall']


def test_tick_persists_before_command(adapter):
    m,c,h,calls=adapter;seen=[]
    c.telemetry=lambda:{'now':1};c.engine.tick=lambda *a:[{'kind':'dock'}]
    async def save():seen.append('save')
    async def execute(effect):seen.append('effect')
    c.persist=save;c.execute=execute
    asyncio.run(c.async_tick());assert seen==['save','effect']
