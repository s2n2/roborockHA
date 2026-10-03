"""Chromium UI smoke tests with a simulated hass.callWS backend, not real HA."""
import importlib.util
import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('ui_engine',ROOT/'custom_components/dobby_scheduler/engine.py')
e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
SETTINGS=dict(e.DEFAULTS, vacuum_entity='vacuum.test', presence_entity='binary_sensor.someone_home',
 mode_entity='select.test_cleaning_mode', battery_entity='sensor.test_battery', error_entity='sensor.test_vacuum_error',
 map_entity='select.test_selected_map', empty_entity='switch.test_dock_dust_emptying', wash_entity='switch.test_dock_mop_washing')
LABELS={k:k for k in ('dobby_cleanable','dobby_daily','dobby_vacuum','dobby_vacuum_mop','dobby_mop','dobby_room_toggle')}
ROOMS=[]
for area,name,segment,mode,priority in [('kitchen','Kitchen',17,'vac_and_mop',10),('hallway_tiles','Hallway tiles',24,'vac_and_mop',20),('bathroom','Bathroom',19,'vac_and_mop',30),('lounge','Lounge',16,'vacuum',50),('bedroom','Bedroom',26,'vacuum',60)]:
 ROOMS.append(dict(area_id=area,name=name,cleanable=True,daily=True,mode=mode,mode_label='dobby_vacuum_mop' if mode=='vac_and_mop' else 'dobby_vacuum',mode_warning='',priority=priority,segments=[segment],map_flag=0,map_name='Main map',verified=True,mapping_error=''))
JOBS=[dict(uid=r['area_id'],area_id=r['area_id'],name=r['name'],mode=r['mode'],segments=r['segments'],map_name='Main map',status='needs_action',source='daily',note='',reason='',urgent=False) for r in ROOMS[:3]]
DATA=dict(version='0.1.3',entry_id='demo',name='Dobby Scheduler',enabled=False,manual=False,active=None,reason='Scheduler disabled',fault='',day='2026-10-03',jobs=JOBS,rooms=ROOMS,maps=[dict(flag=0,name='Main map',rooms={str(r['segments'][0]):r['name'] for r in ROOMS})],maps_at=1790988000,telemetry=dict(home=True,battery=84,vacuum='docked',map_name='Main map',record_supported=True,legacy=[]),backend='Simulated successful-clean record adapter',labels=LABELS,toggle_entities={'binary_sensor.kitchen_wall_input':'kitchen'},entities={'queue':'todo.dobby_scheduler_queue'},log=[dict(at=1790988000,message='Daily rooms restored')],settings=SETTINGS,candidates=[dict(entity_id='vacuum.test',name='Robot',state='docked',options=[]),dict(entity_id='binary_sensor.kitchen_wall_input',name='Kitchen wall input',state='off',options=[])])
MOCK=r"""
window.commands=[];window.demo=DATA;window.failNext=false;
customElements.define('home-assistant',class extends HTMLElement{});
customElements.define('ha-card',class extends HTMLElement{});
customElements.define('ha-icon',class extends HTMLElement{
 connectedCallback(){const key=this.getAttribute('icon')||'';this.textContent=key.includes('chevron-up')?'\u2303':key.includes('chevron-down')?'\u2304':key.includes('close')?'\u00d7':key.includes('dots')?'\u22ef':key.includes('cog')?'\u2699':key.includes('priority')?'!':key.includes('play')?'\u25b6':key.includes('robot')?'\u25c9':key.includes('tune')?'\u2637':'\u2302';this.style.cssText='display:inline-block;width:20px;text-align:center;font-size:20px;line-height:20px;vertical-align:middle;';}
});
window.fakeHass={user:{is_admin:true},callWS:async msg=>{
 if(msg.type==='dobby_scheduler/get'){const result=structuredClone(demo);if(!msg.include_config){delete result.settings;delete result.candidates;}return result;}
 commands.push(structuredClone(msg));if(failNext){failNext=false;throw new Error('Simulated mapping check: choose a valid fetched room number');}
 const p=msg.data||{};
 if(msg.action==='enqueue'){let j=demo.jobs.find(j=>j.area_id===p.area_id);if(!j){const r=demo.rooms.find(r=>r.area_id===p.area_id);j={...r,uid:r.area_id,status:'needs_action',source:'dashboard',note:'',reason:''};demo.jobs.push(j);}j.status='needs_action';j.urgent=!!p.urgent;if(p.urgent){demo.jobs=demo.jobs.filter(x=>x!==j);demo.jobs.unshift(j);}}
 if(msg.action==='remove')demo.jobs=demo.jobs.filter(j=>j.uid!==p.uid);
 if(msg.action==='enable')demo.enabled=p.enabled;
 if(msg.action==='settings')Object.assign(demo.settings,p);
 if(msg.action==='move'){const j=demo.jobs.find(j=>j.uid===p.uid);demo.jobs=demo.jobs.filter(j=>j.uid!==p.uid);demo.jobs.splice(p.previous_uid==null?0:demo.jobs.findIndex(j=>j.uid===p.previous_uid)+1,0,j);}
 if(msg.action==='save_room'){const r=demo.rooms.find(r=>r.area_id===p.area_id);Object.assign(r,p);}
 if(msg.action==='set_toggle'){if(p.enabled)demo.toggle_entities[p.entity_id]='kitchen';else delete demo.toggle_entities[p.entity_id];}
 if(msg.action==='create_labels')demo.labels=LABELS;
 return {ok:true};
}};
""".replace('DATA',json.dumps(DATA),1).replace('LABELS',json.dumps(LABELS))
HTML='''<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#edf3f4;font-family:Arial,sans-serif;color:#17383c}main{max-width:640px;margin:24px auto;padding:0 10px}.preview{font-size:11px;letter-spacing:1px;color:#637f86;margin:0 0 12px;text-align:center}ha-card{display:block}@media(max-width:600px){main{margin:12px auto;}}</style></head><body><main><div class="preview">SIMULATED PREVIEW · DOBBY SCHEDULER 0.1.3</div><dobby-scheduler-card></dobby-scheduler-card></main></body></html>'''

