"""Mirrored entities: one per entity the sender shares."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN, NAME, STALE_AFTER


class MirrorEntity(CoordinatorEntity[DataUpdateCoordinator[dict[str, Any]]]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry, remote_id: str) -> None:
        super().__init__(coordinator)
        self.remote_id = remote_id
        self._attr_unique_id = f"{entry.entry_id}_{remote_id}"
        self._attr_name = self.item["name"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=NAME
        )

    @property
    def item(self) -> dict[str, Any]:
        return self.coordinator.data["entities"][self.remote_id]

    @property
    def _fresh(self) -> bool:
        updated = dt_util.parse_datetime(self.coordinator.data["updated"])
        return updated is not None and dt_util.utcnow() - updated < STALE_AFTER

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.remote_id in self.coordinator.data["entities"]
            and self._fresh
            and self.item["state"] not in ("unavailable", "unknown")
        )


def setup_mirrors(entry: ConfigEntry, add: AddConfigEntryEntitiesCallback, domain: str, cls: type[MirrorEntity]) -> None:
    """Add entities of one domain now and whenever the sender starts sharing new ones."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def add_new() -> None:
        new = [
            cls(coordinator, entry, rid)
            for rid in coordinator.data["entities"]
            if rid.split(".")[0] == domain and rid not in known
        ]
        known.update(e.remote_id for e in new)
        add(new)

    add_new()
    entry.async_on_unload(coordinator.async_add_listener(add_new))
