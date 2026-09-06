"""Constants for Radis la Toque."""
from datetime import timedelta

DOMAIN = "radis_la_toque"
PLATFORMS = ["sensor", "calendar"]

CONF_RESTAURANT_CODE = "restaurant_code"
CONF_RESTAURANT_NAME = "restaurant_name"
CONF_RESTAURANT_URL = "restaurant_url"
CONF_RESTAURANT_CITY = "restaurant_city"
CONF_RESTAURANT_POSTAL_CODE = "restaurant_postal_code"
CONF_SEARCH = "search"
CONF_RESTAURANT = "restaurant"

BASE_URL = "https://www.radislatoque.fr"
LIST_URL = f"{BASE_URL}/les-menus-de-la-cantine/liste-des-restaurants"
RESTAURANT_URL = f"{BASE_URL}/restaurants/{{code}}"
PDF_URL = f"{BASE_URL}/action-DownloadPDF-{{code}}"
DEFAULT_UPDATE_INTERVAL = timedelta(hours=12)
REQUEST_TIMEOUT = 20
MAX_CATALOG_PAGES = 120
CATALOG_CONCURRENCY = 8
INTEGRATION_VERSION = "0.4.0-beta.1"
FRONTEND_URL_BASE = "/radis_la_toque"
FRONTEND_CARD_FILENAME = "radis-la-toque-card.js"
USER_AGENT = (
    f"HomeAssistant-RadisLaToque/{INTEGRATION_VERSION} "
    "(+https://github.com/guat37/ha-radis-la-toque)"
)
