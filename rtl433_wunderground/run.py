#!/usr/bin/env python3
"""MQTT -> Weather Underground PWS uploader for Home Assistant OS."""

from __future__ import annotations

import json
import logging
import math
import os
import signal
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt
import requests

_LOGGER = logging.getLogger("wu_uploader")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

WU_URL = "https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php"
STOP = threading.Event()
LATEST_LOCK = threading.Lock()
LATEST: dict[str, Any] = {}
LATEST_AT = 0.0
LATEST_TOPIC = ""

def opt(name: str, default: Any = None) -> Any:
    return CONFIG.get(name, default)

def numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number

def json_path(data: dict[str, Any], path: str) -> Any:
    """Support dotted nested paths such as weather.temperature_C."""
    if not path:
        return None
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value

def to_f(value: float, unit: str) -> float:
    return value if unit == "F" else value * 9.0 / 5.0 + 32.0

def to_inhg(value: float, unit: str) -> float:
    if unit == "inHg":
        return value
    if unit == "mmHg":
        return value / 25.4
    return value / 33.8638866667  # hPa/mbar

def to_mph(value: float, unit: str) -> float:
    factors = {"mph": 1.0, "m/s": 2.2369362921, "km/h": 0.6213711922, "knots": 1.150779448}
    return value * factors[unit]

def to_inches(value: float, unit: str) -> float:
    return value if unit == "in" else value / 25.4

def _mapped(data: dict[str, Any], field: str) -> float | None:
    return numeric(json_path(data, field))

def build_wu_params(data: dict[str, Any]) -> dict[str, str]:
    """Build WU query parameters from the configured mapping and units."""
    params: dict[str, str] = {
        "ID": str(opt("station_id", "")).strip(),
        "PASSWORD": str(opt("station_key", "")),
        "dateutc": "now",
        "action": "updateraw",
        "softwaretype": "rtl433-weather-underground/0.1.0",
        "realtime": "1",
        "rtfreq": str(max(30, int(opt("upload_interval", 60)))),
    }
    fields: list[tuple[str, str, Any]] = [
        ("temperature_field", "tempf", lambda v: to_f(v, opt("temperature_unit", "C"))),
        ("humidity_field", "humidity", lambda v: v),
        ("pressure_field", "baromin", lambda v: to_inhg(v, opt("pressure_unit", "hPa"))),
        ("wind_speed_field", "windspeedmph", lambda v: to_mph(v, opt("wind_speed_unit", "km/h"))),
        ("wind_gust_field", "windgustmph", lambda v: to_mph(v, opt("wind_gust_unit", "km/h"))),
        ("wind_direction_field", "winddir", lambda v: v),
        ("rain_hour_field", "rainin", lambda v: to_inches(v, opt("rain_hour_unit", "mm"))),
        ("rain_day_field", "dailyrainin", lambda v: to_inches(v, opt("rain_day_unit", "mm"))),
    ]
    for config_field, wu_field, converter in fields:
        source_path = str(opt(config_field, "") or "").strip()
        if not source_path:
            continue
        value = _mapped(data, source_path)
        if value is None:
            continue
        if wu_field == "humidity":
            value = max(0.0, min(100.0, value))
        elif wu_field == "winddir":
            value = value % 360.0
        elif wu_field in ("rainin", "dailyrainin", "windspeedmph", "windgustmph"):
            if value < 0:
                _LOGGER.warning("Ignoring negative value for configured field %s", config_field)
                continue
        try:
            converted = converter(value)
        except (KeyError, ValueError, TypeError):
            _LOGGER.warning("Invalid unit configuration for %s", config_field)
            continue
        if math.isfinite(converted):
            params[wu_field] = f"{converted:.2f}" if wu_field != "humidity" and wu_field != "winddir" else f"{converted:.0f}"
    return params

