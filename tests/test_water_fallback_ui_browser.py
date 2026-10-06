"""Fallback card and settings checks with a mocked Home Assistant backend."""
import json
import shutil
from playwright.sync_api import sync_playwright
from test_frontend import MOCK, HTML, ROOT


def run():
    checks=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        page=browser.new_page(viewport={'width':1100,'height':1000})
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.set_content(HTML);page.add_script_tag(content=MOCK)
        page.add_script_tag(path=str(ROOT/'custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'))
        page.wait_for_function("!!customElements.get('dobby-scheduler-card')")
        page.evaluate("const c=document.querySelector('dobby-scheduler-card');c.setConfig({type:'custom:dobby-scheduler-card',title:'Dobby'});c.hass=fakeHass;")
        page.wait_for_selector('.roomchip')
        assert page.locator('.water-fallback:visible').count()==0;checks.append('no invented fallback on normal queue')
        page.locator('[data-action=setup]').first.click()
        page.locator('[data-action=tab][data-id=settings]').click()
        option=page.locator('[data-cfg=vacuum_on_water_problem]')
        assert option.is_checked();checks.append('fallback enabled by default in setup')
        option.uncheck();page.locator('[data-action=save-settings]').click()
        assert page.evaluate('commands.at(-1).data.vacuum_on_water_problem') is False;checks.append('can opt out using UI without YAML')
        page.locator('[data-cfg=vacuum_on_water_problem]').check()
        page.locator('[data-action=save-settings]').click()
        assert page.evaluate('commands.at(-1).data.vacuum_on_water_problem') is True;checks.append('setting saves as boolean true')
        assert 'unknown/offline still blocks wet jobs' in page.locator('dialog').inner_text();checks.append('source uncertainty limit explained')
        page.locator('[data-action=close]').click()
        page.evaluate("""async()=>{demo.reason='Setting vacuum-only fallback';demo.enabled=true;
          demo.jobs[0].requested_mode='vac_and_mop';demo.jobs[0].effective_mode='vacuum';
          demo.jobs[0].water_fallback=true;demo.jobs[0].fallback_reason='Water tank needs attention; mopping skipped';
          demo.active={uid:'kitchen',name:'Kitchen',mode:'vacuum',requested_mode:'vac_and_mop',phase:'preparing',water_fallback:true};
          demo.activity={text:'Refill/reseat clean-water tank',icon:'mdi:water-alert-outline'};
          await document.querySelector('dobby-scheduler-card').refresh();} """)
        assert page.locator('.water-fallback:visible').count()==1;checks.append('active attempt has nonfault fallback banner')
        assert 'Kitchen' in page.locator('.water-fallback:visible').inner_text();checks.append('fallback banner identifies room')
        assert 'Room labels stay unchanged' in page.locator('.water-fallback:visible').inner_text();checks.append('temporary downgrade explained')
        assert 'Vacuum only' in page.locator('.roomchip').first.inner_text();checks.append('room chip does not still advertise wet run')
        assert 'mopping skipped' in page.locator('.job').first.inner_text();checks.append('queue row shows actual dry plan')
        page.locator('[data-action=job]').first.click()
        assert 'Requested: Vacuum + mop' in page.locator('dialog').inner_text();checks.append('job details preserve requested mode')
        assert 'Vacuum only - mopping skipped' in page.locator('dialog').inner_text();checks.append('job details show fallback result')
        page.locator('[data-action=close]').click()
        page.set_viewport_size({'width':390,'height':950})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');checks.append('390px no page overflow')
        page.locator('dobby-scheduler-card').screenshot(path=str(ROOT/'docs/previews/water-fallback-0.1.6-mobile.png'))
        page.evaluate("""async()=>{demo.active=null;demo.reason='Waiting for everyone to leave';
          Object.assign(demo.jobs[0],{status:'completed',mopping_skipped:true,executed_mode:'vacuum',result:'vacuum_only_water_fallback'});
          await document.querySelector('dobby-scheduler-card').refresh();}""")
        assert 'Vacuumed only - mop skipped' in page.locator('.roomchip').first.inner_text();checks.append('completed room visibly not marked mopped')
        assert 'Kitchen' in page.locator('.skipped-mopping').inner_text();checks.append('skipped mopping retained in daily summary')
        page.locator('dobby-scheduler-card').screenshot(path=str(ROOT/'docs/previews/water-result-0.1.6-mobile.png'))
        page.evaluate("""async()=>{demo.jobs[1].water_fallback=true;demo.jobs[1].name='<img src=x onerror=alert(1)>';
          await document.querySelector('dobby-scheduler-card').refresh();}""")
        assert page.locator('.water-fallback img').count()==0;checks.append('fallback names HTML escaped')
        page.evaluate("""async()=>{demo.fault='Vacuum error';await document.querySelector('dobby-scheduler-card').refresh();}""")
        assert page.locator('.water-fallback:visible').count()==0 and 'Vacuum error' in page.locator('[role=alert]').inner_text();checks.append('real fault not disguised by fallback banner')
        page.locator('[data-action=setup]').first.click()
        page.locator('[data-action=tab][data-id=help]').click()
        assert 'Water-tank fallback' in page.locator('dialog').inner_text();checks.append('embedded help documents behaviour')
        page.locator('[data-action=tab][data-id=settings]').click()
        assert page.locator('dialog').evaluate('(x)=>x.scrollWidth<=x.clientWidth+1');checks.append('settings mobile dialog no overflow')
        assert page.evaluate("commands.every(c=>c.action==='settings')");checks.append('display and setting changes issue no robot commands')
        assert not errors,errors;checks.append('no JavaScript exceptions')
        browser.close()
    result={'checks_passed':len(checks),'checks':checks,'browser_errors':errors,
      'scope':'Headless Chromium with mocked HA data, not a real Home Assistant installation or robot'}
    (ROOT/'docs/water-fallback-ui-0.1.6-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':run()
