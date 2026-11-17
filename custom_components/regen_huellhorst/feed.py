"""Checks messages from the ntfy topic: signature, age and shape. Anything else is dropped."""

from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from homeassistant.util import dt as dt_util

from .const import MAX_FUTURE, PUBLIC_KEY, STALE_AFTER

_KEY = Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY))
_ENTITY_ID = re.compile(r"^(binary_sensor|sensor)\.[a-z0-9_]{1,40}$")
MAX_ENTITIES = 20


def _text(value: Any, limit: int) -> str | None:
    return value[:limit] if isinstance(value, str) else None


def _clean(entities: Any) -> dict[str, dict[str, Any]] | None:
    """Keep only well-formed entities, with every field limited in type and length."""
    if not isinstance(entities, dict) or len(entities) > MAX_ENTITIES:
        return None
    out = {}
    for entity_id, item in entities.items():
        if not (_ENTITY_ID.match(str(entity_id)) and isinstance(item, dict)):
            return None
        state, name = _text(item.get("state"), 64), _text(item.get("name"), 64)
        if state is None or not name:
            return None
        out[entity_id] = {
            "state": state,
            "name": name,
            "device_class": _text(item.get("device_class"), 32),
            "unit": _text(item.get("unit"), 16),
            "state_class": _text(item.get("state_class"), 32),
        }
    return out


def verify(body: str, now: datetime | None = None) -> dict[str, Any] | None:
    """Return the payload of a message body if it is signed by the owner, fresh and well-formed."""
    now = now or dt_util.utcnow()
    try:
        message = json.loads(body)
        payload = message["p"]
        _KEY.verify(base64.b64decode(message["s"], validate=True), payload.encode())
        data = json.loads(payload)
        updated = dt_util.parse_datetime(data["updated"])
        entities = _clean(data["entities"])
    except (ValueError, KeyError, TypeError, AttributeError, InvalidSignature):
        return None
    if updated is None or updated.tzinfo is None or entities is None:
        return None
    if now - updated > STALE_AFTER or updated - now > MAX_FUTURE:
        return None  # an old signed message replayed later must not count as current
    return {"updated": updated.isoformat(), "entities": entities}


def newest(bodies: list[str], current: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """The valid payload with the latest timestamp; never goes back in time relative to current."""
    best = current
    for body in bodies:
        if (data := verify(body)) and (best is None or data["updated"] > best["updated"]):
            best = data
    return best
