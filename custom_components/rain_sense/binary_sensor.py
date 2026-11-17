"""Mirrored binary sensors (e.g. rain detected)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import MirrorEntity, setup_mirrors


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    setup_mirrors(entry, async_add_entities, "binary_sensor", MirrorBinarySensor)


class MirrorBinarySensor(MirrorEntity, BinarySensorEntity):
    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        try:
            return BinarySensorDeviceClass(self.item["device_class"])
        except ValueError:
            return None

    @property
    def is_on(self) -> bool:
        return self.item["state"] == "on"
