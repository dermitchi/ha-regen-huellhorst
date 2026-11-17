"""Sender side: signs the current sensor values and publishes them to the ntfy topic.

Usage: python3 publish.py <private key.pem> [--heartbeat] <state of binary_sensor.regen> <state of sensor.batterie>
Run it when the rain sensor changes and, with --heartbeat, every 15 minutes (ntfy's free limit is 250 messages a day
per IP). Heartbeats are skipped once fewer than LOW_LEFT messages are left, so real changes still get through.
"""
import base64
import json
import sys
import urllib.request
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization

TOPIC_URL = "https://ntfy.sh/regen-huellhorst-dermitchi"
LOW_LEFT = 40
# entity id, name, device class, unit, state class – the receivers show exactly these entities
ENTITIES = [
    ("binary_sensor.regen", "Regen", "moisture", None, None),
    ("sensor.batterie", "Batterie", "battery", "%", "measurement"),
]


def build(states: list[str], key) -> bytes:
    payload = json.dumps(
        {
            "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "entities": {
                eid: {"state": state, "name": name, "device_class": dc, "unit": unit, "state_class": sc}
                for (eid, name, dc, unit, sc), state in zip(ENTITIES, states, strict=True)
            },
        },
        ensure_ascii=False,
    )
    return json.dumps({"p": payload, "s": base64.b64encode(key.sign(payload.encode())).decode()}).encode()


def messages_left() -> int:
    with urllib.request.urlopen("https://ntfy.sh/v1/account", timeout=15) as resp:
        return json.load(resp)["stats"]["messages_remaining"]


if __name__ == "__main__":
    key = serialization.load_pem_private_key(open(sys.argv[1], "rb").read(), None)
    args = sys.argv[2:]
    if heartbeat := args[:1] == ["--heartbeat"]:
        args = args[1:]
        if (left := messages_left()) < LOW_LEFT:
            sys.exit(f"only {left} messages left today, heartbeat skipped")
    body = build(args, key)
    with urllib.request.urlopen(urllib.request.Request(TOPIC_URL, data=body), timeout=15) as resp:
        print(resp.status)
