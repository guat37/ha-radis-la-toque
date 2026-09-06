"""Diagnostics support for Radis la Toque."""
from __future__ import annotations
from typing import Any
from homeassistant.core import HomeAssistant
from . import RadisLaToqueConfigEntry

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: RadisLaToqueConfigEntry) -> dict[str, Any]:
    data = entry.runtime_data.data
    return {
        "config_entry": dict(entry.data),
        "last_update_success": entry.runtime_data.last_update_success,
        "menu": None if data is None else {
            "restaurant_code": data.restaurant_code,
            "source_url": data.source_url,
            "parser_kind": data.parser_kind,
            "parser_score": data.parser_score,
            "days": [
                {
                    "date": day.menu_date.isoformat(),
                    "item_count": len(day.items),
                    "categories": sorted({item.category.value for item in day.items}),
                }
                for day in data.days
            ],
            "etag_present": data.document_etag is not None,
            "last_modified_present": data.document_last_modified is not None,
        },
    }
