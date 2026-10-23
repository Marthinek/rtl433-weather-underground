# RTL433 Weather Underground Uploader

Home Assistant OS add-on that forwards JSON weather observations from MQTT (such as rtl_433) to a Weather Underground Personal Weather Station.

## Install

1. In Home Assistant open **Settings → Add-ons → Add-on store**.
2. Open the top-right menu → **Repositories**.
3. Add `https://github.com/Marthinek/rtl433-weather-underground`.
4. Select **RTL433 Weather Underground Uploader**, install and open its Configuration tab.
5. Configure MQTT and Weather Underground credentials, then configure field names to match your actual MQTT payload.
6. Start the add-on and check its logs.

This is an early beta. The code has not yet been tested against your actual station payload or WU account.

## MQTT

The add-on subscribes to one configurable MQTT topic and expects each matching message to be a JSON object. Nested JSON keys can be mapped with dotted paths.

Example (illustrative only; your rtl_433 decoder may use different keys):

```json
{
  "temperature_C": 18.7,
  "humidity": 64,
  "pressure_hPa": 1014.2,
  "wind_avg_km_h": 8.5,
  "wind_dir_deg": 225,
  "wind_max_km_h": 17,
  "rain_mm": 1.2
}
```

If your Home Assistant entities are created from MQTT discovery but the topic payloads use other field names, use the original MQTT message and set the relevant `*_field` options accordingly. For example, `weather.temperature_C` maps a nested object.

### Configuration fields

- `station_id`, `station_key`: credentials of your Weather Underground PWS.
- `mqtt_host`, `mqtt_port`, `mqtt_username`, `mqtt_password`: MQTT broker connection.
- `mqtt_topic`: MQTT subscription topic. Default: `rtl_433/+/events`.
- `upload_interval`: upload interval in seconds (minimum 30).
- `max_data_age`: skip data if no new MQTT message has arrived recently.
- `temperature_field`, `humidity_field`, `pressure_field`, `wind_speed_field`, `wind_gust_field`, `wind_direction_field`, `rain_hour_field`, `rain_day_field`: JSON keys or dotted paths.
- Unit options indicate the source units; the uploader converts to the units Weather Underground expects.

Leave a field mapping empty to omit that measurement.

## Important notes

- Humidity, temperature, pressure, wind and rain must use the correct source fields and units.
- Wind direction is degrees from 0 to 360.
- Weather stations may publish rainfall as a cumulative counter, a daily total, an hourly total or an incremental amount. This first version does not infer or calculate rain totals from a cumulative counter; map only a field whose meaning you know.
- The uploader waits for a new MQTT message, keeps only the latest message and skips uploads when that message is stale.
- MQTT TLS uses the platform's default CA store. Configure broker username/password as needed.
- Do not paste your station key in GitHub issues or logs.

## Troubleshooting

- **No messages detected:** check the broker hostname, credentials, topic and that the selected topic has JSON weather data.
- **No mapped fields:** inspect one raw MQTT payload and update the field mapping to match the exact key names.
- **No WU update:** confirm the Station ID and Station Key for your PWS and read the add-on logs. Successful WU upload should return `success`.
- **Rain incorrect:** confirm whether the source field is hourly, daily, incremental or cumulative before mapping it.

## Distribution

This is a Home Assistant add-on repository for the add-on store. It is not currently a HACS integration; HACS is a separate distribution path and should be considered only if a native Home Assistant integration is added.

## License

MIT.
