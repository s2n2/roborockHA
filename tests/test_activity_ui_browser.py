"""Browser activity/settings regressions using a mocked Home Assistant backend."""
import json
import shutil
from playwright.sync_api import sync_playwright
from test_frontend import MOCK, HTML, ROOT


def run():
    checks=[]; errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        page=browser.new_page(viewport={'width':1100,'height':1000})
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.set_content(HTML);page.add_script_tag(content=MOCK)
        page.evaluate("""demo.activity={text:'Vac + mop \u00b7 Kitchen',code:'vacuuming_and_mopping',icon:'mdi:robot-vacuum',room:'Kitchen',room_is_current:true};
            demo.entities.activity='sensor.dobby_scheduler_activity';
            demo.entities.room_stable='sensor.dobby_scheduler_room_stable';
            demo.candidates.push({entity_id:'sensor.test_current_room',name:'Robot room',state:'Kitchen',options:[]});
            window.moreInfoEntity=null;document.addEventListener('hass-more-info',event=>window.moreInfoEntity=event.detail.entityId);""")
        page.add_script_tag(path=str(ROOT/'custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'))
        page.wait_for_function("!!customElements.get('dobby-scheduler-card')")
        page.evaluate("const c=document.querySelector('dobby-scheduler-card');c.setConfig({type:'custom:dobby-scheduler-card'});c.hass=fakeHass;")
        page.wait_for_selector('.activity-summary')
        assert 'Vac + mop \u00b7 Kitchen' in page.locator('.activity-summary').inner_text();checks.append('readable activity displayed')
        assert 'Scheduler disabled' in page.locator('.status').inner_text();checks.append('physical activity separate from disabled scheduler')
        page.locator('.activity-summary').click()
        assert page.evaluate('moreInfoEntity')=='sensor.dobby_scheduler_activity';checks.append('activity opens reusable sensor more-info')
        page.locator('[data-action=setup]').first.click();page.locator('[data-action=tab][data-id=settings]').click()
        assert page.locator('[data-cfg=room_confirm_seconds]').input_value()=='60';checks.append('default full-minute confirmation')
        for field in ['current_room_entity','status_entity','dock_error_entity','drying_entity']:
            assert page.locator('[data-cfg='+field+']').count()==1;checks.append(field+' configurable in UI')
        page.locator('[data-cfg=current_room_entity]').fill('sensor.test_current_room')
        page.locator('[data-cfg=room_confirm_seconds]').fill('90');page.locator('[data-action=save-settings]').click()
        assert page.evaluate('commands.at(-1).data.room_confirm_seconds')==90;checks.append('confirmation setting saved')
        assert page.evaluate('commands.at(-1).data.current_room_entity')=='sensor.test_current_room';checks.append('room source setting saved')
        page.locator('[data-action=tab][data-id=help]').click()
        assert 'not backdated' in page.locator('dialog').inner_text();checks.append('filtered-history limit explained in app')
        page.locator('[data-action=tab][data-id=diagnostics]').click()
        assert 'Vac + mop \u00b7 Kitchen' in page.locator('dialog').inner_text();checks.append('diagnostics include activity data')
        page.locator('[data-action=close]').click()
        for state in ['Main brush jammed','Returning','Emptying','Mopping \u00b7 Bathroom','Vacuuming \u00b7 Hallway','Vac + mop \u2192 Kitchen']:
            page.evaluate("v=>{demo.activity.text=v;return document.querySelector('dobby-scheduler-card').refresh()}",state)
            assert state in page.locator('.activity-summary').inner_text();checks.append('renders '+state)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');checks.append('activity card fits 390px viewport')
        page.locator('dobby-scheduler-card').screenshot(path=str(ROOT/'docs/previews/activity-0.1.8-mobile.png'))
        page.locator('[data-action=setup]').first.click();page.locator('[data-action=tab][data-id=settings]').click()
        page.locator('[data-cfg=room_confirm_seconds]').scroll_into_view_if_needed()
        assert page.locator('dialog').evaluate('(d)=>d.scrollWidth<=d.clientWidth+1');checks.append('activity settings fit mobile popup')
        page.locator('dialog').screenshot(path=str(ROOT/'docs/previews/activity-0.1.8-settings.png'))
        page.locator('[data-action=close]').click()
        page.evaluate("demo.activity.text='<img src=x onerror=alert(1)>';document.querySelector('dobby-scheduler-card').refresh();")
        page.wait_for_timeout(100)
        assert page.locator('.activity-summary img').count()==0;checks.append('activity text escaped')
        assert page.evaluate("commands.every(c=>c.action==='settings')");checks.append('no robot or queue commands from activity display')
        assert not errors,errors;checks.append('no browser JavaScript exceptions')
        browser.close()
    result={'checks_passed':len(checks),'checks':checks,'browser_errors':errors,'scope':'Headless Chromium with mocked HA data, not a live robot or HA install'}
    (ROOT/'docs/activity-ui-0.1.8-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__': run()
