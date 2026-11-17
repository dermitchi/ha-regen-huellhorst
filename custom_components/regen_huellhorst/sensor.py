"""Mirrored sensors (e.g. battery, light level, rain amount)."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass

from .entity import MirrorEntity, setup_mirrors


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    setup_mirrors(entry, async_add_entities, "sensor", MirrorSensor)


class MirrorSensor(MirrorEntity, SensorEntity):
    @property
    def device_class(self) -> SensorDeviceClass | None:
        try:
            return SensorDeviceClass(self.item["device_class"])
        except ValueError:
            return None

    @property
    def state_class(self) -> SensorStateClass | None:
        try:
            return SensorStateClass(self.item["state_class"])
        except ValueError:
            return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.item["unit"]

    @property
    def native_value(self) -> str:
        return self.item["state"]  # HA parses numeric strings itself for sensors with a unit/class
