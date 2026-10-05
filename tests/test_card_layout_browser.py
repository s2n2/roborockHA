"""Responsive-layout regressions with a mocked HA backend; never contacts a robot."""
import copy
import json
import re
import runpy
import shutil
import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).parents[1]
BASE=runpy.run_path(str(ROOT/'tests/test_frontend.py'))
DATA=BASE['DATA']
JS=(ROOT/'custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js').read_text()
OUT=ROOT/'docs'/'previews'
ICONS=r"""
customElements.define('ha-icon',class extends HTMLElement{
 connectedCallback(){
  const key=this.getAttribute('icon');
  const icons={
   'mdi:robot-vacuum':'<circle cx="12" cy="12" r="9"/><path d="M5 7l2 2m10 0 2-2M7 15c2 5 8 5 10 0"/><circle cx="9" cy="10" r="1" fill="currentColor"/><circle cx="15" cy="10" r="1" fill="currentColor"/>',
   'mdi:cog-outline':'<path d="M9 3h6l.7 3 3 1 2.3 4-2.3 2.4.3 3.3-4 2.3L12 18l-3 1-4-2.3.3-3.3L3 11l2.3-4 3-1Z"/><circle cx="12" cy="11" r="3"/>',
   'mdi:tune':'<path d="M3 6h18M3 12h18M3 18h18M8 3v6m8 0v6m-6 0v6"/>',
   'mdi:play':'<path d="m7 4 13 8-13 8Z" fill="currentColor" stroke="none"/>',
   'mdi:home-import-outline':'<path d="m3 11 9-8 9 8M6 9v11h12V9M1 15h10m-3-3 3 3-3 3"/>',
   'mdi:check-circle':'<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
   'mdi:check-circle-outline':'<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
   'mdi:circle-outline':'<circle cx="12" cy="12" r="9"/>',
   'mdi:alert-outline':'<path d="M12 3 2 21h20ZM12 9v5m0 3v1"/>',
   'mdi:floor-plan':'<path d="M3 3h18v18H3Zm0 9h9V3m0 9v9m0-5h9"/>',
   'mdi:map-search-outline':'<path d="m2 5 6-2 7 2 7-2v12m-14-12v17m7-15v6m-13-6v16l6-2 4 1"/><circle cx="17" cy="16" r="4"/><path d="m20 19 3 3"/>',
   'mdi:arrow-right':'<path d="M4 12h16m-7-7 7 7-7 7"/>',
   'mdi:priority-high':'<path d="M12 4v11m0 3v2"/>',
   'mdi:chevron-up':'<path d="m6 15 6-6 6 6"/>',
   'mdi:chevron-down':'<path d="m6 9 6 6 6-6"/>',
   'mdi:close':'<path d="m6 6 12 12M18 6 6 18"/>',
   'mdi:dots-horizontal':'<circle cx="4" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="20" cy="12" r="1"/>'
  };
  const root=this.attachShadow({mode:'open'});
  root.innerHTML='<style>:host{display:inline-flex;align-items:center;justify-content:center}svg{width:var(--mdc-icon-size,20px);height:var(--mdc-icon-size,20px)}</style><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+(icons[key]||'<circle cx="12" cy="12" r="8"/>')+'</svg>';
 }
});
"""

def mount(page,data,width=360,viewport=1440,dark=False,source=JS):
    page.set_viewport_size({'width':viewport,'height':1000})
    theme='--primary-color:#73cabe;--primary-text-color:#e5ecec;--secondary-text-color:#9faeb1;--card-background-color:#202729;--secondary-background-color:#272f32;--divider-color:#3b484b;--text-primary-color:#14201f;' if dark else '--primary-color:#147d75;--primary-text-color:#24393d;--secondary-text-color:#64767b;--card-background-color:white;--secondary-background-color:#f4f7f7;--divider-color:#dfe7e7;'
    page.set_content('<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;padding:16px;font:28px Arial;background:'+('#111819' if dark else '#edf2f3')+';'+theme+'}main{width:'+str(width)+'px;max-width:100%;margin:0 auto}.label{font:10px Arial;color:'+('#acbabb' if dark else '#6b8087')+';text-align:center;margin-bottom:12px;letter-spacing:.08em}</style></head><body><main><div class="label">SIMULATED PREVIEW - DOBBY 0.1.4</div><dobby-scheduler-card></dobby-scheduler-card></main></body></html>')
    mock=BASE['MOCK'].replace('window.demo='+json.dumps(DATA)+';', 'window.demo='+json.dumps(data)+';')
    mock=re.sub(r"customElements.define\('ha-icon',class extends HTMLElement\{.*?\n\}\);",lambda m:ICONS,mock,count=1,flags=re.S)
    page.add_script_tag(content=mock)
    page.add_script_tag(content=source)
    page.wait_for_function("!!customElements.get('dobby-scheduler-card')")
    page.evaluate("const c=document.querySelector('dobby-scheduler-card');c.setConfig({type:'custom:dobby-scheduler-card',title:'Dobby'});c.hass=fakeHass;")
    page.wait_for_selector('.summary')


def no_overflow(page,modal=False):
    scope='dialog .pane' if modal else 'ha-card'
    return page.locator(scope).evaluate('(e)=>({ok:e.scrollWidth<=e.clientWidth+1,scroll:e.scrollWidth,width:e.clientWidth})')


