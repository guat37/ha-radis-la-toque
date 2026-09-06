"""DataUpdateCoordinator for Radis la Toque."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .client import (
    CannotConnect,
    InvalidPdf,
    MenuNotAvailable,
    MenuParseError,
    RadisLaToqueClient,
    RestaurantNotFound,
    WeeklyMenu,
)
from .const import (
    CONF_ENTITY_PREFIX,
    CONF_RESTAURANT_CODE,
    CONF_RESTAURANT_ID,
    CONF_RESTAURANT_NAME,
    CONF_RESTAURANT_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class RadisLaToqueCoordinator(DataUpdateCoordinator[WeeklyMenu | None]):
    """Coordinate one shared menu fetch for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: RadisLaToqueClient,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_UPDATE_INTERVAL,
            always_update=False,
        )
        self.entry = entry
        self.client = client
        self.code = str(entry.data[CONF_RESTAURANT_CODE])
        self.restaurant_id = str(entry.data[CONF_RESTAURANT_ID])
        self.entity_prefix = str(entry.data[CONF_ENTITY_PREFIX])
        self.restaurant_name = str(entry.data[CONF_RESTAURANT_NAME])
        self.restaurant_url = str(entry.data[CONF_RESTAURANT_URL])

    async def _async_resolve_current_code(self) -> str:
        """Resolve and persist the current volatile Rxxxxx code.

        RESTORIA rotates menu codes independently of the stable restaurant
        fiche.  Resolve from the fiche on every coordinator cycle so existing
        entries self-heal without delete/recreate.
        """
        try:
            current_code = await self.client.async_resolve_code(self.restaurant_url)
        except RestaurantNotFound:
            # Preserve service if the fiche HTML changes temporarily but the
            # last known PDF endpoint is still usable.
            _LOGGER.warning(
                "Unable to resolve current Radis la Toque code for %s; using last known %s",
                self.restaurant_id,
                self.code,
            )
            return self.code

        if current_code != self.code:
            old_code = self.code
            self.code = current_code
            new_data = {**self.entry.data, CONF_RESTAURANT_CODE: current_code}
            self.hass.config_entries.async_update_entry(self.entry, data=new_data)
            _LOGGER.info(
                "Radis la Toque menu code changed for %s: %s -> %s",
                self.restaurant_id,
                old_code,
                current_code,
            )
        return self.code

    async def _async_update_data(self) -> WeeklyMenu | None:
        try:
            code = await self._async_resolve_current_code()
            return await self.client.async_get_menu(
                code,
                self.restaurant_name,
                today=dt_util.now().date(),
            )
        except MenuNotAvailable:
            # A missing menu is a valid service state (holidays / no publication).
            return None
        except (CannotConnect, InvalidPdf, MenuParseError) as err:
            raise UpdateFailed(str(err)) from err
