"""Sender link, receiver entities and the config flows."""

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.rain_sense.const import DOMAIN, SCAN_INTERVAL

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

LINK = "http://friend.example/api/rain_sense/secret"
PAYLOAD = {
    "name": "Michel",
    "entities": {
        "binary_sensor.rain": {"state": "on", "name": "Rain", "device_class": "moisture", "unit": None, "state_class": None},
        "sensor.rain_battery": {"state": "87", "name": "Rain battery", "device_class": "battery", "unit": "%", "state_class": "measurement"},
    },
}


async def setup_sender(hass: HomeAssistant, entities: list[str]) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={"mode": "send", "key": "secret"}, options={"entities": entities})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_sender_serves_only_chosen_entities(hass, hass_client_no_auth) -> None:
    hass.states.async_set("binary_sensor.rain", "on", {"device_class": "moisture", "friendly_name": "Rain"})
    hass.states.async_set("sensor.secret", "1")
    await setup_sender(hass, ["binary_sensor.rain", "sensor.missing"])
    client = await hass_client_no_auth()

    resp = await client.get("/api/rain_sense/secret")
    assert resp.status == 200
    data = await resp.json()
    assert list(data["entities"]) == ["binary_sensor.rain"]  # not the unshared one, not the missing one
    assert data["entities"]["binary_sensor.rain"]["state"] == "on"
    assert (await client.get("/api/rain_sense/wrong")).status == 404


async def test_receiver_mirrors_and_adds_new_entities(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(LINK, json={"name": "Michel", "entities": {"binary_sensor.rain": PAYLOAD["entities"]["binary_sensor.rain"]}})
    entry = MockConfigEntry(domain=DOMAIN, title="Michel", data={"mode": "receive", "url": LINK})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    reg = er.async_get(hass)
    rain = reg.async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_binary_sensor.rain")
    assert hass.states.get(rain).state == "on"
    assert hass.states.get(rain).attributes["device_class"] == "moisture"

    aioclient_mock.clear_requests()
    aioclient_mock.get(LINK, json=PAYLOAD | {"entities": {**PAYLOAD["entities"], "binary_sensor.rain": {**PAYLOAD["entities"]["binary_sensor.rain"], "state": "off"}}})
    async_fire_time_changed(hass, dt_util.utcnow() + SCAN_INTERVAL + timedelta(seconds=1))
    await hass.async_block_till_done()

    assert hass.states.get(rain).state == "off"
    battery = reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_sensor.rain_battery")
    state = hass.states.get(battery)
    assert state.state == "87" and state.attributes["unit_of_measurement"] == "%"
    assert state.attributes["device_class"] == "battery"


async def test_receiver_unavailable_when_sender_unreachable(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(LINK, json=PAYLOAD)
    entry = MockConfigEntry(domain=DOMAIN, title="Michel", data={"mode": "receive", "url": LINK})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    rain = er.async_get(hass).async_get_entity_id("binary_sensor", DOMAIN, f"{entry.entry_id}_binary_sensor.rain")

    aioclient_mock.clear_requests()
    aioclient_mock.get(LINK, status=500)
    async_fire_time_changed(hass, dt_util.utcnow() + SCAN_INTERVAL + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert hass.states.get(rain).state == "unavailable"


async def test_receive_flow(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(LINK, json=PAYLOAD)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "receive"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": LINK})
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["title"] == "Michel"
    assert result["data"] == {"mode": "receive", "url": LINK}


async def test_receive_flow_bad_link(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(LINK, status=404)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "receive"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"url": LINK})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "cannot_connect"}


async def test_send_flow_shows_link_and_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "send"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"entities": ["binary_sensor.rain"]})
    assert result["step_id"] == "link"
    assert "/api/rain_sense/" in result["description_placeholders"]["link"]
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {"entities": ["binary_sensor.rain"]} and len(result["data"]["key"]) >= 30