def run():
    checks=[]; errors=[]; OUT.mkdir(exist_ok=True)
    def check(condition,name):
        assert condition,name
        checks.append(name)
    empty=copy.deepcopy(DATA)
    empty.update(jobs=[],rooms=[dict(r,cleanable=False) for r in DATA['rooms']])
    empty['telemetry']['battery']=None
    empty['telemetry']['legacy']=[{'name':'Old Dobby schedule','entity_id':'automation.dobby_clean_daily_when_noone_is_home'}]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'))
        for width in (300,340,380,520,720):
            page=browser.new_page()
            page.on('pageerror',lambda err:errors.append(str(err)))
            mount(page,empty,width)
            check(no_overflow(page)['ok'],f'empty card no overflow: {width}px card / 1440px desktop')
            check(page.locator('.summary').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'),f'summary bounded: {width}px')
            check(page.locator('.summary strong').evaluate_all('(xs)=>xs.every(e=>e.scrollWidth<=e.clientWidth+1)'),f'summary text fits: {width}px')
            check(page.locator('.empty-onboarding button').evaluate('(e)=>{const b=e.getBoundingClientRect(),p=e.parentElement.getBoundingClientRect();return b.right<=p.right&&b.left>=p.left}'),f'onboarding button stays inside card: {width}px')
            check(page.evaluate('commands.length===0'),f'initial UI sends no commands: {width}px')
            if width==340:
                box=page.locator('.summary .metric-main').bounding_box();other=page.locator('.summary .metric-complete').bounding_box()
                check(box['y']<other['y'],'narrow DESKTOP column uses stacked summary')
                page.locator('main').screenshot(path=str(OUT/'ui-0.1.4-empty.png'))
                check(page.evaluate("!('rows' in document.querySelector('dobby-scheduler-card').getGridOptions())"),'no forced Sections row count')
            if width==720:
                box=page.locator('.summary .metric-main').bounding_box();other=page.locator('.summary .metric-complete').bounding_box()
                check(abs(box['y']-other['y'])<2,'wide card has a single summary row')
            page.close()
        # Long names, populated states, and large inherited dashboard typography.
        data=copy.deepcopy(DATA)
        data['rooms'][0]['name']='Kitchen and open-plan dining area with a very long room name'
        data['jobs'][0]['name']=data['rooms'][0]['name']
        data['jobs'][0]['urgent']=True
        data['enabled']=True
        data['reason']='Waiting for everyone to leave'
        for width in (300,340,420):
            page=browser.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
            mount(page,data,width)
            check(no_overflow(page)['ok'],f'long room names do not overflow: {width}px')
            check(page.locator('.job .actions').evaluate_all('(xs)=>xs.every(e=>{let b=e.getBoundingClientRect(),p=e.parentElement.getBoundingClientRect();return b.right<=p.right+1&&b.left>=p.left-1})'),f'queue controls contained: {width}px')
            check(page.locator('dobby-scheduler-card').evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)===14'),f'28px parent font cannot inflate card: {width}px')
            page.close()
        for viewport in (360,390,768,1440):
            page=browser.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
            mount(page,DATA,340,viewport)
            page.locator('[data-action="setup"]').first.click()
            check(page.locator('dialog').is_visible(),f'popup opens: {viewport}px viewport')
            for tab in ('rooms','settings','switches','help','diagnostics'):
                page.locator('[data-action="tab"][data-id="'+tab+'"]').click()
                check(no_overflow(page,True)['ok'],f'{tab} pane bounded: {viewport}px viewport')
                check(page.locator('dialog .tabs').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'),f'tabs bounded in {tab}: {viewport}px')
                if tab=='rooms' and viewport<768:
                    check(page.locator('#room-choice').is_visible(),f'mobile Area selector visible: {viewport}px')
                    page.locator('#room-choice').select_option('lounge')
                    check(page.locator('.roomlayout section h3').inner_text()=='Lounge',f'mobile Area selector works: {viewport}px')
                    page.locator('#room-choice').select_option('kitchen')
                if tab=='settings':
                    check(page.locator('.settings-section').count()==2,f'settings grouped into two sections: {viewport}px')
                    page.locator('[data-action="save-settings"]').scroll_into_view_if_needed()
                    head=page.locator('.dialoghead').bounding_box()
                    check(head['y']>=0 and head['y']<100,f'popup header stays visible when pane scrolls: {viewport}px')
            if viewport in (390,1440):
                page.locator('[data-action="tab"][data-id="rooms"]').click()
                page.locator('dialog').screenshot(path=str(OUT/f'ui-0.1.4-setup-{viewport}.png'))
                page.locator('[data-action="tab"][data-id="settings"]').click()
                page.locator('dialog').screenshot(path=str(OUT/f'ui-0.1.4-settings-{viewport}.png'))
            check(page.evaluate('commands.length===0'),f'opening and browsing setup sends no write commands: {viewport}px')
            page.close()
        # Independent theme previews and switch accessibility/dispatch.
        for dark in (False,True):
            page=browser.new_page();page.on('pageerror',lambda err:errors.append(str(err)))
            mount(page,DATA,380,900,dark)
            check(no_overflow(page)['ok'],f'theme layout: {"dark" if dark else "light"}')
            page.locator('[data-setting="auto"]').check()
            check(page.evaluate("commands.at(-1).action==='enable'&&commands.at(-1).data.enabled===true"),f'automatic switch retains behaviour: {dark}')
            page.locator('main').screenshot(path=str(OUT/f'ui-0.1.4-populated-{"dark" if dark else "light"}.png'))
            page.close()
        check(not errors,'no browser JavaScript exceptions')
        browser.close()
    result={'checks_passed':len(checks),'checks':checks,'browser_errors':errors,'environment':'System Chromium, mock HA API and icon renderer. Not a live Home Assistant or Dwains dashboard; no robot commands or credentials.'}
    (ROOT/'docs/layout-0.1.4-test-results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':run()
