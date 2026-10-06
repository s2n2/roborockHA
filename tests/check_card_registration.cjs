// Regression simulations for the HA frontend registry-replacement race.
// These model the native -> scoped registry transition, not a live HA instance.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'), 'utf8');
const TAG = 'dobby-scheduler-card';
const checks = [];
const tick = () => new Promise(resolve => setImmediate(resolve));

class Registry {
  constructor(native = null) { this.entries = new Map(); this.waiters = new Map(); this.native = native; }
  get(key) { return this.entries.get(key); }
  whenDefined(key) {
    if (this.get(key)) return Promise.resolve(this.get(key));
    return new Promise(resolve => {
      if (!this.waiters.has(key)) this.waiters.set(key, []);
      this.waiters.get(key).push(resolve);
    });
  }
  define(key, value) {
    assert(!this.entries.has(key), `Duplicate registration: ${key}`);
    this.entries.set(key, value);
    for (const resolve of this.waiters.get(key) || []) resolve(value);
    this.waiters.delete(key);
    // A scoped registry installs a stand-in in the native registry, which also
    // resolves native whenDefined promises started before the replacement.
    if (this.native && !this.native.get(key)) this.native.define(key, class StandIn {});
  }
}
function environment(ready = false) {
  const native = new Registry();
  const messages = [];
  const NativeHTMLElement = class {};
  const context = vm.createContext({
    HTMLElement: NativeHTMLElement, customElements: native,
    customCards: [{type: 'unrelated-card', name: 'Other card'}],
    console: {info: (...args) => messages.push(['info', ...args]), warn: (...args) => messages.push(['warn', ...args]), error: (...args) => messages.push(['error', ...args])}
  });
  context.window = context;
  if (ready) native.define('home-assistant', class extends NativeHTMLElement {});
  return {native, context, NativeHTMLElement, messages};
}
function run(env, code = source) { vm.runInContext(`(() => {\n${code}\n})();`, env.context); }
function installScopedRegistry(env) {
  env.context.HTMLElement = class ScopedHTMLElement {};
  env.context.customElements = new Registry(env.native);
  return env.context.customElements;
}
function ready(env) { env.context.customElements.define('home-assistant', class extends env.context.HTMLElement {}); }
function assertRegistered(env) {
  const ctor = env.context.customElements.get(TAG);
  assert(ctor);
  assert.equal(ctor.version, '0.1.6');
  assert.equal(ctor.getStubConfig().title, 'Dobby');
  assert.equal(Object.getPrototypeOf(ctor.prototype), env.context.HTMLElement.prototype);
  assert.equal(env.context.customCards.filter(c => c.type === TAG).length, 1);
  assert.equal(env.context.customCards.find(c => c.type === TAG).documentationURL, 'https://github.com/s2n2/roborockHA');
  assert.equal(env.context.dobbySchedulerCardStatus.stage, 'registered');
  assert.equal(env.messages.filter(m => m[0] === 'error').length, 0);
  return ctor;
}
async function main() {
  let env = environment();
  // This is the 0.1.1 registration pattern, which produces the user's exact
  // console combination after registry replacement. No network is required.
  run(env, `class OldDobby extends HTMLElement { static getStubConfig(){return {title:'Dobby'};} }
    customElements.define('${TAG}', OldDobby);
    window.customCards.push({type:'${TAG}',name:'Dobby Scheduler'});`);
  assert(env.native.get(TAG));
  installScopedRegistry(env); ready(env); await tick();
  assert.equal(env.context.customElements.get(TAG), undefined);
  assert.equal(env.context.customCards.filter(c => c.type === TAG).length, 1);
  checks.push('reproduces 0.1.1: picker entry present but active-registry element missing');

  env = environment(true); run(env); await tick();
  let ctor = assertRegistered(env);
  checks.push('warm frontend: card registered and stub available');
  run(env); await tick();
  assert.equal(assertRegistered(env), ctor);
  assert.equal(env.context.customCards.length, 2);
  assert.equal(env.context.customCards[0].type, 'unrelated-card');
  checks.push('duplicate module import: same constructor and one picker entry');

  env = environment(); run(env); await tick();
  assert.equal(env.native.get(TAG), undefined);
  assert.equal(env.context.customCards.length, 1);
  assert.equal(env.context.dobbySchedulerCardStatus.stage, 'waiting-for-home-assistant');
  checks.push('cold frontend: no early native registration and no phantom picker entry');
  installScopedRegistry(env); ready(env); await tick();
  assertRegistered(env);
  checks.push('registry replacement: registers with final registry and final HTMLElement');

  env = environment(); run(env); run(env); await tick();
  installScopedRegistry(env); ready(env); await tick();
  assertRegistered(env);
  checks.push('two simultaneous early imports: one final registration');

  env = environment(); installScopedRegistry(env); run(env); await tick();
  assert.equal(env.context.customElements.get(TAG), undefined);
  ready(env); await tick(); assertRegistered(env);
  checks.push('module between polyfill and HA root: waits then registers');

  env = environment(); run(env); await tick();
  ready(env); await tick(); assertRegistered(env);
  checks.push('no registry replacement: delayed HA root still works');

  env = environment(true);
  env.context.customCards.push({type:TAG,name:'Outdated metadata'});
  run(env); await tick(); assertRegistered(env);
  assert.equal(env.context.customCards.find(c => c.type === TAG).name, 'Dobby Scheduler');
  checks.push('stale picker metadata repaired without a duplicate');

  env = environment(true);
  const oldCtor = class OldCard extends env.context.HTMLElement {};
  env.native.define(TAG, oldCtor);
  run(env); await tick();
  assert.equal(env.native.get(TAG), oldCtor);
  assert.equal(env.context.dobbySchedulerCardStatus.elementVersion, 'older-build');
  assert(env.messages.some(m => m[0] === 'warn'));
  checks.push('existing older registered card: kept intact with explicit refresh warning');

  env = environment(true);
  const originalDefine = env.native.define.bind(env.native);
  env.native.define = (key, value) => { if(key === TAG) throw new Error('Simulated define failure'); originalDefine(key,value); };
  run(env); await tick();
  assert.equal(env.context.dobbySchedulerCardStatus.stage, 'failed');
  assert.equal(env.context.customCards.filter(c => c.type === TAG).length, 0);
  assert(env.messages.some(m => m[0] === 'error'));
  checks.push('registration failure: diagnostic error and no advertised unusable card');

  console.log(JSON.stringify({passed:checks.length,checks,scope:'Mocked browser registry transition; not a live Home Assistant or robot test.'}, null, 2));
}
main().catch(error => {console.error(error);process.exitCode=1;});
