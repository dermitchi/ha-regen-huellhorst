"""Constants for Regen Hüllhorst."""

from datetime import timedelta

DOMAIN = "regen_huellhorst"
NAME = "Regen Hüllhorst"
# Public feed that the rain sensor in Hüllhorst writes to (gist, only the owner can edit it).
# The API is read, not the raw URL: raw is cached for 5 minutes, the API is not.
FEED_URL = "https://api.github.com/gists/5251d98c23afedfacb2c1cba0d8dd525"
FEED_FILE = "regen-huellhorst.json"
SCAN_INTERVAL = timedelta(minutes=2)  # GitHub allows 60 anonymous API calls per hour and IP, 304 answers count too
STALE_AFTER = timedelta(hours=1)  # no fresh feed for this long: show unavailable instead of an old "dry"