def on_connect(client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
    # Paho MQTT v2 passes a ReasonCode object, not an int.
    code = getattr(reason_code, "value", reason_code)
    if int(code) == 0:
        topic = str(opt("mqtt_topic", "rtl_433/+/events"))
        client.subscribe(topic, qos=0)
        _LOGGER.info("Connected to MQTT broker; subscribed to %s", topic)
    else:
        _LOGGER.error("MQTT connection refused (code %s)", reason_code)

def on_message(client: mqtt.Client, userdata: Any, message: mqtt.MQTTMessage) -> None:
    global LATEST, LATEST_AT, LATEST_TOPIC
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("top-level JSON value is not an object")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as err:
        _LOGGER.debug("Ignoring non-JSON MQTT payload on %s: %s", message.topic, err)
        return
    # A station may publish metadata/other messages on the same topic.
    with LATEST_LOCK:
        LATEST = payload
        LATEST_AT = time.time()
        LATEST_TOPIC = message.topic

def upload_once() -> None:
    with LATEST_LOCK:
        payload = dict(LATEST)
        age = time.time() - LATEST_AT if LATEST_AT else float("inf")
        source_topic = LATEST_TOPIC
    if not payload:
        _LOGGER.info("Waiting for first JSON MQTT weather message")
        return
    max_age = int(opt("max_data_age", 300))
    if age > max_age:
        _LOGGER.warning("Latest MQTT message is %.0fs old (limit %ss); skipping upload", age, max_age)
        return
    params = build_wu_params(payload)
    required = ("ID", "PASSWORD")
    if not all(params.get(key) for key in required):
        _LOGGER.error("Weather Underground station_id/station_key are not configured")
        return
    weather_fields = set(params) - {"ID", "PASSWORD", "dateutc", "action", "softwaretype"}
    if not weather_fields:
        _LOGGER.warning("No configured sensor fields found in latest MQTT payload (topic %s)", source_topic)
        return
    # Never log the full URL or request parameters; they include the station key.
    try:
        response = requests.get(WU_URL, params=params, timeout=20, allow_redirects=False)
        response.raise_for_status()
        body = response.text.strip()
        if body.lower().startswith("success"):
            _LOGGER.info("Weather Underground upload succeeded; fields=%s, MQTT age=%.0fs", ",".join(sorted(weather_fields)), age)
        else:
            _LOGGER.error("Weather Underground rejected or did not confirm upload (HTTP %s, response=%r)", response.status_code, body[:160])
    except requests.RequestException as err:
        _LOGGER.warning("Weather Underground request failed (%s); will retry on next interval", type(err).__name__)

def load_config() -> dict[str, Any]:
    path = os.getenv("WU_OPTIONS_PATH", "/data/options.json")
    try:
        with open(path, encoding="utf-8") as stream:
            config = json.load(stream)
    except (OSError, json.JSONDecodeError) as err:
        raise RuntimeError(f"Cannot read add-on configuration at {path}: {err}") from err
    if not isinstance(config, dict):
        raise RuntimeError("Add-on configuration is invalid")
    return config

CONFIG = load_config()

def main() -> None:
    if not opt("station_id") or not opt("station_key"):
        _LOGGER.warning("Set station_id and station_key in the add-on configuration before uploads can succeed")
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="ha-wu-uploader",
        protocol=mqtt.MQTTv311,
    )
    username = str(opt("mqtt_username", "") or "")
    password = str(opt("mqtt_password", "") or "")
    if username:
        client.username_pw_set(username, password)
    if bool(opt("mqtt_tls", False)):
        client.tls_set()
    client.on_connect = on_connect
    client.on_message = on_message
    host = str(opt("mqtt_host", "core-mosquitto"))
    port = int(opt("mqtt_port", 1883))
    interval = int(opt("upload_interval", 60))
    if interval < 30:
        raise RuntimeError("upload_interval must be at least 30 seconds")
    signal.signal(signal.SIGTERM, lambda *_: STOP.set())
    signal.signal(signal.SIGINT, lambda *_: STOP.set())
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    try:
        client.connect_async(host, port, keepalive=60)
        client.loop_start()
        _LOGGER.info("Uploader started; MQTT=%s:%s, upload interval=%ss", host, port, interval)
        while not STOP.wait(interval):
            upload_once()
    except (OSError, ValueError, mqtt.MQTTException) as err:
        _LOGGER.exception("Uploader stopped because of an error: %s", err)
        raise
    finally:
        client.loop_stop()
        try:
            client.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    main()
