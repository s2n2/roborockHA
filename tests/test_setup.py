"""Bootstrap contract simulations; not a live Home Assistant runtime."""
from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest

ROOT = Path(__file__).parents[1]
BASE = ROOT / 'custom_components' / 'dobby_scheduler'
MANIFEST = json.loads((BASE / 'manifest.json').read_text())


@pytest.fixture
def bootstrap(monkeypatch):
    def mod(name, **attrs):
        value = ModuleType(name)
        value.__dict__.update(attrs)
        monkeypatch.setitem(sys.modules, name, value)
        return value

    calls = NS(paths=[], modules=[], api=[], flows=[], forwarded=[])
    mod('homeassistant')
    mod('homeassistant.components')
    mod('homeassistant.components.frontend', add_extra_js_url=lambda hass, url, es5=False: calls.modules.append((url, es5)))
    mod('homeassistant.components.http', StaticPathConfig=lambda url, path, cache_headers: NS(url_path=url, path=path, cache_headers=cache_headers))
    mod('homeassistant.config_entries', SOURCE_IMPORT='import')
    mod('homeassistant.helpers')
    mod('homeassistant.helpers.config_validation', string=str)

    package_name = 'dobby_bootstrap_tests'
    # Stub the schema and controller dependencies so importing __init__ exercises
    # only bootstrap logic. These tests do not imply full HA compatibility.
    schema = NS(Schema=lambda *a, **kw: object(), Optional=lambda key, **kw: key, ALLOW_EXTRA=object())
    mod(package_name + '.compat', vol=schema)

    class Controller:
        def __init__(self, hass, entry):
            self.entry = entry
            self.loaded = False
            self.unloaded = False

        async def async_load(self):
            self.loaded = True

        async def async_unload(self):
            self.unloaded = True

    mod(package_name + '.controller', DobbyController=Controller, DOMAIN='dobby_scheduler')
    mod(package_name + '.api', register_api=lambda hass: calls.api.append(True))

    async def paths(values):
        calls.paths.extend(values)

    async def flow(domain, **kwargs):
        calls.flows.append((domain, kwargs))

    async def forward(entry, platforms):
        calls.forwarded.append((entry.entry_id, platforms))

    tasks = []
    hass = NS(data={}, http=NS(async_register_static_paths=paths), async_create_task=tasks.append,
              config_entries=NS(flow=NS(async_init=flow), async_forward_entry_setups=forward))
    spec = importlib.util.spec_from_file_location(package_name, BASE / '__init__.py', submodule_search_locations=[str(BASE)])
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, package_name, module)
    spec.loader.exec_module(module)
    yield module, hass, calls, tasks
    for task in tasks:
        task.close()
    sys.modules.pop(package_name + '.const', None)


def test_manifest_service_not_helper():
    assert MANIFEST['integration_type'] == 'service'


def test_manifest_requires_frontend():
    assert 'frontend' in MANIFEST['dependencies']
    assert MANIFEST['config_flow'] is True


def test_release_and_domain(bootstrap):
    module, hass, calls, tasks = bootstrap
    assert module.DOMAIN == 'dobby_scheduler'
    assert MANIFEST['version'] == '0.1.5'
    assert module.CARD_URL.endswith('?v=' + MANIFEST['version'])


def test_serves_actual_bundled_card(bootstrap):
    module, hass, calls, tasks = bootstrap
    assert asyncio.run(module.async_setup(hass, {}))
    assert len(calls.paths) == 1
    assert calls.paths[0].url_path == '/dobby_scheduler_frontend'
    assert (Path(calls.paths[0].path) / 'dobby-scheduler-card.js').is_file()
    assert calls.paths[0].cache_headers is False


def test_loads_module_without_lovelace_storage(bootstrap):
    module, hass, calls, tasks = bootstrap
    asyncio.run(module.async_setup(hass, {}))
    assert calls.modules == [('/dobby_scheduler_frontend/dobby-scheduler-card.js?v=0.1.5', False)]
    assert 'lovelace' not in hass.data
    assert 'lovelace_data' not in hass.data


def test_setup_idempotent(bootstrap):
    module, hass, calls, tasks = bootstrap
    asyncio.run(module.async_setup(hass, {}))
    asyncio.run(module.async_setup(hass, {}))
    assert len(calls.api) == len(calls.paths) == len(calls.modules) == 1


def test_old_process_data_still_registers_frontend(bootstrap):
    module, hass, calls, tasks = bootstrap
    hass.data[module.DOMAIN] = {'api_registered': True}
    asyncio.run(module.async_setup(hass, {}))
    assert not calls.api and not calls.paths
    assert len(calls.modules) == 1


def test_bootstrap_preserves_existing_entry_data(bootstrap):
    module, hass, calls, tasks = bootstrap
    sentinel = object()
    hass.data[module.DOMAIN] = {'existing-entry': sentinel}
    config = {'unrelated': {'keep': 'unchanged'}}
    asyncio.run(module.async_setup(hass, config))
    assert hass.data[module.DOMAIN]['existing-entry'] is sentinel
    assert config == {'unrelated': {'keep': 'unchanged'}}
    assert not tasks and not calls.flows


def test_optional_yaml_import_keeps_domain(bootstrap):
    module, hass, calls, tasks = bootstrap
    asyncio.run(module.async_setup(hass, {module.DOMAIN: {'name': 'Dobby'}}))
    assert len(tasks) == 1
    asyncio.run(tasks.pop())
    assert calls.flows == [('dobby_scheduler', {'context': {'source': 'import'}, 'data': {'name': 'Dobby'}})]


def test_entry_setup_uses_existing_entry_id(bootstrap):
    module, hass, calls, tasks = bootstrap
    entry = NS(entry_id='existing-entry', title='Dobby Scheduler')
    asyncio.run(module.async_setup(hass, {}))
    assert asyncio.run(module.async_setup_entry(hass, entry))
    assert entry.runtime_data is hass.data[module.DOMAIN]['existing-entry']
    assert entry.runtime_data.loaded
    assert calls.forwarded == [('existing-entry', ['sensor', 'switch', 'todo'])]
