from __future__ import annotations

import sys

from app import app


SAMPLE_PAYLOAD_BASE = {
    "start_lat": 30.7333,
    "start_lon": 76.7794,
    "end_lat": 30.7392,
    "end_lon": 76.7739,
}


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_smoke() -> None:
    client = app.test_client()

    health = client.get("/health")
    ensure(health.status_code == 200, f"/health failed with {health.status_code}")

    zones = client.get("/api/safety_zones")
    ensure(zones.status_code == 200, f"/api/safety_zones failed with {zones.status_code}")
    zones_json = zones.get_json()
    ensure(isinstance(zones_json, dict), "safety zones response is not JSON object")
    ensure("features" in zones_json, "safety zones missing features")

    modes = ("fastest", "calm", "safe", "accessibility", "dog", "weather")
    for mode in modes:
        payload = {**SAMPLE_PAYLOAD_BASE, "route_mode": mode}
        if mode == "dog":
            payload["dog_sub_mode"] = "relax"
        response = client.post("/smart_route", json=payload)
        ensure(response.status_code == 200, f"/smart_route failed for mode={mode} status={response.status_code}")
        data = response.get_json()
        ensure("fastest_route" in data, f"mode={mode} missing fastest_route")
        ensure(isinstance(data["fastest_route"], list), f"mode={mode} fastest_route must be a list")
        if mode != "fastest":
            ensure("smart_route" in data, f"mode={mode} missing smart_route")
            ensure(isinstance(data["smart_route"], list), f"mode={mode} smart_route must be a list")

    print("Smoke checks passed for /health, /api/safety_zones, and /smart_route modes.")


if __name__ == "__main__":
    try:
        run_smoke()
    except Exception as exc:  # pragma: no cover
        print(f"Smoke checks failed: {exc}")
        sys.exit(1)
