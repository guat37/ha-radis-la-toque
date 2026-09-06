"""Import/runtime smoke test of calendar.py using minimal Home Assistant stubs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import pathlib
import runpy
import sys
import types

ns = runpy.run_path(str(pathlib.Path(__file__).with_name("run_regression.py")), run_name="fixture_loader")
load = ns["load"]
ROOT = ns["ROOT"]
models = ns["models"]
presentation = load(
    "custom_components.radis_la_toque.client.presentation",
    ROOT / "client" / "presentation.py",
)

# Minimal HA modules used by calendar.py.
ha = types.ModuleType("homeassistant")
sys.modules["homeassistant"] = ha
components = types.ModuleType("homeassistant.components")
sys.modules["homeassistant.components"] = components
calendar_mod = types.ModuleType("homeassistant.components.calendar")

@dataclass
class CalendarEvent:
    start: object
    end: object
    summary: str
    description: str | None = None
    location: str | None = None

class CalendarEntity:
    pass

calendar_mod.CalendarEvent = CalendarEvent
calendar_mod.CalendarEntity = CalendarEntity
sys.modules[calendar_mod.__name__] = calendar_mod

core_mod = types.ModuleType("homeassistant.core")
core_mod.HomeAssistant = type("HomeAssistant", (), {})
sys.modules[core_mod.__name__] = core_mod

helpers_mod = types.ModuleType("homeassistant.helpers")
sys.modules[helpers_mod.__name__] = helpers_mod
entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
entity_platform.AddEntitiesCallback = object
sys.modules[entity_platform.__name__] = entity_platform

util_mod = types.ModuleType("homeassistant.util")
sys.modules[util_mod.__name__] = util_mod
dt_mod = types.ModuleType("homeassistant.util.dt")
dt_mod.now = lambda: datetime(2026, 9, 5, 12, 0, 0)
sys.modules[dt_mod.__name__] = dt_mod
util_mod.dt = dt_mod

pkg = sys.modules["custom_components.radis_la_toque"]
pkg.RadisLaToqueConfigEntry = object
client_pkg = sys.modules["custom_components.radis_la_toque.client"]
client_pkg.DayMenu = models.DayMenu
coord_mod = types.ModuleType("custom_components.radis_la_toque.coordinator")
coord_mod.RadisLaToqueCoordinator = type("RadisLaToqueCoordinator", (), {})
sys.modules[coord_mod.__name__] = coord_mod
entity_mod = types.ModuleType("custom_components.radis_la_toque.entity")
class RadisLaToqueEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator
entity_mod.RadisLaToqueEntity = RadisLaToqueEntity
sys.modules[entity_mod.__name__] = entity_mod

calendar = load("custom_components.radis_la_toque.calendar", ROOT / "calendar.py")

item_main = models.MenuItem("Colin Dugléré", models.MenuCategory.MAIN_COURSE)
item_side = models.MenuItem("Haricots verts", models.MenuCategory.SIDE)
day = models.DayMenu(date(2026, 9, 7), "Lundi 07/09", (item_main, item_side))
event = calendar._as_event(day)
assert event.start == date(2026, 9, 7)
assert event.end == date(2026, 9, 8)
assert event.summary == "Colin Dugléré · Haricots verts"
assert "Colin Dugléré" in event.description
print("CALENDAR PLATFORM STUB: PASS")

# Entity behavior: current/next event and date-range filtering use coordinator memory only.
class Coordinator:
    code = "RTEST"
    entity_prefix = "entry-test"
    restaurant_name = "Test"
    data = models.WeeklyMenu(
        "RTEST",
        "Test",
        "https://example.invalid",
        (
            day,
            models.DayMenu(
                date(2026, 9, 8),
                "Mardi 08/09",
                (models.MenuItem("Poulet rôti", models.MenuCategory.MAIN_COURSE),),
            ),
        ),
    )

entity = calendar.RadisLaToqueCalendar(Coordinator())
assert entity.event.start == date(2026, 9, 7)

import asyncio
async def _range_test():
    events = await entity.async_get_events(
        object(),
        datetime(2026, 9, 7, 0, 0, 0),
        datetime(2026, 9, 9, 0, 0, 0),
    )
    assert [e.start.isoformat() for e in events] == ["2026-09-07", "2026-09-08"]

asyncio.run(_range_test())
print("CALENDAR ENTITY RANGE: PASS")
