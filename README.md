# RTL433 Weather Underground Uploader

A Home Assistant OS add-on that forwards weather observations received over MQTT to a Weather Underground Personal Weather Station (PWS). It is designed for weather sensors decoded by [rtl_433](https://github.com/merbanan/rtl_433), including stations that publish JSON over MQTT.

The add-on subscribes to your configured MQTT topic, maps fields from the latest JSON message, converts supported units, and periodically uploads available values to Weather Underground.

## Tested hardware and confirmed functionality

**Tested with:** Vevor 7-in-1 Wireless Weather Station, using `rtl_433` JSON messages delivered over MQTT.

The following has been verified with this setup:

- MQTT messages from the station are received by the add-on.
- Temperature is converted from Celsius to the Weather Underground temperature field.
- Relative humidity and wind direction are uploaded.
- Average wind speed and wind gust are converted from km/h to mph and uploaded.
- Weather Underground confirms successful uploads, and the add-on log lists the submitted fields.

The tested upload log included: `humidity`, `tempf`, `winddir`, `windspeedmph`, and `windgustmph`.

**Not confirmed for this setup:** pressure upload, hourly/daily rainfall interpretation, and other weather station models. The example Vevor payload below does not include pressure. Rain fields should not be enabled until their meaning (for example, interval amount versus cumulative total) is confirmed.

Other rtl_433-compatible stations may work, but their payload field names and sensor semantics can differ. They may require different field mappings and testing.

## Features

- MQTT input, including the common `rtl_433/+/events` topic pattern.
- Configurable JSON field mapping, including dotted paths for nested JSON.
- Unit conversion for temperature, pressure, wind speed/gust, and rain.
- Configurable upload interval and maximum accepted MQTT message age.
- Skips fields that are missing or not numeric rather than sending invented values.
- Logs upload status and submitted field names without printing station credentials.

## Installation

This project is distributed as a **Home Assistant add-on repository**. HACS is not required.

1. In Home Assistant, open **Settings → Add-ons → Add-on store**.
2. Open the store menu and select **Repositories**.
3. Add this repository:
   `https://github.com/Marthinek/rtl433-weather-underground`
4. Find **RTL433 Weather Underground Uploader** and install it.
5. Open the add-on's **Configuration** page and fill in the settings described below.
6. Start the add-on, then check the **Log** tab for MQTT connection and upload status.

To install a newer release, refresh the add-on store/repository and install the offered update when it becomes available.

## Configuration

Configure the add-on through the Home Assistant add-on configuration page.

### Weather Underground

- **Station ID** (`station_id`): your Weather Underground PWS station ID.
- **Station Key** (`station_key`): the matching station key.

Create or configure your PWS through Weather Underground. Keep these values private: do not commit them to Git, post them in screenshots, or include them in public issues.

### MQTT connection

| Option | Default | Description |
| --- | --- | --- |
| `mqtt_host` | `core-mosquitto` | MQTT broker hostname reachable from the add-on |
| `mqtt_port` | `1883` | MQTT broker port |
| `mqtt_username` | empty | MQTT username, if required |
| `mqtt_password` | empty | MQTT password, if required |
| `mqtt_topic` | `rtl_433/+/events` | Topic filter containing the weather JSON |
| `mqtt_tls` | `false` | Enable TLS for the MQTT connection |

The MQTT broker and rtl_433 publisher must already be running, and the configured topic must receive JSON weather messages. If your broker uses authentication, configure the correct MQTT username and password.

### Upload behaviour

| Option | Default | Description |
| --- | --- | --- |
| `upload_interval` | `60` | Upload interval in seconds (30–3600) |
| `max_data_age` | `300` | Maximum age of the latest MQTT message in seconds before upload is skipped |

The add-on uses the latest JSON message received on the subscribed topic. If that message becomes older than `max_data_age`, it skips the upload rather than sending stale observations.

### JSON field mapping

The default field mappings are intended for common rtl_433 weather payloads. If your decoder uses different names, change the mapping to match the JSON keys exactly.

| Setting | Default JSON field | Weather Underground field |
| --- | --- | --- |
| `temperature_field` | `temperature_C` | Temperature (`tempf`) |
| `temperature_unit` | `C` | Input temperature unit: Celsius or Fahrenheit |
| `humidity_field` | `humidity` | Relative humidity |
| `pressure_field` | `pressure_hPa` | Pressure (`baromin`) |
| `pressure_unit` | `hPa` | Input pressure unit: hPa, inHg, or mmHg |
| `wind_speed_field` | `wind_avg_km_h` | Average wind speed (`windspeedmph`) |
| `wind_speed_unit` | `km/h` | Input wind speed unit |
| `wind_gust_field` | `wind_max_km_h` | Wind gust (`windgustmph`) |
| `wind_gust_unit` | `km/h` | Input gust speed unit |
| `wind_direction_field` | `wind_dir_deg` | Wind direction in degrees |
| `rain_hour_field` | empty | Hourly rain amount (`rainin`) |
| `rain_hour_unit` | `mm` | Input hourly rain unit: mm or inches |
| `rain_day_field` | empty | Daily rain amount (`dailyrainin`) |
| `rain_day_unit` | `mm` | Input daily rain unit: mm or inches |

Rain mappings are empty by default intentionally. Only configure them once you know what the sensor's rain field represents.

The add-on supports dotted paths for nested JSON, for example `weather.temperature_C`.

## Example MQTT payload

This is an example message received from the tested Vevor 7-in-1 Wireless Weather Station via rtl_433:

```json
{
  "time": "2026-10-23T05:28:17",
  "model": "Vevor-7in1",
  "id": 50167,
  "channel": 0,
  "battery_ok": 0,
  "temperature_C": 1.8,
  "humidity": 99,
  "wind_avg_km_h": 0.0,
  "wind_max_km_h": 0.0,
  "wind_dir_deg": 250,
  "rain_mm": 0.0,
  "uvi": 0.0,
  "light_lux": 0,
  "mic": "CHECKSUM"
}
```

The example includes temperature, humidity, wind speed, gust, wind direction, rain, UV index and light level. The current uploader mapping does not send every field in the payload: only configured and supported Weather Underground fields are uploaded.

**Important:** this payload does not contain a pressure field. Pressure will not be uploaded unless your MQTT payload includes a pressure value and `pressure_field` points to the correct key. Do not infer pressure from temperature or humidity.

## Rain data

Rain fields require special care. Depending on the station and decoder, a rain value may be a cumulative counter, a daily total, or an amount for a particular interval. These meanings are not interchangeable.

Do not map a field such as `rain_mm` to hourly or daily rain until you have confirmed what it represents. Incorrect mapping can result in misleading rainfall values on Weather Underground. Counter rollover/reset handling is not currently provided by this add-on.

## Logs and troubleshooting

Open the add-on's **Log** tab in Home Assistant.

Common messages:

- **Waiting for first JSON MQTT weather message** — no valid JSON weather message has been received yet.
- **Connected to MQTT broker; subscribed to ...** — the MQTT connection succeeded and the topic subscription was requested.
- **Weather Underground upload succeeded; fields=...** — Weather Underground returned a success response; the log lists the submitted weather fields.
- **Latest MQTT message is ... old** — no sufficiently recent message is available; check the sensor, rtl_433 publisher, MQTT topic, and `max_data_age`.
- **Invalid unit configuration** — check the selected input units in the add-on configuration.

A successful upload confirms that Weather Underground accepted the request, but you should still verify that the station page displays updated values as expected.

## Development status

The current implementation has been tested with a Vevor 7-in-1 Wireless Weather Station, rtl_433 MQTT messages, and a Weather Underground PWS. Compatibility with other stations has not been confirmed. Sensor models and payloads vary, so verify field mappings and units for your own setup before relying on the reported data.

## License

MIT. See [LICENSE](LICENSE).
