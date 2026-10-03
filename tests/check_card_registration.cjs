// Simulate two ES-module scopes: automatic module + a legacy manual resource.
// This tests picker registration, not an installed Home Assistant dashboard.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../custom_components/dobby_scheduler/frontend/dobby-scheduler-card.js'), 'utf8');
const definitions = new Map();
const context = vm.createContext({
  window: {customCards: [{type: 'unrelated-card', name: 'Other card'}]},
  HTMLElement: class {},
  customElements: {
    get: key => definitions.get(key),
    define: (key, value) => {assert(!definitions.has(key)); definitions.set(key, value);}
  },
});
const run = () => vm.runInContext(`(() => {\n${source}\n})();`, context);
run();
assert(definitions.has('dobby-scheduler-card'));
const ctor = definitions.get('dobby-scheduler-card');
assert.equal(ctor.getStubConfig().title, 'Dobby');
assert.equal(context.window.customCards.filter(c => c.type === 'dobby-scheduler-card').length, 1);
assert.equal(context.window.customCards.find(c => c.type === 'dobby-scheduler-card').name, 'Dobby Scheduler');
run();
assert.equal(definitions.get('dobby-scheduler-card'), ctor);
assert.equal(context.window.customCards.length, 2);
assert.equal(context.window.customCards[0].type, 'unrelated-card');
assert.equal(context.window.customCards[1].documentationURL, 'https://github.com/s2n2/roborockHA');
console.log('Card registration checks passed: picker metadata, stub config, duplicate imports, unrelated metadata preserved.');
