# rtl433-weather-underground

A Home Assistant OS add-on that forwards weather observations received over MQTT (for example, from `rtl_433`) to a Weather Underground Personal Weather Station (PWS).

> **Early development / beta:** This project needs testing with real `rtl_433` MQTT messages and a Weather Underground PWS. Do not assume rain accumulation fields are interchangeable; configure mappings to match your sensors.

## Features

- Subscribe to an MQTT topic and parse JSON messages.
- Configurable JSON field mapping for temperature, humidity, pressure, wind and rain.
- Convert common metric units to the Weather Underground upload units.
- Periodic uploads to Weather Underground.
- Validate MQTT data age and values; avoid sending fields that are not available.
- Keep station credentials in the add-on options, not in source code.
- Logs with credentials redacted.

## Installation (manual beta testing)

1. In Home Assistant, open **Settings → Add-ons → Add-on store**.
2. Open the menu and select **Repositories**.
3. Add this repository URL: `https://github.com/Marthinek/rtl433-weather-underground`.
4. Find **RTL433 Weather Underground Uploader**, install it and configure the add-on.
5. Configure MQTT broker details, the topic that contains your station data, and the JSON field mapping.
6. Start the add-on and inspect its logs before relying on uploads.

This repository is distributed as a **Home Assistant add-on repository**, not yet as a HACS integration. HACS and the add-on store are different distribution mechanisms. A native HACS integration may be added later if there is a good use case.

## MQTT input

The add-on expects JSON messages. A typical example might look like this, but the real `rtl_433` field names vary by station and decoder:

```json
{
  "temperature_C": 18.7,
  "humidity": 64,
  "pressure_hPa": 1014.2,
  "wind_avg_km_h": 8.5,
  "wind_dir_deg": 225,
  "rain_mm": 1.2
}
```

Configure the mappings to match your actual payload. Do not share your Weather Underground key in issues or logs.

## Rain totals

Rain data needs special care. A station may publish a cumulative counter, a daily total, or an hourly amount. These are not interchangeable. Map the correct metric and unit; avoid interpreting a cumulative counter as an hourly amount. Counter rollover/reset handling will be improved as real payload examples become available.

## Weather Underground credentials

Create/configure a Personal Weather Station in Weather Underground and enter its Station ID and Station Key in the add-on configuration. Use only your own station credentials. Do not commit credentials to Git.

## Development status

Initial repository scaffolding. The first implementation is deliberately configurable because the owner's exact MQTT payload has not yet been captured. Test using real sensor payloads before calling the release stable.

## License

MIT. See [LICENSE](LICENSE).
