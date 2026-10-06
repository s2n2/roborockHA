"""Real Chromium, simulated HA registry swap, no HA backend or robot.

This deliberately models (rather than bundles) HA's scoped registry installation.
It checks that registration is deferred and the card uses the post-swap base class.
"""
from pathlib import Path
import json
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parents[1]
CARD = ROOT / 'custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'
SWAP = r"""
window.beforeRegistry = window.customElements;
window.beforeHTMLElement = window.HTMLElement;
class ScopedHTMLElement extends window.beforeHTMLElement {}
const own = new Map();
const waits = new Map();
window.simulatedRegistry = {
  get(name) { return own.get(name); },
  define(name, ctor) {
    if (own.has(name)) throw new Error('duplicate simulated registry entry');
    own.set(name, ctor);
    if (!beforeRegistry.get(name)) beforeRegistry.define(name, ctor);
    for (const resolve of waits.get(name) || []) resolve(ctor);
    waits.delete(name);
  },
  whenDefined(name) {
    if (own.has(name)) return Promise.resolve(own.get(name));
    return new Promise(resolve => {
      if (!waits.has(name)) waits.set(name, []);
      waits.get(name).push(resolve);
    });
  }
};
Object.defineProperty(window, 'customElements', {configurable:true, value:simulatedRegistry});
Object.defineProperty(window, 'HTMLElement', {configurable:true, value:ScopedHTMLElement});
"""
READY = "customElements.define('home-assistant', class extends HTMLElement {});"
OLD_PATTERN = """
class OldDobby extends HTMLElement { static getStubConfig(){return {title:'Dobby'};} }
customElements.define('dobby-scheduler-card',OldDobby);
window.customCards=[{type:'dobby-scheduler-card',name:'Dobby Scheduler'}];
"""

def run():
    checks = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=shutil.which('chromium'))
        def page():
            value = browser.new_page()
            value.on('pageerror', lambda error: errors.append(str(error)))
            value.set_content('<!doctype html><body><main></main></body>')
            return value
        def registered(value):
            value.wait_for_function("!!customElements.get('dobby-scheduler-card')")
            result = value.evaluate("""() => {
              const C = customElements.get('dobby-scheduler-card');
              const c = document.createElement('dobby-scheduler-card');
              c.setConfig(C.getStubConfig());
              document.querySelector('main').append(c);
              return {correctBase:Object.getPrototypeOf(C.prototype)===HTMLElement.prototype,
                hasShadow:!!c.shadowRoot, hasMain:!!c.shadowRoot.querySelector('#main'),
                catalog:window.customCards.filter(x=>x.type==='dobby-scheduler-card').length,
                stage:window.dobbySchedulerCardStatus.stage, version:C.version};
            }""")
            assert result == dict(correctBase=True,hasShadow=True,hasMain=True,catalog=1,stage='registered',version='0.1.7'), result

        value = page()
        value.add_script_tag(content=OLD_PATTERN, type='module')
        value.evaluate(SWAP)
        value.evaluate(READY)
        assert value.evaluate("({registered:!!customElements.get('dobby-scheduler-card'),picker:window.customCards.length})") == dict(registered=False,picker=1)
        checks.append('reproduces original registration pattern losing visibility after registry replacement')
        value.close()

        value = page()
        value.add_script_tag(path=str(CARD), type='module')
        assert value.evaluate("!!customElements.get('dobby-scheduler-card')") is False
        assert value.evaluate("(window.customCards||[]).length") == 0
        value.evaluate(SWAP)
        value.evaluate(READY)
        registered(value)
        checks.append('cold-load module before replacement: registers late and constructs with post-swap HTMLElement')
        value.close()

        value = page()
        value.evaluate(SWAP)
        value.add_script_tag(path=str(CARD), type='module')
        assert value.evaluate("!!customElements.get('dobby-scheduler-card')") is False
        value.evaluate(READY)
        registered(value)
        checks.append('module after replacement but before HA root: registers when root is defined')
        value.close()

        value = page()
        value.evaluate(SWAP)
        value.evaluate(READY)
        value.add_script_tag(path=str(CARD), type='module')
        registered(value)
        value.add_script_tag(content=CARD.read_text()+'\n// alternate module URL simulation', type='module')
        registered(value)
        checks.append('warm-load and duplicate module: constructor works and picker remains unique')
        value.close()

        value = page()
        value.add_script_tag(path=str(CARD), type='module')
        value.add_script_tag(content=CARD.read_text()+'\n// second early module', type='module')
        value.evaluate(SWAP)
        value.evaluate(READY)
        registered(value)
        checks.append('two simultaneous pre-root imports: one usable card definition')
        value.close()
        browser.close()
    assert not errors, errors
    result = dict(checks_passed=len(checks),checks=checks,browser_errors=errors,
                  scope='Real headless Chromium with a simulated HA registry swap, not the real HA scoped registry polyfill or a live HA/robot test.')
    (ROOT/'docs'/'frontend_startup_test_results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__ == '__main__':
    run()
