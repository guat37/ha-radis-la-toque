"""Base entities for Radis la Toque."""
from __future__ import annotations

from datetime import datetime

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RadisLaToqueCoordinator


class RadisLaToqueEntity(CoordinatorEntity[RadisLaToqueCoordinator]):
    """Base coordinator-backed entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RadisLaToqueCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entity_prefix)},
            name=coordinator.restaurant_name,
            manufacturer="RESTORIA / Radis la Toque",
            configuration_url=coordinator.restaurant_url,
        )


class RadisLaToqueDateAwareEntity(RadisLaToqueEntity):
    """Entity whose state depends on Home Assistant's current local date.

    Coordinator data can legitimately stay unchanged across midnight because a
    downloaded weekly menu already contains several days.  The displayed
    entity state still has to be recomputed when the local date changes.
    Register a local-midnight listener that only writes the state from the
    already-cached coordinator data; it does not perform any network I/O.
    """

    async def async_added_to_hass(self) -> None:
        """Subscribe to the local date rollover while the entity is loaded."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(
                self.hass,
                self._handle_local_midnight,
                hour=0,
                minute=0,
                second=0,
            )
        )

    @callback
    def _handle_local_midnight(self, _now: datetime) -> None:
        """Recompute the entity state from cached menu data at local midnight."""
        self.async_write_ha_state()