def run_ui_tests():
 checks=[];errors=[];out=ROOT/'docs'/'previews';out.mkdir(parents=True,exist_ok=True)
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True, executable_path=shutil.which("chromium"))
  page=browser.new_page(viewport={'width':1100,'height':1060},device_scale_factor=1)
  page.on('pageerror',lambda err:errors.append(str(err)))
  page.on('dialog',lambda dialog:dialog.accept())
  page.set_content(HTML);page.add_script_tag(content=MOCK);page.add_script_tag(path=str(ROOT/'custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'))
  page.wait_for_function("!!customElements.get('dobby-scheduler-card')")
  page.evaluate("const c=document.querySelector('dobby-scheduler-card');c.setConfig({type:'custom:dobby-scheduler-card',title:'Dobby'});c.hass=fakeHass;")
  page.wait_for_selector('dobby-scheduler-card .roomchip')
  assert page.locator('.roomchip').count()==5;checks.append('dynamic room picker')
  assert page.locator('.summary strong').first.inner_text()=='Kitchen';checks.append('next room shown')
  page.locator('[data-action="toggle-room"][data-id="lounge"]').click();assert page.locator('.job').count()==4;checks.append('add room')
  page.locator('[data-action="promote"][data-id="lounge"]').click();assert page.locator('.job .text strong').first.inner_text()=='Lounge';checks.append('promote room')
  page.locator('[data-action="down"][data-id="lounge"]').click();assert page.locator('.job .text strong').first.inner_text()=='Kitchen';checks.append('queue reorder')
  page.screenshot(path=str(out/'card-desktop.png'),full_page=True)
  page.locator('[data-action="setup"]').first.click();assert page.locator('dialog').is_visible();checks.append('setup popup')
  page.locator('[data-action="area"][data-id="kitchen"]').click()
  assert page.locator('[data-room="segments"] option').count()==5;checks.append('fetched segment choices')
  page.locator('[data-room="segments"]').select_option(['17']);assert not page.locator('[data-room="verified"]').is_checked();checks.append('mapping edit clears confirmation')
  page.locator('[data-room="verified"]').check();page.locator('[data-room="priority"]').fill('5');page.locator('[data-action="save-room"]').click()
  assert page.evaluate("commands.at(-1).data.priority")==5;checks.append('save room metadata')
  page.locator('[data-action="popup-queue"]').click();assert page.evaluate("demo.jobs.some(j=>j.area_id==='kitchen')")==False;checks.append('popup room selection')
  page.locator('[data-action="popup-next"]').click();assert page.evaluate("demo.jobs[0].area_id")=='kitchen';checks.append('popup priority request')
  page.evaluate('failNext=true');page.locator('[data-action="save-room"]').click()
  assert page.locator('dialog .toast').is_visible();checks.append('popup errors visible in modal')
  page.evaluate("document.querySelector('dobby-scheduler-card').shadowRoot.getElementById('toast')?.remove()")
  page.screenshot(path=str(out/'setup-desktop.png'),full_page=True)
  page.locator('[data-action="tab"][data-id="settings"]').click()
  page.locator('[data-cfg="away_minutes"]').fill('12');page.locator('[data-cfg="window_start"]').click();page.wait_for_timeout(5300)
  assert page.locator('[data-cfg="away_minutes"]').input_value()=='12';checks.append('draft survives status refresh')
  page.locator('[data-action="save-settings"]').click();assert page.evaluate('demo.settings.away_minutes')==12;checks.append('settings persist command')
  page.locator('[data-action="tab"][data-id="switches"]').click();page.locator('#toggle-choice').fill('binary_sensor.kitchen_wall_input');page.locator('[data-action="add-toggle"]').click()
  assert page.evaluate("commands.at(-1).action")=='set_toggle';checks.append('label-only switch setup')
  page.locator('[data-action="tab"][data-id="help"]').click();assert 'dobby_vacuum_mop' in page.locator('dialog').inner_text();checks.append('built-in label instructions')
  page.locator('[data-action="tab"][data-id="diagnostics"]').click();assert 'Simulated successful-clean' in page.locator('dialog').inner_text();checks.append('completion diagnostics')
  page.locator('[data-action="close"]').click();page.set_viewport_size({'width':390,'height':844})
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth');checks.append('mobile document no horizontal overflow')
  page.screenshot(path=str(out/'card-mobile.png'),full_page=True)
  page.locator('[data-action="setup"]').first.click();page.locator('[data-action="tab"][data-id="rooms"]').click()
  assert page.locator('dialog').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1');checks.append('mobile popup no horizontal overflow')
  page.screenshot(path=str(out/'setup-mobile.png'),full_page=True)
  page.locator('[data-action="close"]').click()
  page.evaluate("demo.rooms[0].name='<img src=x onerror=alert(1)>';document.querySelector('dobby-scheduler-card').refresh();")
  page.wait_for_timeout(100)
  assert page.locator('dobby-scheduler-card img').count()==0;checks.append('dynamic room name escaped')
  assert not errors,errors;checks.append('no browser JavaScript exceptions')
  browser.close()
 result={'checks_passed':len(checks),'checks':checks,'browser_errors':errors,'environment':'Headless Chromium with mocked Home Assistant backend; not an installed HA dashboard'}
 (ROOT/'docs'/'frontend_test_results.json').write_text(json.dumps(result,indent=2))
 print(json.dumps(result,indent=2))

if __name__=='__main__':run_ui_tests()
