"""Config-entry migration regression: preserve entity IDs while fixing stable identity."""
from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import re
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "radis_la_toque"

for name in ["custom_components", "custom_components.radis_la_toque"]:
    mod = types.ModuleType(name); mod.__path__=[]; sys.modules[name]=mod

ha = types.ModuleType("homeassistant"); sys.modules["homeassistant"] = ha
ce = types.ModuleType("homeassistant.config_entries")
class ConfigEntry:
    @classmethod
    def __class_getitem__(cls, item): return cls
ce.ConfigEntry = ConfigEntry
sys.modules[ce.__name__] = ce
core = types.ModuleType("homeassistant.core"); core.HomeAssistant=object; sys.modules[core.__name__]=core
helpers = types.ModuleType("homeassistant.helpers"); sys.modules[helpers.__name__]=helpers
aio = types.ModuleType("homeassistant.helpers.aiohttp_client"); aio.async_get_clientsession=lambda hass: object(); sys.modules[aio.__name__]=aio

client = types.ModuleType("custom_components.radis_la_toque.client")
client.RadisLaToqueClient = object
class RestaurantNotFound(Exception): pass
client.RestaurantNotFound = RestaurantNotFound
def restaurant_id_from_url(url):
    m=re.search(r"/entry-(\d+)(?:-|\.html|/|$)", url)
    if not m: raise RestaurantNotFound
    return f"entry-{m.group(1)}"
client.restaurant_id_from_url=restaurant_id_from_url
sys.modules[client.__name__]=client

const = types.ModuleType("custom_components.radis_la_toque.const")
for k,v in {
    "CONF_ENTITY_PREFIX":"entity_prefix",
    "CONF_RESTAURANT_CODE":"restaurant_code",
    "CONF_RESTAURANT_ID":"restaurant_id",
    "CONF_RESTAURANT_URL":"restaurant_url",
    "PLATFORMS":["sensor","calendar"],
}.items(): setattr(const,k,v)
sys.modules[const.__name__]=const
coord=types.ModuleType("custom_components.radis_la_toque.coordinator"); coord.RadisLaToqueCoordinator=type("C",(),{}); sys.modules[coord.__name__]=coord
front=types.ModuleType("custom_components.radis_la_toque.frontend")
async def async_register_frontend(hass): pass
front.async_register_frontend=async_register_frontend; sys.modules[front.__name__]=front

spec=importlib.util.spec_from_file_location("custom_components.radis_la_toque.__init__", ROOT/"__init__.py")
module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; assert spec and spec.loader; spec.loader.exec_module(module)

class Entry:
    version=1
    entry_id="01TEST"
    unique_id="R03436"
    data={
        "restaurant_code":"R03436",
        "restaurant_url":"https://www.radislatoque.fr/les-menus-de-la-cantine/liste-des-restaurants/entry-1247-rs-st-etienne-de-chigny.html",
    }
class Manager:
    def async_update_entry(self, entry, **kwargs):
        for k,v in kwargs.items(): setattr(entry,k,v)
class Hass:
    config_entries=Manager()

entry=Entry()
assert asyncio.run(module.async_migrate_entry(Hass(), entry)) is True
assert entry.version == 2
assert entry.unique_id == "entry-1247"
assert entry.data["restaurant_id"] == "entry-1247"
assert entry.data["entity_prefix"] == "R03436"  # old entity/device IDs preserved
print("CONFIG MIGRATION V1->V2: PASS")
