"""Diagnostics support for Radis la Toque."""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import RadisLaToqueConfigEntry
from .const import (
    CONF_ENTITY_PREFIX,
    CONF_RESTAURANT_CITY,
    CONF_RESTAURANT_CODE,
    CONF_RESTAURANT_ID,
    CONF_RESTAURANT_NAME,
    CONF_RESTAURANT_POSTAL_CODE,
    CONF_RESTAURANT_URL,
)


def _isoformat(value: Any) -> str | None:
    """Return an ISO timestamp when available."""
    return value.isoformat() if value is not None else None


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: RadisLaToqueConfigEntry,
) -> dict[str, Any]:
    """Return useful, non-sensitive diagnostics for one canteen."""
    coordinator = entry.runtime_data
    data = coordinator.data

    return {
        "config_entry": {
            "restaurant_id": entry.data.get(CONF_RESTAURANT_ID),
            "restaurant_code": entry.data.get(CONF_RESTAURANT_CODE),
            "entity_prefix": entry.data.get(CONF_ENTITY_PREFIX),
            "restaurant_name": entry.data.get(CONF_RESTAURANT_NAME),
            "restaurant_city": entry.data.get(CONF_RESTAURANT_CITY),
            "restaurant_postal_code": entry.data.get(CONF_RESTAURANT_POSTAL_CODE),
            "restaurant_url": entry.data.get(CONF_RESTAURANT_URL),
        },
        "last_update_success": coordinator.last_update_success,
        "last_attempt": _isoformat(coordinator.last_attempt),
        "last_successful_update": _isoformat(coordinator.last_successful_update),
        "last_result": coordinator.last_result,
        "menu": (
            None
            if data is None
            else {
                "restaurant_code": data.restaurant_code,
                "source_url": data.source_url,
                "parser_kind": data.parser_kind,
                "parser_score": data.parser_score,
                "day_count": len(data.days),
                "days": [
                    {
                        "date": day.menu_date.isoformat(),
                        "item_count": len(day.items),
                        "categories": sorted(
                            {item.category.value for item in day.items}
                        ),
                    }
                    for day in data.days
                ],
                "etag_present": data.document_etag is not None,
                "last_modified_present": data.document_last_modified is not None,
            }
        ),
    }
