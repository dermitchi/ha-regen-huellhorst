"""Constants for Regen Hüllhorst."""

from datetime import timedelta

DOMAIN = "regen_huellhorst"
NAME = "Regen Hüllhorst"
# The sensor in Hüllhorst publishes signed messages to this public ntfy topic. Anyone can write to it,
# so every message is checked against PUBLIC_KEY; only the owner of the private key can make valid ones.
NTFY_URL = "https://ntfy.sh/regen-huellhorst-dermitchi/json"
PUBLIC_KEY = "498PjI7wJBIpak3eDA7RKOKESBw/igo6U1jKoBJ3twg="
SCAN_INTERVAL = timedelta(minutes=5)  # fallback poll and staleness check; live updates come through the open stream
STALE_AFTER = timedelta(minutes=30)  # no valid message for this long (the sender sends a heartbeat every 10 minutes): show unavailable instead of an old "dry"
MAX_FUTURE = timedelta(minutes=10)  # tolerated clock difference to the sender
