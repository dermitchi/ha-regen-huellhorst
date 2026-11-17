"""Sender side: signs the current sensor values and publishes them to the ntfy topic.

Usage: python3 publish.py <private key.pem> <state of binary_sensor.regen> <state of sensor.batterie>
Run it when the rain sensor changes and every 15 minutes as a heartbeat (ntfy's free limit is 250 messages a day).
"""
import base64
import json
import sys
import urllib.request
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization

TOPIC_URL = "https://ntfy.sh/regen-huellhorst-dermitchi"
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


if __name__ == "__main__":
    key = serialization.load_pem_private_key(open(sys.argv[1], "rb").read(), None)
    body = build(sys.argv[2:], key)
    with urllib.request.urlopen(urllib.request.Request(TOPIC_URL, data=body), timeout=15) as resp:
        print(resp.status)
