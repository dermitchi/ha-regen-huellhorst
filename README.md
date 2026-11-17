# Rain Sense

Share a rain sensor (or any `binary_sensor` / `sensor`) from one Home Assistant with another one. The receiver gets exactly the entities the sender chose: state, name, device class, unit.

Made for a Zigbee rain sensor shared with a friend, but it works with any binary sensor or sensor.

## How it works

- **Sender:** add the integration, pick *Share my sensor*, choose the entities. You get a private link like `https://your-ha/api/rain_sense/<secret>`. It is read-only and only serves the chosen entities.
- **Receiver:** add the integration, pick *Receive a shared sensor* and paste the link. The entities appear as one device and update every 60 seconds.

You can change the shared entities later under *Configure* on the sender entry. Remove the entry to revoke the link.

## Install

HACS → Custom repositories → add `https://github.com/dermitchi/ha-rain-sense` (type *Integration*), install, restart Home Assistant, then *Settings → Devices & services → Add integration → Rain Sense*.

## Reachability

The receiver's Home Assistant must reach the sender's Home Assistant at the link's address. Rain Sense does not open anything to the internet. Options: Tailscale (put both in one tailnet, use the sender's tailnet address), a reverse proxy, or Nabu Casa remote URL. The address in the link is only a suggestion: replace the host in front of `/api/rain_sense/...` with the one your friend can reach.

## Security

Anyone with the link can read the shared entities. Keep it private and delete the sender entry to revoke it. The link contains the key, so it may show up in proxy logs.
