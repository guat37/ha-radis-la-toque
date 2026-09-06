"""Frontend support for Radis la Toque."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    FRONTEND_CARD_FILENAME,
    FRONTEND_URL_BASE,
    INTEGRATION_VERSION,
)

_LOGGER = logging.getLogger(__name__)
_DATA_FRONTEND_REGISTERED = "frontend_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve and globally load the bundled Lovelace card.

    A HACS integration repository does not automatically create a Lovelace
    resource for JavaScript bundled inside ``custom_components``.  Loading the
    versioned module through Home Assistant's frontend API makes
    ``custom:radis-la-toque-card`` available after installation without a
    manual Resources entry.
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(_DATA_FRONTEND_REGISTERED):
        return

    static_file = Path(__file__).parent / "www" / FRONTEND_CARD_FILENAME
    card_url = f"{FRONTEND_URL_BASE}/{FRONTEND_CARD_FILENAME}"
    versioned_url = f"{card_url}?v={INTEGRATION_VERSION}"

    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(card_url, str(static_file), False)]
        )
    except RuntimeError:
        _LOGGER.debug("Frontend path %s is already registered", card_url)
    except Exception:  # pragma: no cover - frontend must never break data setup
        _LOGGER.exception("Unable to register the Radis la Toque frontend path")
        return

    add_extra_js_url(hass, versioned_url)
    domain_data[_DATA_FRONTEND_REGISTERED] = True
    _LOGGER.debug("Registered Radis la Toque frontend module %s", versioned_url)
