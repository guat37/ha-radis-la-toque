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
from .client.presentation import (
    day_to_dict,
    display_week,
    menu_category_text,
    menu_summary,
    menu_widget_text,
    week_start,
)
from .coordinator import RadisLaToqueCoordinator
from .entity import RadisLaToqueEntity

_WIDGET_STATE_MAX_LENGTH = 255
_EMPTY_CATEGORY_STATE = "—"


@dataclass(frozen=True, kw_only=True)
class RadisMenuSensorDescription(SensorEntityDescription):
    """Describe a single-day menu sensor."""

    menu_fn: Callable[[WeeklyMenu | None], DayMenu | None]


@dataclass(frozen=True, kw_only=True)
class RadisTodayCategorySensorDescription(SensorEntityDescription):
    """Describe one compact category from today's menu."""

    category: MenuCategory


def _today(data: WeeklyMenu | None) -> DayMenu | None:
    return data.menu_for_date(dt_util.now().date()) if data else None


def _next(data: WeeklyMenu | None) -> DayMenu | None:
    return data.next_menu_after(dt_util.now().date()) if data else None


def _truncate_state(value: str, max_length: int = _WIDGET_STATE_MAX_LENGTH) -> str:
    """Return a string guaranteed to fit in a Home Assistant entity state."""
    if len(value) <= max_length:
        return value
    if max_length <= 1:
        return value[:max_length]
    return value[: max_length - 1].rstrip() + "…"


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

TODAY_CATEGORY_SENSORS = (
    RadisTodayCategorySensorDescription(
        key="today_starter",
        translation_key="today_starter",
        icon="mdi:leaf",
        category=MenuCategory.STARTER,
    ),
    RadisTodayCategorySensorDescription(
        key="today_main_course",
        translation_key="today_main_course",
        icon="mdi:silverware-fork-knife",
        category=MenuCategory.MAIN_COURSE,
    ),
    RadisTodayCategorySensorDescription(
        key="today_dessert",
        translation_key="today_dessert",
        icon="mdi:cupcake",
        category=MenuCategory.DESSERT,
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
    entities.extend(
        RadisLaToqueTodayCategorySensor(entry.runtime_data, description)
        for description in TODAY_CATEGORY_SENSORS
    )
    entities.append(RadisLaToqueWidgetSensor(entry.runtime_data))
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


class RadisLaToqueTodayCategorySensor(RadisLaToqueEntity, SensorEntity):
    """Expose one compact category of today's menu for mobile widgets."""

    entity_description: RadisTodayCategorySensorDescription

    def __init__(
        self,
        coordinator: RadisLaToqueCoordinator,
        description: RadisTodayCategorySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entity_prefix}_{description.key}"

    @property
    def native_value(self) -> str | None:
        day = _today(self.coordinator.data)
        if day is None:
            return None
        value = menu_category_text(
            day,
            self.entity_description.category,
            max_length=_WIDGET_STATE_MAX_LENGTH,
        )
        return value or _EMPTY_CATEGORY_STATE

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        day = _today(self.coordinator.data)
        category = self.entity_description.category
        if day is None:
            return {
                "menu_available": False,
                "category": category.value,
                "choices": [],
            }
        choices = list(day.items_by_category(category))
        return {
            "menu_available": True,
            "category_available": bool(choices),
            "date": day.menu_date.isoformat(),
            "category": category.value,
            "choices": choices,
        }


class RadisLaToqueWidgetSensor(RadisLaToqueEntity, SensorEntity):
    """Expose today's menu in a mobile-friendly representation."""

    _attr_translation_key = "widget"
    _attr_icon = "mdi:silverware-fork-knife"

    def __init__(self, coordinator: RadisLaToqueCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entity_prefix}_widget"

    @property
    def native_value(self) -> str | None:
        day = _today(self.coordinator.data)
        if day is None:
            return None
        return _truncate_state(menu_summary(day))

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        day = _today(self.coordinator.data)
        if day is None:
            return {
                "menu_available": False,
                "widget_text": "",
                "items": [],
            }
        return {
            "menu_available": True,
            "widget_text": menu_widget_text(day),
            **day_to_dict(day),
        }


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
