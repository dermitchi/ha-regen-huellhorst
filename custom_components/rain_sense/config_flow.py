"""Config flow: a sender (choose entities, get a link) or a receiver (paste the link)."""

from __future__ import annotations

import secrets
from typing import Any

import voluptuous as vol
from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .const import CONF_ENTITIES, CONF_KEY, CONF_MODE, CONF_URL, DOMAIN, MODE_RECEIVE, MODE_SEND, SHARE_DOMAINS, URL_PATH

ENTITIES_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITIES): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=SHARE_DOMAINS, multiple=True)
        )
    }
)


class RainSenseConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return RainSenseOptionsFlow()

    @classmethod
    @callback
    def async_supports_options_flow(cls, config_entry: ConfigEntry) -> bool:
        return config_entry.data[CONF_MODE] == MODE_SEND

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=[MODE_SEND, MODE_RECEIVE])

    async def async_step_send(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._entities = user_input[CONF_ENTITIES]
            self._key = secrets.token_urlsafe(24)
            return await self.async_step_link()
        return self.async_show_form(step_id="send", data_schema=ENTITIES_SCHEMA)

    async def async_step_link(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="Rain Sense (sharing)",
                data={CONF_MODE: MODE_SEND, CONF_KEY: self._key},
                options={CONF_ENTITIES: self._entities},
            )
        try:
            host = get_url(self.hass, prefer_external=True)
        except NoURLAvailableError:
            host = "<your Home Assistant address>"
        return self.async_show_form(
            step_id="link", description_placeholders={"link": f"{host}{URL_PATH}/{self._key}"}
        )

    async def async_step_receive(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip()
            try:
                async with async_get_clientsession(self.hass).get(url, timeout=10) as resp:
                    resp.raise_for_status()
                    name = (await resp.json())["name"]
            except (ClientError, TimeoutError, ValueError, KeyError, TypeError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=name, data={CONF_MODE: MODE_RECEIVE, CONF_URL: url})
        return self.async_show_form(
            step_id="receive", data_schema=vol.Schema({vol.Required(CONF_URL): str}), errors=errors
        )


class RainSenseOptionsFlow(OptionsFlow):
    """Sender only: change which entities are shared (takes effect on the next request)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(ENTITIES_SCHEMA, self.config_entry.options),
        )
