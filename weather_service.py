from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Dict, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

_weather_cache: Dict[Tuple[float, float], Tuple[float, dict]] = {}
_DEFAULT_STATE = {
    "raining": False,
    "hot": False,
    "windy": False,
    "condition_text": "Unknown",
}


def _cache_ttl_seconds() -> int:
    value = os.getenv("WEATHER_CACHE_TTL_SEC", "900")
    try:
        return max(int(value), 60)
    except ValueError:
        return 900


def _request_timeout_seconds() -> float:
    value = os.getenv("WEATHER_REQUEST_TIMEOUT_SEC", "4.0")
    try:
        return max(float(value), 1.0)
    except ValueError:
        return 4.0


def _cache_key(lat: float, lon: float) -> Tuple[float, float]:
    # Round to ~10 km grid for practical caching.
    return round(lat, 1), round(lon, 1)


def _read_cache(lat: float, lon: float) -> dict | None:
    key = _cache_key(lat, lon)
    cached = _weather_cache.get(key)
    if not cached:
        return None
    updated_at, data = cached
    if time.time() - updated_at > _cache_ttl_seconds():
        return None
    return data


def _write_cache(lat: float, lon: float, weather_state: dict) -> dict:
    key = _cache_key(lat, lon)
    if len(_weather_cache) > 1000:
        _weather_cache.clear()
    _weather_cache[key] = (time.time(), weather_state)
    return weather_state


def _mock_weather_state(lat: float, lon: float) -> dict:
    # Deterministic mock by coordinate + current UTC hour.
    hour = datetime.utcnow().hour
    seed = int(abs(lat * 100) + abs(lon * 100) + hour)
    condition = ("Clear", "Rain", "Hot", "Windy")[seed % 4]
    return {
        "raining": condition == "Rain",
        "hot": condition == "Hot",
        "windy": condition == "Windy",
        "condition_text": condition,
    }


def _live_weather_state(lat: float, lon: float) -> dict:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {
            "raining": False,
            "hot": False,
            "windy": False,
            "condition_text": "Clear (No API Key)",
        }

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    )
    timeout = _request_timeout_seconds()
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()

    temp = payload.get("main", {}).get("temp", 20.0)
    wind_speed = payload.get("wind", {}).get("speed", 0.0)
    weather_id = payload.get("weather", [{}])[0].get("id", 800)
    condition_text = payload.get("weather", [{}])[0].get("main", "Clear")

    return {
        "raining": 200 <= weather_id < 600,
        "hot": temp > 30.0,
        "windy": wind_speed > 10.0,
        "condition_text": condition_text,
        "temp_c": temp,
        "wind_mps": wind_speed,
    }


def get_current_weather(lat: float, lon: float) -> dict:
    cached = _read_cache(lat, lon)
    if cached:
        return cached

    use_mock = os.getenv("USE_MOCK_WEATHER", "true").lower() == "true"
    try:
        weather_state = _mock_weather_state(lat, lon) if use_mock else _live_weather_state(lat, lon)
    except Exception:
        weather_state = {
            **_DEFAULT_STATE,
            "condition_text": "Weather Unavailable",
        }

    return _write_cache(lat, lon, weather_state)
