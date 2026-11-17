"""Regen Hüllhorst – live rain data from Hüllhorst, no setup needed."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import FEED_URL, NAME, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

type RegenConfigEntry = ConfigEntry[DataUpdateCoordinator[dict[str, Any]]]


async def async_setup_entry(hass: HomeAssistant, entry: RegenConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    async def fetch() -> dict[str, Any]:
        try:
            async with session.get(FEED_URL, timeout=10) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)  # gist raw serves text/plain
            if not (isinstance(data, dict) and isinstance(data.get("entities"), dict) and "updated" in data):
                raise ValueError("unexpected feed shape")
            return data
        except (ClientError, TimeoutError, ValueError, KeyError, TypeError) as err:
            raise UpdateFailed(err) from err

    entry.runtime_data = DataUpdateCoordinator(
        hass, _LOGGER, config_entry=entry, name=NAME, update_method=fetch, update_interval=SCAN_INTERVAL
    )
    await entry.runtime_data.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RegenConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
