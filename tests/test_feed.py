"""Signature, replay and shape checks – the part that keeps strangers from faking rain."""

import base64
import importlib.util
import json
from datetime import timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from homeassistant.util import dt as dt_util

import custom_components.regen_huellhorst.feed as feed

OWNER = Ed25519PrivateKey.generate()


def make(key=OWNER, updated=None, entities=None, tamper=False) -> str:
    payload = json.dumps(
        {
            "updated": (updated or dt_util.utcnow()).isoformat(),
            "entities": entities or {"binary_sensor.regen": {"state": "on", "name": "Regen"}},
        }
    )
    sig = key.sign(payload.encode())
    if tamper:
        payload = payload.replace("on", "off")
    return json.dumps({"p": payload, "s": base64.b64encode(sig).decode()})


def setup_function() -> None:
    raw = OWNER.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    feed._KEY = feed.Ed25519PublicKey.from_public_bytes(raw)  # tests sign with their own key


def test_valid_message_passes() -> None:
    assert feed.verify(make())["entities"]["binary_sensor.regen"]["state"] == "on"


def test_foreign_key_and_tampering_are_rejected() -> None:
    assert feed.verify(make(key=Ed25519PrivateKey.generate())) is None
    assert feed.verify(make(tamper=True)) is None
    assert feed.verify("not json") is None and feed.verify("{}") is None and feed.verify('{"p":1,"s":2}') is None


def test_old_and_future_messages_are_rejected() -> None:
    assert feed.verify(make(updated=dt_util.utcnow() - timedelta(hours=2))) is None
    assert feed.verify(make(updated=dt_util.utcnow() + timedelta(hours=1))) is None


def test_bad_entities_are_rejected() -> None:
    for bad in (
        {"light.kitchen": {"state": "on", "name": "x"}},  # not a shared domain
        {"sensor.a": {"state": 5, "name": "x"}},  # state must be text
        {"sensor.a": {"state": "1"}},  # name missing
        {f"sensor.s{i}": {"state": "1", "name": "x"} for i in range(21)},  # too many
    ):
        assert feed.verify(make(entities=bad)) is None


def test_replayed_older_message_never_wins() -> None:
    now = dt_util.utcnow()
    newer, older = make(updated=now), make(updated=now - timedelta(minutes=5), entities={"binary_sensor.regen": {"state": "off", "name": "Regen"}})
    assert feed.newest([newer, older])["entities"]["binary_sensor.regen"]["state"] == "on"
    current = feed.verify(newer)
    assert feed.newest([older], current) is current
    assert feed.newest(["junk", make(key=Ed25519PrivateKey.generate())]) is None


def test_publish_script_output_is_accepted() -> None:
    spec = importlib.util.spec_from_file_location("publish", Path(__file__).parent.parent / "tools" / "publish.py")
    publish = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publish)
    data = feed.verify(publish.build(["on", "87"], OWNER).decode())
    assert data["entities"]["sensor.batterie"]["unit"] == "%"
