"""DataUpdateCoordinator for Radis la Toque."""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from .client import CannotConnect, InvalidPdf, MenuNotAvailable, MenuParseError, RadisLaToqueClient, WeeklyMenu
from .const import CONF_RESTAURANT_CODE, CONF_RESTAURANT_NAME, DEFAULT_UPDATE_INTERVAL, DOMAIN

class RadisLaToqueCoordinator(DataUpdateCoordinator[WeeklyMenu | None]):
    """Coordinate one shared menu fetch for all entities."""
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: RadisLaToqueClient) -> None:
        super().__init__(hass, logger=__import__('logging').getLogger(__name__), name=DOMAIN, update_interval=DEFAULT_UPDATE_INTERVAL, always_update=False)
        self.client = client
        self.code = str(entry.data[CONF_RESTAURANT_CODE])
        self.restaurant_name = str(entry.data[CONF_RESTAURANT_NAME])

    async def _async_update_data(self) -> WeeklyMenu | None:
        try:
            return await self.client.async_get_menu(self.code, self.restaurant_name, today=dt_util.now().date())
        except MenuNotAvailable:
            # A missing menu is a valid service state (holidays / no publication).
            return None
        except (CannotConnect, InvalidPdf, MenuParseError) as err:
            raise UpdateFailed(str(err)) from err
