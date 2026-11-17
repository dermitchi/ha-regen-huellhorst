# Regen Hüllhorst

Live rain data from Hüllhorst for your Home Assistant. Install it, add it, done: nothing to configure.

A rain sensor in Hüllhorst publishes its values to a public [ntfy](https://ntfy.sh) topic. This integration keeps a connection to that topic open, so a change (rain starts, rain stops) shows up in your Home Assistant within seconds, and creates the same entities there (for example *Regen* nass/trocken and *Batterie*). If there has been no update for an hour, the entities show *unavailable* instead of an old value.

## Install

HACS → Custom repositories → add `https://github.com/dermitchi/ha-regen-huellhorst` (type *Integration*), install, restart Home Assistant, then *Settings → Devices & services → Add integration → Regen Hüllhorst*.

New entities from the sensor appear on their own, no update needed.

## Security

The topic is public and anyone can write to it, so every message carries an Ed25519 signature. The integration only accepts messages signed with the owner's key (the public key is in `const.py`), drops anything older than an hour or older than what it already has (so recorded messages can't be replayed), and checks every field it receives. Others can't fake rain, they can only add noise that is ignored. The integration reads from ntfy.sh over HTTPS and sends nothing about you or your Home Assistant.

## Sender side (the one with the sensor)

`tools/make_key.py` creates the key pair, `tools/publish.py` signs the current values and publishes them. Run it when the sensor changes and every 15 minutes as a heartbeat (ntfy's free limit is 250 messages a day).
