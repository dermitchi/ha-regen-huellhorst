"""Regen Hüllhorst – live rain data from Hüllhorst, no setup needed."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import ClientError, ClientTimeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import NAME, NTFY_URL, SCAN_INTERVAL
from .feed import newest

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]
RETRY_S = 30

type RegenConfigEntry = ConfigEntry[DataUpdateCoordinator[dict[str, Any]]]


def bodies(lines: list[bytes]) -> list[str]:
    """Message texts out of ntfy's JSON lines (keepalives and open events have no message)."""
    out = []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("event") == "message" and isinstance(event.get("message"), str):
            out.append(event["message"])
    return out


async def async_setup_entry(hass: HomeAssistant, entry: RegenConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    async def poll() -> dict[str, Any]:
        """Everything the topic still has from the last hour; keeps the newest valid message."""
        try:
            async with session.get(
                NTFY_URL, params={"poll": "1", "since": "1h"}, allow_redirects=False, timeout=ClientTimeout(total=15)
            ) as resp:
                resp.raise_for_status()
                lines = (await resp.content.read(256 * 1024)).splitlines()
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(err) from err
        if (data := newest(bodies(lines), coordinator.data)) is None:
            raise UpdateFailed("no valid message from Hüllhorst in the last 30 minutes")
        return data

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, config_entry=entry, name=NAME, update_method=poll, update_interval=SCAN_INTERVAL
    )
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()

    async def stream() -> None:
        """Open connection: ntfy delivers new messages within a second."""
        while True:
            try:
                async with session.get(
                    NTFY_URL, params={"since": "10s"}, allow_redirects=False, timeout=ClientTimeout(total=None, sock_read=120)
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.content:  # keepalives every 45 s keep sock_read from firing
                        if data := newest(bodies([line]), coordinator.data):
                            if data is not coordinator.data:
                                coordinator.async_set_updated_data(data)
            except (ClientError, TimeoutError, ValueError) as err:
                _LOGGER.debug("Stream interrupted: %s", err)
            await asyncio.sleep(RETRY_S)

    entry.async_create_background_task(hass, stream(), f"{NAME} stream")
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RegenConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
