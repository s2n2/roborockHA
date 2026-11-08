"""0.2.0 fault/recovery card checks with a mocked Home Assistant backend."""
import json
import shutil
from playwright.sync_api import sync_playwright
from test_frontend import MOCK, HTML, ROOT


def refresh(page, js):
    page.evaluate("async()=>{" + js + ";await document.querySelector('dobby-scheduler-card').refresh();}")


def run():
    checks = []; errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=shutil.which('chromium'))
        page = browser.new_page(viewport={'width': 1100, 'height': 1000})
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.set_content(HTML); page.add_script_tag(content=MOCK)
        page.add_script_tag(path=str(ROOT / 'custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'))
        page.wait_for_function("!!customElements.get('dobby-scheduler-card')")
        page.evaluate("const c=document.querySelector('dobby-scheduler-card');c.setConfig({type:'custom:dobby-scheduler-card',title:'Dobby'});c.hass=fakeHass;")
        page.wait_for_selector('.roomchip')

        refresh(page, "demo.fault='error: Vacuum error or error reading unavailable';demo.needs_attention=false;"
                      "demo.fault_retry={used:1,limit:2,room_uid:'kitchen',recoverable:true}")
        banner = page.locator('.warn.recovering')
        assert banner.count() == 1 and page.locator('[role=alert]').count() == 0; checks.append('self-healing fault is a calm status, not an alarm')
        text = banner.inner_text()
        assert 'Recovering automatically' in text and 'Retry 2 of 2' in text; checks.append('shows which automatic retry is next')
        assert 'skipped for today' in text; checks.append('explains skip instead of blocking')
        page.locator('.warn.recovering [data-action=retry]').click()
        assert page.evaluate('commands.at(-1).action') == 'retry'; checks.append('Retry now still sends the manual retry')

        refresh(page, "demo.needs_attention=true")
        alert = page.locator('[role=alert]')
        assert alert.count() == 1 and 'Dobby needs you' in alert.inner_text(); checks.append('needs-you fault is an alert')
        assert page.locator('.warn.recovering').count() == 0; checks.append('no recovering banner while waiting for a person')

        refresh(page, "demo.fault='';demo.needs_attention=false;demo.fault_retry=null;demo.skipped_rooms=['Hallway']")
        assert 'Skipped today' in page.locator('body').inner_text() or 'Skipped today' in page.locator('dobby-scheduler-card').evaluate('e=>e.shadowRoot.textContent'); checks.append('skipped rooms are listed')
        assert page.locator('[role=alert]').count() == 0; checks.append('a skipped room is not an alarm')

        page.locator('[data-action=setup]').first.click()
        page.locator('[data-action=tab][data-id=settings]').click()
        dialog = page.locator('dialog').inner_text()
        assert 'Faults & notifications' in dialog; checks.append('fault settings section present')
        assert 'APP_CHARGE' not in dialog; checks.append('old APP_CHARGE-only wording removed')
        page.locator('[data-cfg=auto_retries]').fill('3'); page.locator('[data-cfg=auto_retries]').dispatch_event('change')
        page.locator('[data-cfg=notify_service]').fill('notify.mobile_app_phone'); page.locator('[data-cfg=notify_service]').dispatch_event('change')
        page.locator('[data-action=save-settings]').click()
        saved = page.evaluate('commands.at(-1).data')
        assert saved.get('auto_retries') == 3 and saved.get('notify_service') == 'notify.mobile_app_phone'; checks.append('retry and notify settings save with types')
        page.locator('[data-action=close]').click()

        page.set_viewport_size({'width': 360, 'height': 800})
        refresh(page, "demo.fault='dock: Error while calling APP_CHARGE';demo.needs_attention=false;demo.fault_retry={used:0,limit:2,room_uid:'kitchen'}")
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'); checks.append('mobile recovering banner no horizontal overflow')
        browser.close()
    assert not errors, errors; checks.append('no browser JavaScript exceptions')
    print(json.dumps({'passed': len(checks), 'checks': checks, 'browser_errors': errors,
                      'environment': 'Headless Chromium with mocked Home Assistant backend; not an installed HA dashboard'}, indent=2))


if __name__ == '__main__':
    run()
