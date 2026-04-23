from __future__ import annotations

from shapely.geometry import LineString, Polygon

# Mock crime/danger zones near Chandigarh center.
_MOCK_ZONES = [
    Polygon(
        [
            (76.7780, 30.7400),
            (76.7850, 30.7400),
            (76.7850, 30.7450),
            (76.7780, 30.7450),
        ]
    ),
    Polygon(
        [
            (76.7700, 30.7250),
            (76.7750, 30.7250),
            (76.7750, 30.7300),
            (76.7700, 30.7300),
        ]
    ),
]


def get_safety_zones_geojson():
    features = []
    for polygon in _MOCK_ZONES:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [list(polygon.exterior.coords)],
                },
                "properties": {"danger_level": "high"},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def is_edge_unsafe(lon_lat_points: list) -> bool:
    if not lon_lat_points or len(lon_lat_points) < 2:
        return False

    line = LineString(lon_lat_points)
    line_bounds = line.bounds
    lx0, ly0, lx1, ly1 = line_bounds

    for zone in _MOCK_ZONES:
        zx0, zy0, zx1, zy1 = zone.bounds
        if lx1 < zx0 or lx0 > zx1 or ly1 < zy0 or ly0 > zy1:
            continue
        if zone.intersects(line):
            return True
    return False
