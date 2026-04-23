from __future__ import annotations

import ast


def _as_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_highway(highway: object) -> str:
    if isinstance(highway, (list, tuple)) and highway:
        return str(highway[0]).lower()
    if isinstance(highway, str):
        value = highway.strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                parsed = ast.literal_eval(value)
                if isinstance(parsed, (list, tuple)) and parsed:
                    return str(parsed[0]).lower()
            except (ValueError, SyntaxError):
                pass
        return value.lower()
    return "unclassified"


HIGHWAY_STRESS = {
    "footway": 0.85,
    "pedestrian": 0.85,
    "path": 0.9,
    "cycleway": 0.9,
    "living_street": 0.95,
    "residential": 1.0,
    "service": 1.15,
    "unclassified": 1.25,
    "tertiary": 1.4,
    "tertiary_link": 1.5,
    "secondary": 2.0,
    "secondary_link": 2.2,
    "primary": 2.8,
    "primary_link": 3.0,
    "trunk": 3.4,
    "trunk_link": 3.7,
    "motorway": 4.0,
    "motorway_link": 4.2,
}
