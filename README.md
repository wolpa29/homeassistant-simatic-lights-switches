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
