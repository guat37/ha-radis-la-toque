"""Smoke test bundled card auto-loading without Lovelace Resources entry."""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "radis_la_toque"

# Package stubs
for name in ["custom_components", "custom_components.radis_la_toque"]:
    mod = types.ModuleType(name)
    mod.__path__ = []
    sys.modules[name] = mod

# HA stubs
ha = types.ModuleType("homeassistant")
sys.modules["homeassistant"] = ha
components = types.ModuleType("homeassistant.components")
sys.modules["homeassistant.components"] = components
frontend = types.ModuleType("homeassistant.components.frontend")
loaded_urls: list[str] = []
frontend.add_extra_js_url = lambda hass, url: loaded_urls.append(url)
sys.modules[frontend.__name__] = frontend
http = types.ModuleType("homeassistant.components.http")
class StaticPathConfig:
    def __init__(self, url_path, path, cache_headers):
        self.url_path = url_path
        self.path = path
        self.cache_headers = cache_headers
http.StaticPathConfig = StaticPathConfig
sys.modules[http.__name__] = http
core = types.ModuleType("homeassistant.core")
core.HomeAssistant = object
sys.modules[core.__name__] = core

const = types.ModuleType("custom_components.radis_la_toque.const")
const.DOMAIN = "radis_la_toque"
const.FRONTEND_CARD_FILENAME = "radis-la-toque-card.js"
const.FRONTEND_URL_BASE = "/radis_la_toque"
const.INTEGRATION_VERSION = "0.4.0-beta.2"
sys.modules[const.__name__] = const

spec = importlib.util.spec_from_file_location(
    "custom_components.radis_la_toque.frontend", ROOT / "frontend.py"
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec and spec.loader
spec.loader.exec_module(module)

class Http:
    def __init__(self): self.paths=[]
    async def async_register_static_paths(self, paths): self.paths.extend(paths)
class Hass:
    def __init__(self):
        self.data={}
        self.http=Http()

async def main():
    hass=Hass()
    await module.async_register_frontend(hass)
    await module.async_register_frontend(hass)  # idempotent
    assert len(hass.http.paths) == 1
    assert loaded_urls == ["/radis_la_toque/radis-la-toque-card.js?v=0.4.0-beta.2"]
    print("FRONTEND AUTOLOAD: PASS")

asyncio.run(main())
