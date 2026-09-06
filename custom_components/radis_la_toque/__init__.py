"""Radis la Toque Home Assistant integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import RadisLaToqueClient, RestaurantNotFound, restaurant_id_from_url
from .const import (
    CONF_ENTITY_PREFIX,
    CONF_RESTAURANT_CODE,
    CONF_RESTAURANT_ID,
    CONF_RESTAURANT_URL,
    PLATFORMS,
)
from .coordinator import RadisLaToqueCoordinator
from .frontend import async_register_frontend

_LOGGER = logging.getLogger(__name__)

type RadisLaToqueConfigEntry = ConfigEntry[RadisLaToqueCoordinator]


async def async_migrate_entry(
    hass: HomeAssistant, entry: RadisLaToqueConfigEntry
) -> bool:
    """Migrate v1 entries from volatile Rxxxxx identity to stable fiche identity."""
    if entry.version > 2:
        return False

    if entry.version == 1:
        try:
            restaurant_id = restaurant_id_from_url(
                str(entry.data[CONF_RESTAURANT_URL])
            )
        except (KeyError, RestaurantNotFound):
            _LOGGER.error(
                "Cannot migrate Radis la Toque entry %s: stable fiche id missing",
                entry.entry_id,
            )
            return False

        old_code = str(entry.data[CONF_RESTAURANT_CODE])
        new_data = {
            **entry.data,
            CONF_RESTAURANT_ID: restaurant_id,
            # Keep the old prefix forever for existing entries so entity and
            # device registry identifiers do not change during migration.
            CONF_ENTITY_PREFIX: old_code,
        }
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            unique_id=restaurant_id,
            version=2,
        )
        _LOGGER.info(
            "Migrated Radis la Toque entry %s from %s to stable id %s",
            entry.entry_id,
            old_code,
            restaurant_id,
        )

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: RadisLaToqueConfigEntry
) -> bool:
    """Set up one restaurant."""
    await async_register_frontend(hass)
    client = RadisLaToqueClient(async_get_clientsession(hass))
    coordinator = RadisLaToqueCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: RadisLaToqueConfigEntry
) -> bool:
    """Unload one restaurant."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
