"""Menu sensors for Radis la Toque."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import RadisLaToqueConfigEntry
from .client import DayMenu, MenuCategory, WeeklyMenu
from .client.presentation import day_to_dict, display_week, week_start
from .coordinator import RadisLaToqueCoordinator
from .entity import RadisLaToqueEntity


@dataclass(frozen=True, kw_only=True)
class RadisMenuSensorDescription(SensorEntityDescription):
    """Describe a single-day menu sensor."""

    menu_fn: Callable[[WeeklyMenu | None], DayMenu | None]


def _today(data: WeeklyMenu | None) -> DayMenu | None:
    return data.menu_for_date(dt_util.now().date()) if data else None


def _next(data: WeeklyMenu | None) -> DayMenu | None:
    return data.next_menu_after(dt_util.now().date()) if data else None


SENSORS = (
    RadisMenuSensorDescription(
        key="today",
        translation_key="today",
        icon="mdi:silverware-fork-knife",
        device_class=SensorDeviceClass.DATE,
        menu_fn=_today,
    ),
    RadisMenuSensorDescription(
        key="next",
        translation_key="next",
        icon="mdi:calendar-arrow-right",
        device_class=SensorDeviceClass.DATE,
        menu_fn=_next,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RadisLaToqueConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Radis la Toque sensors."""
    entities: list[SensorEntity] = [
        RadisLaToqueMenuSensor(entry.runtime_data, description) for description in SENSORS
    ]
    entities.append(RadisLaToqueWeekSensor(entry.runtime_data))
    async_add_entities(entities)


class RadisLaToqueMenuSensor(RadisLaToqueEntity, SensorEntity):
    """A sensor representing one menu day."""

    entity_description: RadisMenuSensorDescription

    def __init__(
        self,
        coordinator: RadisLaToqueCoordinator,
        description: RadisMenuSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entity_prefix}_{description.key}"

    @property
    def native_value(self) -> date | None:
        day = self.entity_description.menu_fn(self.coordinator.data)
        return day.menu_date if day else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        day = self.entity_description.menu_fn(self.coordinator.data)
        if day is None:
            return {"menu_available": False, "items": []}
        return {"menu_available": True, **day_to_dict(day)}


class RadisLaToqueWeekSensor(RadisLaToqueEntity, SensorEntity):
    """Expose the current or next useful school week in one entity."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_translation_key = "week"
    _attr_icon = "mdi:calendar-week"

    def __init__(self, coordinator: RadisLaToqueCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entity_prefix}_week"

    @property
    def native_value(self) -> date | None:
        return week_start(self.coordinator.data, dt_util.now().date())

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        today = dt_util.now().date()
        days = display_week(self.coordinator.data, today)
        start = week_start(self.coordinator.data, today)
        if not days or start is None:
            return {"menu_available": False, "days": []}
        return {
            "menu_available": True,
            "week_start": start.isoformat(),
            "week_end": (start + timedelta(days=6)).isoformat(),
            "days": [day_to_dict(day) for day in days],
        }
