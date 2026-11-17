"""Constants for Rain Sense."""

from datetime import timedelta

DOMAIN = "rain_sense"
CONF_MODE = "mode"
CONF_ENTITIES = "entities"
CONF_KEY = "key"
CONF_URL = "url"
MODE_SEND = "send"
MODE_RECEIVE = "receive"
SHARE_DOMAINS = ["binary_sensor", "sensor"]
SCAN_INTERVAL = timedelta(seconds=60)
URL_PATH = "/api/rain_sense"
