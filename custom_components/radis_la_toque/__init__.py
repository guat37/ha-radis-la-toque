"""Radis la Toque Home Assistant integration."""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .client import RadisLaToqueClient
from .const import PLATFORMS
from .coordinator import RadisLaToqueCoordinator
from .frontend import async_register_frontend

type RadisLaToqueConfigEntry = ConfigEntry[RadisLaToqueCoordinator]

async def async_setup_entry(hass: HomeAssistant, entry: RadisLaToqueConfigEntry) -> bool:
    await async_register_frontend(hass)
    client = RadisLaToqueClient(async_get_clientsession(hass))
    coordinator = RadisLaToqueCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: RadisLaToqueConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
