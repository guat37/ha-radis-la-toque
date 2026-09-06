"""Frontend support for Radis la Toque.

The Lovelace card is shipped inside the integration so HACS installs a single
self-contained package.  We only expose the JavaScript through Home
Assistant's supported static-path API; users register the Lovelace resource
explicitly, which keeps dashboard configuration under user control.
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, FRONTEND_CARD_FILENAME, FRONTEND_URL_BASE

_LOGGER = logging.getLogger(__name__)
_DATA_FRONTEND_REGISTERED = "frontend_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Expose the bundled Lovelace card through a local HTTP path."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_DATA_FRONTEND_REGISTERED):
        return

    static_file = Path(__file__).parent / "www" / FRONTEND_CARD_FILENAME
    card_url = f"{FRONTEND_URL_BASE}/{FRONTEND_CARD_FILENAME}"
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(card_url, str(static_file), True)]
        )
    except RuntimeError:
        # A reload can encounter the path registered by the previous entry.
        _LOGGER.debug("Frontend path %s is already registered", card_url)
    except Exception:  # pragma: no cover - frontend must never break data setup
        _LOGGER.exception("Unable to register the Radis la Toque frontend path")
        return

    domain_data[_DATA_FRONTEND_REGISTERED] = True
