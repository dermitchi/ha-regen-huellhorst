"""Constants for Regen Hüllhorst."""

from datetime import timedelta

DOMAIN = "regen_huellhorst"
NAME = "Regen Hüllhorst"
# Public feed that the rain sensor in Hüllhorst writes to (gist, only the owner can edit it).
FEED_URL = "https://gist.githubusercontent.com/dermitchi/GIST_ID/raw/regen-huellhorst.json"
SCAN_INTERVAL = timedelta(minutes=5)  # raw.githubusercontent caches for up to 5 minutes anyway
STALE_AFTER = timedelta(hours=1)  # no fresh feed for this long: show unavailable instead of an old "dry"
