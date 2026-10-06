"""Gesture settings frontend tests with simulated HA, not physical input events."""
import json, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from test_frontend import MOCK, HTML, ROOT


def run():
 checks=[];errors=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
  page=browser.new_page(viewport={'width':1100,'height':1000})
  page.on('pageerror',lambda error:errors.append(str(error)))
  page.set_content(HTML);page.add_script_tag(content=MOCK)
  page.evaluate("demo.candidates.push({entity_id:'event.kitchen_button',name:'Kitchen button',state:'2026-10-05T10:00:00+00:00',event_types:['single','double','hold'],event_type:'single'},{entity_id:'input_button.kitchen_request',name:'Kitchen request',state:'unknown'});demo.gesture_entities={};demo.gesture_issues=[];")
  page.add_script_tag(path=str(ROOT/'custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'))
  page.wait_for_function("!!customElements.get('dobby-scheduler-card')")
  page.evaluate("const c=document.querySelector('dobby-scheduler-card');c.setConfig({type:'custom:dobby-scheduler-card'});c.hass=fakeHass;")
  page.locator('[data-action=setup]').first.click();page.locator('[data-id=switches][data-action=tab]').click()
  assert page.locator('#gesture-label option').count()==3;checks.append('three gesture choices')
  assert 'now means one cycle' in page.locator('dialog').inner_text();checks.append('old label semantic change disclosed')
  page.locator('#gesture-label').select_option('dobby_room_toggle');page.locator('#toggle-choice').fill('binary_sensor.kitchen_wall_input');page.locator('[data-action=add-toggle]').click()
  assert page.evaluate('commands.at(-1).data.label')=='dobby_room_toggle';checks.append('one cycle saved')
  page.locator('#gesture-label').select_option('dobby_room_double_toggle');page.locator('[data-action=add-toggle]').click()
  assert page.evaluate('commands.at(-1).data.label')=='dobby_room_double_toggle';checks.append('two cycles saved without lost click')
  page.locator('#gesture-label').select_option('dobby_room_press');assert page.locator('#press-event-type').is_visible();checks.append('single press event options visible')
  assert page.locator('#toggle-list option[value="event.kitchen_button"]').count()==1;checks.append('event entities selectable')
  assert page.locator('#toggle-list option[value="input_button.kitchen_request"]').count()==1;checks.append('input button bridge selectable')
  page.locator('#toggle-choice').fill('event.kitchen_button');page.locator('#press-event-type').click()
  assert page.locator('#press-event-types option').count()==3;checks.append('event types from selected entity')
  page.locator('#press-event-type').fill('single');page.locator('[data-action=add-toggle]').click()
  assert page.evaluate('commands.at(-1).data.event_type')=='single';checks.append('exact event filter saved')
  assert page.evaluate('commands.at(-1).data.entity_id')=='event.kitchen_button';checks.append('new button saved without YAML')
  page.locator('[data-action=edit-gesture][data-id="event.kitchen_button"]').click()
  assert page.locator('#gesture-label').input_value()=='dobby_room_press';checks.append('edit restores gesture type')
  assert page.locator('#press-event-type').input_value()=='single';checks.append('edit restores event filter')
  page.locator('#press-event-type').fill('initial_press');page.wait_for_timeout(5300)
  assert page.locator('#press-event-type').input_value()=='initial_press';checks.append('unsaved input survives live refresh')
  page.locator('[data-action=locate]').click();assert page.evaluate('commands.at(-1).action')=='locate';checks.append('test locate uses backend action')
  page.locator('[data-action=remove-toggle][data-id="event.kitchen_button"]').click()
  assert page.evaluate("demo.gesture_entities['event.kitchen_button']") is None;checks.append('gesture removal')
  for width in [390,1100]:
   page.set_viewport_size({'width':width,'height':1000})
   assert page.locator('dialog').evaluate('(x)=>x.scrollWidth<=x.clientWidth+1');checks.append(f'gesture pane fits {width}px viewport')
   page.locator('.pane').evaluate('(x)=>x.scrollTop=0')
   page.locator('dialog').screenshot(path=str(ROOT/f'docs/previews/gestures-0.1.5-{width}.png'))
  page.locator('[data-action=tab][data-id=help]').click()
  assert 'dobby_room_double_toggle' in page.locator('dialog').inner_text();checks.append('in-app instructions updated')
  assert 'room_press' in page.locator('dialog').inner_text();checks.append('press alias documented')
  assert not errors,errors;checks.append('no JavaScript exceptions')
  browser.close()
 result={'checks_passed':len(checks),'checks':checks,'browser_errors':errors,'scope':'Headless Chromium with simulated HA API; no hardware access'}
 (ROOT/'docs/gesture-ui-0.1.5-results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':run()
