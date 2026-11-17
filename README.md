# Regen Hüllhorst

Live rain data from Hüllhorst for your Home Assistant. Install it, add it, done: nothing to configure.

A rain sensor in Hüllhorst publishes its values to a public feed. This integration reads the feed every few minutes and creates the same entities in your Home Assistant (for example *Regen* nass/trocken and *Batterie*). If the feed is older than an hour, the entities show *unavailable* instead of an old value.

## Install

HACS → Custom repositories → add `https://github.com/dermitchi/ha-regen-huellhorst` (type *Integration*), install, restart Home Assistant, then *Settings → Devices & services → Add integration → Regen Hüllhorst*.

New entities from the sensor appear on their own, no update needed. Code updates show up in HACS as usual.
