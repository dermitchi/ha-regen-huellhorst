"""Rain Sense – mirror a rain sensor (or any binary_sensor/sensor) from one Home Assistant to another."""

from __future__ import annotations

import hmac
import logging
from typing import Any

from aiohttp import ClientError, web
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_ENTITIES, CONF_KEY, CONF_MODE, CONF_URL, DOMAIN, MODE_SEND, SCAN_INTERVAL, URL_PATH

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

type RainSenseConfigEntry = ConfigEntry[DataUpdateCoordinator[dict[str, Any]] | None]


def snapshot(hass: HomeAssistant, entity_ids: list[str]) -> dict[str, Any]:
    """What the sender publishes: state plus the few attributes the receiver needs."""
    items = {}
    for entity_id in entity_ids:
        if (state := hass.states.get(entity_id)) is None:
            continue
        a = state.attributes
        items[entity_id] = {
            "state": state.state,
            "name": a.get("friendly_name", entity_id),
            "device_class": a.get("device_class"),
            "unit": a.get("unit_of_measurement"),
            "state_class": a.get("state_class"),
        }
    return {"name": hass.config.location_name, "entities": items}


class ShareView(HomeAssistantView):
    """Read-only link; the secret key in the path is the only credential."""

    url = URL_PATH + "/{key}"
    name = "api:rain_sense"
    requires_auth = False

    async def get(self, request: web.Request, key: str) -> web.Response:
        hass = request.app["hass"]
        for entry in hass.config_entries.async_entries(DOMAIN):
            if (
                entry.state is ConfigEntryState.LOADED
                and entry.data[CONF_MODE] == MODE_SEND
                and hmac.compare_digest(entry.data[CONF_KEY], key)
            ):
                return self.json(snapshot(hass, entry.options[CONF_ENTITIES]))
        return web.Response(status=404)


async def async_setup_entry(hass: HomeAssistant, entry: RainSenseConfigEntry) -> bool:
    entry.runtime_data = None
    if entry.data[CONF_MODE] == MODE_SEND:
        if not hass.data.get(DOMAIN):  # the view is registered once for all sender entries
            hass.http.register_view(ShareView())
            hass.data[DOMAIN] = True
        return True

    session = async_get_clientsession(hass)

    async def fetch() -> dict[str, Any]:
        try:
            async with session.get(entry.data[CONF_URL], timeout=10) as resp:
                resp.raise_for_status()
                return await resp.json()
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(err) from err

    entry.runtime_data = DataUpdateCoordinator(
        hass, _LOGGER, config_entry=entry, name=entry.title, update_method=fetch, update_interval=SCAN_INTERVAL
    )
    await entry.runtime_data.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RainSenseConfigEntry) -> bool:
    if entry.data[CONF_MODE] == MODE_SEND:
        return True
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
