"""Activity integration simulations using the existing lightweight HA fixtures."""
import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import pytest
from test_adapter import adapter


def setup(c,h):
    c.settings.update(vacuum_entity='vacuum.test',error_entity='sensor.test_vacuum_error',
        mode_entity='select.test_cleaning_mode',map_entity='select.test_selected_map',
        empty_entity='switch.test_dock_dust_emptying',wash_entity='switch.test_dock_mop_washing')
    h.states.add('vacuum.test','cleaning')
    h.states.add('sensor.test_vacuum_error','none')
    h.states.add('select.test_cleaning_mode','vacuum')
    h.states.add('select.test_selected_map','Ground')
    h.states.add('sensor.test_current_room','Kitchen')
    h.states.add('switch.test_dock_dust_emptying','off')
    h.states.add('switch.test_dock_mop_washing','off')
    c.maps=[{'flag':0,'name':'Ground','rooms':{'17':'Kitchen'}}]


def test_blank_sources_detect_current_vacuum_without_saving(adapter):
    m,c,h,calls=adapter; setup(c,h)
    assert c.reporting_sources()['current_room_entity']=='sensor.test_current_room'
    assert c.settings['current_room_entity']==''
    assert c.store.saved==[] and calls==[]


def test_explicit_unavailable_source_not_replaced_by_another_robot(adapter):
    m,c,h,calls=adapter;setup(c,h)
    c.settings['current_room_entity']='sensor.renamed_room'
    assert c.reporting_sources()['current_room_entity']=='sensor.renamed_room'
    c.update_activity()
    assert c.activity['confirmed_room'] is None


def test_find_controls_includes_new_optional_sources(adapter):
    m,c,h,calls=adapter;setup(c,h)
    h.states.add('sensor.test_status','segment_cleaning')
    h.states.add('sensor.test_dock_error','ok')
    h.states.add('binary_sensor.test_mop_drying','off')
    found=c.detect('vacuum.test')
    assert found['current_room_entity']=='sensor.test_current_room'
    assert found['status_entity']=='sensor.test_status'
    assert found['dock_error_entity']=='sensor.test_dock_error'
    assert found['drying_entity']=='binary_sensor.test_mop_drying'


@pytest.mark.parametrize('values',[
 {'room_confirm_seconds':0},{'room_confirm_seconds':601},
 {'current_room_entity':'light.room'},{'drying_entity':'switch.mop'},
 {'current_room_entity':'sensor.dobby_scheduler_room_stable'},
 {'status_entity':'sensor.dobby_scheduler_activity'}])
def test_invalid_reporting_settings_rejected(adapter,values):
    m,c,h,calls=adapter
    with pytest.raises(ValueError):c.validate_settings(values)


def test_valid_settings_retained_across_old_defaults(adapter):
    m,c,h,calls=adapter; setup(c,h)
    out=c.validate_settings({'room_confirm_seconds':90,'current_room_entity':'sensor.my_room'})
    assert out['room_confirm_seconds']==90 and out['current_room_entity']=='sensor.my_room'
    assert out['empty_after_room']==c.settings['empty_after_room']


def test_timer_publishes_confirmed_room_without_more_source_events(adapter,monkeypatch):
    m,c,h,calls=adapter;setup(c,h)
    clock=[0.]; monkeypatch.setattr(m.time,'monotonic',lambda:clock[0])
    notifications=[];c.add_listener(lambda:notifications.append(c.activity['text']))
    c.publish()
    clock[0]=59;c._timer(None)
    assert notifications[-1]=='Cleaning'
    clock[0]=60;c._timer(None)
    assert notifications[-1]=='Cleaning Kitchen'
    assert not calls and not c.engine.enabled


def test_state_event_immediately_exposes_brush_error_without_engine_tick(adapter,monkeypatch):
    m,c,h,calls=adapter;setup(c,h);c.update_activity()
    old=h.states.get('sensor.test_vacuum_error')
    new=h.states.add('sensor.test_vacuum_error','main_brush_jammed')
    c._state_changed(NS(data={'entity_id':new.entity_id,'old_state':old,'new_state':new}))
    assert c.activity['text']=='Main brush jammed'
    assert calls==[] and c.store.saved==[]


def test_auto_room_events_restart_countdown(adapter,monkeypatch):
    m,c,h,calls=adapter;setup(c,h)
    clock=[0.];monkeypatch.setattr(m.time,'monotonic',lambda:clock[0]);c.publish()
    clock[0]=59
    old=h.states.get('sensor.test_current_room');new=h.states.add('sensor.test_current_room','Hallway')
    c._state_changed(NS(data={'entity_id':new.entity_id,'old_state':old,'new_state':new}))
    clock[0]=61;c._timer(None)
    assert c.activity['confirmed_room'] is None
    clock[0]=119;c._timer(None)
    assert c.activity['confirmed_room']=='Hallway'


def test_reporting_never_calls_clean_or_locate_or_marks_job_done(adapter,monkeypatch):
    m,c,h,calls=adapter;setup(c,h)
    c.engine.jobs=[{'uid':'k','area_id':'kitchen','status':'needs_action'}]
    before=c.engine.export()
    clock=[0.];monkeypatch.setattr(m.time,'monotonic',lambda:clock[0]);c.update_activity()
    for moment in (60,70,90,120):
        clock[0]=moment;c.publish()
    assert c.engine.export()==before and calls==[] and c.store.saved==[]


def test_new_entities_are_text_sensors_with_no_units(adapter,monkeypatch):
    m,c,h,calls=adapter;setup(c,h)
    sensor_module=ModuleType('homeassistant.components.sensor')
    class SensorEntity:pass
    sensor_module.SensorEntity=SensorEntity
    monkeypatch.setitem(sys.modules,sensor_module.__name__,sensor_module)
    emodule=ModuleType('homeassistant.helpers.entity')
    class Entity:pass
    emodule.Entity=Entity
    monkeypatch.setitem(sys.modules,emodule.__name__,emodule)
    monkeypatch.setattr(sys.modules['homeassistant.helpers.device_registry'],'DeviceInfo',dict,raising=False)
    path=Path(__file__).parents[1]/'custom_components/dobby_scheduler/sensor.py'
    spec=importlib.util.spec_from_file_location('dobby_testpkg.sensor',path)
    mod=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,spec.name,mod);spec.loader.exec_module(mod)
    entities=[]
    asyncio.run(mod.async_setup_entry(h,NS(runtime_data=c),entities.extend))
    assert len(entities)==5
    activity_sensor=next(e for e in entities if e.key=='activity')
    room_sensor=next(e for e in entities if e.key=='room_stable')
    assert activity_sensor.entity_id=='sensor.dobby_scheduler_activity'
    assert room_sensor.entity_id=='sensor.dobby_scheduler_room_stable'
    assert activity_sensor.native_value=='Cleaning'
    assert activity_sensor.available is True
    assert activity_sensor.extra_state_attributes['scheduled_room'] is None
    assert not hasattr(activity_sensor,'_attr_native_unit_of_measurement')
    assert not hasattr(activity_sensor,'_attr_state_class')
    assert 'sensor.dobby_scheduler_status' in {e.entity_id for e in entities}
