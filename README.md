# Home Assistant Simatic (S7) integration

Connects Home Assistant to a Siemens Simatic PLC (S7) over
[snap7](https://snap7.sourceforge.net/). My lights and blinds are momentary push
buttons (Taster), so turning one on or off just sends a short pulse on a bit in a
data block, and the PLC reacts on the edge.

Everything is set up in the UI now, no YAML. You add one connection to your PLC,
then add each light and blind as a device. The old YAML components, to manually add it in the folder structure and with the configuration.yaml file, are still in
`original/` if you want them. (no HACS overhead)

## Install with HACS

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=wolpa29&repository=homeassistant-simatic-lights-switches&category=integration)

Click the button (or add this repo in HACS as a custom repository, category
Integration), install it and restart. Needs a fairly recent Home Assistant
(around 2025.3 or newer). You can also just copy `custom_components/simatic/`
into your `config/custom_components/` folder by hand.

`python-snap7` gets installed automatically. This uses version 3.0+, which is
pure Python, so there's no native `libsnap7.so` to worry about anymore (that was
the annoying part on Linux). Just leave the library path empty.

## Setup

1. Settings -> Devices and Services -> Add Integration -> Simatic (S7). Enter
   host/IP, rack and slot (defaults 0 / 2). Done once.
2. On the integration, hit Add device, pick Light or Switch/blind, and fill in
   name, the control address (`db_number`, `start_offset`, `bit_offset`) and
   optionally a status address for state feedback.
3. Repeat for every device. You can edit or remove them in the UI anytime.

## Good to know

- Lights read their status from a data block, switches read it from the output
  process image (PA area), same as my original code. So for switches the status
  `db_number` is ignored, only byte and bit matter.
- All devices share one connection to the PLC and poll once per second.

> Uses snap7 (LGPL v3), which is not shipped here.

---

# Old YAML components

Below is the original README for the older `simatic_lights` and
`simatic_switches` components, now kept under `original/`. Still work, but need
YAML and a restart to change devices.

# Homeassistant Simatic lights and switches integrations

Home Assistant custom components to connect a Siemens Simatic PLC (S7) over
[snap7](https://snap7.sourceforge.net/):

- **`simatic_lights`** switches lights via a bit in a data block (DB).
- **`simatic_switches`** controls switches or blinds via bits in a data block (DB).

## Setup

Copy the `simatic_lights` and/or `simatic_switches` folder into your
`config/custom_components/` directory and restart Home Assistant. Then add the
example config to your `configuration.yaml` (lights under `light:`, switches under
`switch:`) and adjust `host`, `rack`, `slot` and the DB addresses to your PLC.

In my setup these are momentary push buttons (Taster), not level switches, so the
component only sends a short pulse. The PLC reacts on the falling edge.

`python-snap7` is listed as a requirement, so Home Assistant installs it
automatically. Since `python-snap7 == 1.3` ships the native `libsnap7` library,
you normally just leave the `lib:` option out of your config.

If loading the bundled library fails, get a matching `libsnap7.so` (from the
[Snap7 project](https://snap7.sourceforge.net/) or
[`python-snap7`](https://github.com/gijzelaerr/python-snap7)), drop it into your
`config` folder and uncomment `lib:` in the config to point at it.

> Uses snap7 (LGPL v3), which is not shipped here.

## Credits
Big thanks to [@dereisele](https://github.com/dereisele). He inspired my very first Home Assistant integration and helped me figure out the snap7 setup for my Simatic smart home back in 2023. Finally sharing my own custom component code now after some successfully connected years between Home Assistant and my Simatic home automation. Thanks for the support!
