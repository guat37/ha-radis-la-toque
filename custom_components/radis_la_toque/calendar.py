"""Calendar platform for Radis la Toque menus."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import RadisLaToqueConfigEntry
from .client import DayMenu
from .client.presentation import menu_description, menu_summary
from .coordinator import RadisLaToqueCoordinator
from .entity import RadisLaToqueEntity


def _as_event(day: DayMenu) -> CalendarEvent:
    """Convert one immutable menu day to an all-day calendar event."""
    return CalendarEvent(
        start=day.menu_date,
        end=day.menu_date + timedelta(days=1),
        summary=menu_summary(day),
        description=menu_description(day),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RadisLaToqueConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the read-only canteen calendar."""
    async_add_entities([RadisLaToqueCalendar(entry.runtime_data)])


class RadisLaToqueCalendar(RadisLaToqueEntity, CalendarEntity):
    """Read-only calendar backed by the downloaded school menu."""

    _attr_translation_key = "menus"
    _attr_icon = "mdi:food-apple-outline"

    def __init__(self, coordinator: RadisLaToqueCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.code}_calendar"

    @property
    def event(self) -> CalendarEvent | None:
        """Return today's event or the next upcoming event from memory."""
        data = self.coordinator.data
        if data is None:
            return None
        today = dt_util.now().date()
        day = data.menu_for_date(today) or data.next_menu_after(today)
        return _as_event(day) if day else None

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return all menu events overlapping the requested range."""
        data = self.coordinator.data
        if data is None:
            return []
        start_day = start_date.date()
        end_day = end_date.date()
        return [
            _as_event(day)
            for day in data.days
            if day.menu_date < end_day and day.menu_date + timedelta(days=1) > start_day
        ]
