"""Config flow for Radis la Toque."""
from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .client import CannotConnect, RadisLaToqueClient, Restaurant, RestaurantNotFound
from .const import CONF_RESTAURANT, CONF_RESTAURANT_CITY, CONF_RESTAURANT_CODE, CONF_RESTAURANT_NAME, CONF_RESTAURANT_POSTAL_CODE, CONF_RESTAURANT_URL, CONF_SEARCH, DOMAIN

class RadisLaToqueConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    def __init__(self) -> None:
        self._restaurants: dict[str, Restaurant] = {}
        self._client: RadisLaToqueClient | None = None

    @property
    def client(self) -> RadisLaToqueClient:
        if self._client is None:
            self._client = RadisLaToqueClient(async_get_clientsession(self.hass))
        return self._client

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                restaurants = await self.client.async_find_restaurants(str(user_input[CONF_SEARCH]).strip())
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except RestaurantNotFound:
                errors["base"] = "cannot_parse"
            else:
                if not restaurants:
                    errors["base"] = "no_restaurants"
                else:
                    self._restaurants = {restaurant.page_url: restaurant for restaurant in restaurants}
                    return await self.async_step_restaurant()
        return self.async_show_form(step_id="user", data_schema=vol.Schema({vol.Required(CONF_SEARCH): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT))}), errors=errors)

    async def async_step_restaurant(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            restaurant = self._restaurants.get(str(user_input[CONF_RESTAURANT]))
            if restaurant is None:
                return self.async_abort(reason="invalid_restaurant")
            try:
                resolved = await self.client.async_resolve_restaurant(restaurant)
                assert resolved.code is not None
                await self.client.async_validate_restaurant(resolved.code)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except RestaurantNotFound:
                errors["base"] = "cannot_parse"
            else:
                await self.async_set_unique_id(resolved.code)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=resolved.label, data={CONF_RESTAURANT_CODE: resolved.code, CONF_RESTAURANT_NAME: resolved.name, CONF_RESTAURANT_URL: resolved.page_url, CONF_RESTAURANT_CITY: resolved.city, CONF_RESTAURANT_POSTAL_CODE: resolved.postal_code})
        options = [selector.SelectOptionDict(value=url, label=restaurant.label) for url, restaurant in self._restaurants.items()]
        return self.async_show_form(step_id="restaurant", data_schema=vol.Schema({vol.Required(CONF_RESTAURANT): selector.SelectSelector(selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN, sort=True))}), errors=errors)
