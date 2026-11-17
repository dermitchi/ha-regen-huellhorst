"""ntfy topic → entities, staleness, forged messages and the one-click config flow."""

import base64
import json
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

import custom_components.regen_huellhorst.feed as feed
from custom_components.regen_huellhorst import bodies
from custom_components.regen_huellhorst.const import DOMAIN, NTFY_URL, SCAN_INTERVAL, STALE_AFTER

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

OWNER = Ed25519PrivateKey.generate()


@pytest.fixture(autouse=True)
def owner_key(monkeypatch):
    raw = OWNER.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    monkeypatch.setattr(feed, "_KEY", feed.Ed25519PublicKey.from_public_bytes(raw))
    monkeypatch.setattr("custom_components.regen_huellhorst.RETRY_S", 3600)  # the live stream is not under test here


def message(rain="on", battery="87", updated=None, key=OWNER, extra=None) -> bytes:
    payload = json.dumps(
        {
            "updated": (updated or dt_util.utcnow()).isoformat(),
            "entities": {
                "binary_sensor.regen": {"state": rain, "name": "Regen", "device_class": "moisture", "unit": None, "state_class": None},
                "sensor.batterie": {"state": battery, "name": "Batterie", "device_class": "battery", "unit": "%", "state_class": "measurement"},
                **(extra or {}),
            },
        }
    )
    body = json.dumps({"p": payload, "s": base64.b64encode(key.sign(payload.encode())).decode()})
    return json.dumps({"event": "message", "message": body}).encode() + b"\n"


async def setup(hass: HomeAssistant, aioclient_mock, *lines: bytes) -> MockConfigEntry:
    aioclient_mock.get(NTFY_URL, content=b"".join(lines))
    entry = MockConfigEntry(domain=DOMAIN, title="Regen Hüllhorst", data={})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def get(hass, domain, entry, key):
    eid = er.async_get(hass).async_get_entity_id(domain, DOMAIN, f"{entry.entry_id}_{key}")
    return hass.states.get(eid)


async def refresh(hass, aioclient_mock, *lines: bytes, status=200) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.get(NTFY_URL, content=b"".join(lines), status=status)
    async_fire_time_changed(hass, dt_util.utcnow() + SCAN_INTERVAL + timedelta(seconds=1))
    await hass.async_block_till_done()


async def test_entities_follow_the_topic(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup(hass, aioclient_mock, message())
    rain = get(hass, "binary_sensor", entry, "binary_sensor.regen")
    assert rain.state == "on" and rain.attributes["device_class"] == "moisture"
    battery = get(hass, "sensor", entry, "sensor.batterie")
    assert battery.state == "87" and battery.attributes["unit_of_measurement"] == "%"

    await refresh(hass, aioclient_mock, message(rain="off", battery="86"))
    assert get(hass, "binary_sensor", entry, "binary_sensor.regen").state == "off"
    assert get(hass, "sensor", entry, "sensor.batterie").state == "86"


async def test_new_entity_appears(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup(hass, aioclient_mock, message())
    lux = {"sensor.helligkeit": {"state": "300", "name": "Helligkeit", "device_class": "illuminance", "unit": "lx", "state_class": "measurement"}}
    await refresh(hass, aioclient_mock, message(extra=lux))
    assert get(hass, "sensor", entry, "sensor.helligkeit").state == "300"


async def test_forged_and_junk_messages_are_ignored(hass: HomeAssistant, aioclient_mock) -> None:
    fake = message(rain="off", key=Ed25519PrivateKey.generate())
    entry = await setup(hass, aioclient_mock, message(rain="on", updated=dt_util.utcnow() - timedelta(minutes=5)), fake, b"junk\n")
    assert get(hass, "binary_sensor", entry, "binary_sensor.regen").state == "on"  # the newer forged "off" did not count


async def test_only_forged_messages_do_not_set_up(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup(hass, aioclient_mock, message(key=Ed25519PrivateKey.generate()))
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_old_data_becomes_unavailable(hass: HomeAssistant, aioclient_mock, freezer) -> None:
    entry = await setup(hass, aioclient_mock, message())
    freezer.tick(STALE_AFTER + timedelta(minutes=1))
    await refresh(hass, aioclient_mock)  # topic is empty now
    assert get(hass, "binary_sensor", entry, "binary_sensor.regen").state == "unavailable"


async def test_unreachable_topic_is_unavailable(hass: HomeAssistant, aioclient_mock) -> None:
    entry = await setup(hass, aioclient_mock, message())
    await refresh(hass, aioclient_mock, status=500)
    assert get(hass, "binary_sensor", entry, "binary_sensor.regen").state == "unavailable"


def test_bodies_skips_keepalives() -> None:
    lines = [b'{"event":"keepalive"}', b"not json", b'{"event":"message","message":"x"}', b'{"event":"message","message":5}']
    assert bodies(lines) == ["x"]


async def test_flow_is_one_click_and_single(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(NTFY_URL, content=message())
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY and result["title"] == "Regen Hüllhorst"
    again = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert again["type"] is FlowResultType.ABORT
