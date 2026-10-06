"""Immediate-request card tests using a simulated HA WebSocket backend."""
import json
import shutil
from playwright.sync_api import sync_playwright
from test_frontend import MOCK, HTML, ROOT


def run():
    checks=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        page=browser.new_page(viewport={'width':1100,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(HTML);page.add_script_tag(content=MOCK)
        page.add_script_tag(path=str(ROOT/'custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'))
        page.wait_for_function("!!customElements.get('dobby-scheduler-card')")
        page.evaluate("const c=document.querySelector('dobby-scheduler-card');c.setConfig({type:'custom:dobby-scheduler-card',title:'Dobby'});c.hass=fakeHass;")
        page.wait_for_selector('.roomchip')
        assert not page.locator('.immediate-requests').count();checks.append('no immediate banner for ordinary daily queue')
        page.locator('[data-action=setup]').first.click();page.locator('[data-action=tab][data-id=settings]').click()
        option=page.locator('[data-cfg=gesture_start_immediately]')
        assert option.is_checked();checks.append('immediate gesture start enabled by default')
        assert 'those rooms only' in page.locator('.immediate-help').inner_text();checks.append('per-room permission explained')
        assert 'the cleaning time window' in page.locator('.immediate-help').inner_text();checks.append('automatic-window bypass explicit')
        option.uncheck();page.locator('[data-action=save-settings]').click()
        assert page.evaluate('commands.at(-1).data.gesture_start_immediately') is False;checks.append('queue-only option can be saved')
        option.check();page.locator('[data-action=save-settings]').click()
        assert page.evaluate('commands.at(-1).data.gesture_start_immediately') is True;checks.append('immediate option can be restored')
        page.locator('[data-action=tab][data-id=switches]').click()
        assert 'Only requested rooms get this permission' in page.locator('dialog').inner_text();checks.append('gesture pane explains batch permissions')
        page.locator('[data-action=close]').click()
        page.evaluate("""async()=>{demo.jobs[0].immediate_request=true;demo.jobs[0].urgent=true;
          demo.jobs[1].immediate_request=true;demo.jobs[1].urgent=true;
          demo.immediate_rooms=['Kitchen','Hallway tiles'];demo.enabled=false;demo.manual=false;
          demo.reason='Setting cleaning mode';demo.gesture_start_immediately=true;
          await document.querySelector('dobby-scheduler-card').refresh();}""")
        assert page.locator('.immediate-requests:visible').count()==1;checks.append('batch banner appears even with automatic scheduling off')
        text=page.locator('.immediate-requests').inner_text()
        assert 'Kitchen, Hallway tiles' in text and 'one after another' in text;checks.append('all pending immediate rooms displayed')
        assert 'normal daily rooms still follow' in text;checks.append('normal daily queue stays distinct')
        assert page.locator('.job').filter(has_text='switch request - run now').count()==2;checks.append('two rows visibly carry immediate permission')
        page.locator('[data-action=job]').first.click()
        assert 'can run while home' in page.locator('dialog').inner_text();checks.append('job details show scoped permission')
        page.locator('[data-action=close]').click()
        page.set_viewport_size({'width':390,'height':1050})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');checks.append('mobile page does not overflow')
        page.locator('dobby-scheduler-card').screenshot(path=str(ROOT/'docs/previews/immediate-requests-0.1.8-mobile.png'))
        page.evaluate("""async()=>{demo.jobs[0].name='<img src=x onerror=alert(1)>';await document.querySelector('dobby-scheduler-card').refresh();}""")
        assert page.locator('.immediate-requests img').count()==0;checks.append('request names HTML-escaped')
        page.evaluate("""async()=>{demo.jobs.forEach(j=>j.immediate_request=false);demo.immediate_rooms=[];demo.reason='Waiting for everyone to leave';await document.querySelector('dobby-scheduler-card').refresh();}""")
        assert not page.locator('.immediate-requests').count();checks.append('batch banner removed when permission ends')
        assert page.locator('.job').filter(has_text='priority (queue only)').count()==2;checks.append('ordinary priority is not mislabelled run-now')
        page.locator('[data-action=setup]').first.click();page.locator('[data-action=tab][data-id=settings]').click()
        assert page.locator('dialog').evaluate('(x)=>x.scrollWidth<=x.clientWidth+1');checks.append('mobile settings do not overflow')
        assert not errors,errors;checks.append('no JavaScript errors')
        browser.close()
    result={'checks_passed':len(checks),'checks':checks,'browser_errors':errors,
            'scope':'Headless Chromium with mocked Home Assistant backend; no live robot'}
    (ROOT/'docs/immediate-ui-0.1.8-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':run()
