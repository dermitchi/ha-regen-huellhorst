"""Feed → entities, staleness and the one-click config flow."""

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.regen_huellhorst.const import DOMAIN, FEED_URL, SCAN_INTERVAL, STALE_AFTER

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def feed(rain="on", battery="87", updated=None):
    return {
        "name": "Regen Hüllhorst",
        "updated": (updated or dt_util.utcnow()).isoformat(),
        "entities": {
            "binary_sensor.regen": {"state": rain, "name": "Regen", "device_class": "moisture", "unit": None, "state_class": None},
            "sensor.batterie": {"state": battery, "name": "Batterie", "device_class": "battery", "unit": "%", "state_class": "measurement"},
        },
    }


async def setup(hass: HomeAssistant, aioclient_mock, payload=None, **kw) -> MockConfigEntry:
    aioclient_mock.get(FEED_URL, json=payload or feed(), **kw)
    entry = MockConfigEntry(domain=DOMAIN, title="Regen Hüllhorst", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def get(hass, domain, entry, key):
    eid = er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{key}")
    return hass.states.get(eid)


async def refresh(hass, aioclient_mock, **kw) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, **kw)
    async_fire_time_changed(hass, dt_util.utcnow() + SCAN_INTERVAL + timedelta(seconds=1))
    await hass.async_block_till_done()


async def test_entities_follow_the_feed(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup(hass, aioclient_mock)
    rain = get(hass, "binary_sensor", entry, "binary_sensor.regen")
    assert rain.state == "on" and rain.attributes["device_class"] == "moisture"
    battery = get(hass, "sensor", entry, "sensor.batterie")
    assert battery.state == "87" and battery.attributes["unit_of_measurement"] == "%"

    await refresh(hass, aioclient_mock, json=feed(rain="off", battery="86"))
    assert get(hass, "binary_sensor", entry, "binary_sensor.regen").state == "off"
    assert get(hass, "sensor", entry, "sensor.batterie").state == "86"


async def test_new_entity_in_feed_appears(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup(hass, aioclient_mock)
    payload = feed()
    payload["entities"]["sensor.helligkeit"] = {"state": "300", "name": "Helligkeit", "device_class": "illuminance", "unit": "lx", "state_class": "measurement"}
    await refresh(hass, aioclient_mock, json=payload)
    assert get(hass, "sensor", entry, "sensor.helligkeit").state == "300"


async def test_old_feed_is_unavailable(hass: HomeAssistant, aioclient_mock) -> None:
    old = dt_util.utcnow() - STALE_AFTER - timedelta(minutes=1)
    entry = await setup(hass, aioclient_mock, feed(updated=old))
    assert get(hass, "binary_sensor", entry, "binary_sensor.regen").state == "unavailable"


async def test_unreachable_feed_is_unavailable(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup(hass, aioclient_mock)
    await refresh(hass, aioclient_mock, status=500)
    assert get(hass, "binary_sensor", entry, "binary_sensor.regen").state == "unavailable"


async def test_wrong_shape_does_not_set_up(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FEED_URL, json=["not", "a", "feed"])
    entry = MockConfigEntry(domain=DOMAIN, title="Regen Hüllhorst", data={})
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)


async def test_flow_is_one_click_and_single(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(FEED_URL, json=feed())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["title"] == "Regen Hüllhorst"
    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert again["type"] is FlowResultType.ABORT
