from __future__ import annotations

from accessibility import (
    get_accessibility_intersection_penalty,
    get_accessibility_turn_penalty,
    get_accessibility_weight,
)
from dog_mode import get_dog_intersection_penalty, get_dog_turn_penalty, get_dog_weight
from routing_utils import HIGHWAY_STRESS, _as_float, _normalize_highway
from safety_zones import is_edge_unsafe


def _weather_adjusted_stress(highway: str, stress: float, weather: dict, *, stronger: bool) -> float:
    rain_mult = 1.8 if stronger else 1.5
    wind_mult = 1.7 if stronger else 1.5

    if weather.get("raining"):
        if highway in ("path", "pedestrian", "footway", "cycleway"):
            stress *= rain_mult
        elif highway in ("residential", "living_street"):
            stress *= 0.85
    if weather.get("hot"):
        if highway in ("living_street", "residential", "pedestrian", "footway"):
            stress *= 0.8
        elif highway in ("primary", "secondary", "trunk"):
            stress *= 1.15
    if weather.get("windy"):
        if highway in ("primary", "secondary", "trunk"):
            stress *= wind_mult
    return stress


class RouteMode:
    def __init__(self, weather=None, dog_sub_mode=None, preference_bias: int = 50):
        self.weather = weather or {}
        self.dog_sub_mode = dog_sub_mode
        self.preference_bias = max(0, min(100, int(preference_bias)))

    @property
    def comfort_factor(self) -> float:
        # 0.5x at 0, 1.0x at 50, 1.5x at 100
        return 0.5 + (self.preference_bias / 100.0)

    def get_weight(self, u, v, edge_data, lon_lat_points=None):
        return _as_float(edge_data.get("length"), 1.0)

    def get_turn_penalty(self, delta: float) -> float:
        return 0.0

    def get_intersection_penalty(self, street_count: float) -> float:
        return 0.0


class CalmMode(RouteMode):
    def get_weight(self, u, v, edge_data, lon_lat_points=None):
        length = _as_float(edge_data.get("length"), 1.0)
        highway = _normalize_highway(edge_data.get("highway", "unclassified"))
        stress = HIGHWAY_STRESS.get(highway, 1.5)
        stress = _weather_adjusted_stress(highway, stress, self.weather, stronger=False)
        effective_stress = 1.0 + (stress - 1.0) * self.comfort_factor
        return max(length * effective_stress, 0.1)

    def get_turn_penalty(self, delta: float) -> float:
        if delta < 25:
            return 0.0
        if delta < 55:
            return 8.0
        if delta < 95:
            return 18.0
        if delta < 140:
            return 36.0
        return 60.0

    def get_intersection_penalty(self, street_count: float) -> float:
        return max(street_count - 2.0, 0.0) * 2.5 * self.comfort_factor


class WeatherMode(CalmMode):
    def get_weight(self, u, v, edge_data, lon_lat_points=None):
        length = _as_float(edge_data.get("length"), 1.0)
        highway = _normalize_highway(edge_data.get("highway", "unclassified"))
        stress = HIGHWAY_STRESS.get(highway, 1.5)
        stress = _weather_adjusted_stress(highway, stress, self.weather, stronger=True)
        effective_stress = 1.0 + (stress - 1.0) * self.comfort_factor
        return max(length * effective_stress, 0.1)


class SafeMode(RouteMode):
    def get_weight(self, u, v, edge_data, lon_lat_points=None):
        length = _as_float(edge_data.get("length"), 1.0)
        highway = _normalize_highway(edge_data.get("highway", "unclassified"))
        stress = HIGHWAY_STRESS.get(highway, 1.5)

        # Avoid isolated or less visible foot paths for safety.
        if highway in ("path", "footway"):
            stress *= 1.5

        weight = max(length * stress, 0.1)
        if is_edge_unsafe(lon_lat_points):
            # Strongly discourage dangerous zones without making route impossible.
            weight *= 100.0
        return weight * self.comfort_factor

    def get_turn_penalty(self, delta: float) -> float:
        return CalmMode().get_turn_penalty(delta)

    def get_intersection_penalty(self, street_count: float) -> float:
        return CalmMode().get_intersection_penalty(street_count)


class AccessibilityMode(RouteMode):
    def get_weight(self, u, v, edge_data, lon_lat_points=None):
        return get_accessibility_weight(edge_data) * self.comfort_factor

    def get_turn_penalty(self, delta: float) -> float:
        return get_accessibility_turn_penalty(delta)

    def get_intersection_penalty(self, street_count: float) -> float:
        return get_accessibility_intersection_penalty(street_count)


class DogMode(RouteMode):
    def get_weight(self, u, v, edge_data, lon_lat_points=None):
        return get_dog_weight(edge_data, self.dog_sub_mode or "relax") * self.comfort_factor

    def get_turn_penalty(self, delta: float) -> float:
        return get_dog_turn_penalty(delta)

    def get_intersection_penalty(self, street_count: float) -> float:
        return get_dog_intersection_penalty(street_count)


def get_mode_instance(mode_name: str, weather: dict, dog_sub_mode: str, preference_bias: int = 50) -> RouteMode:
    mode_name = (mode_name or "calm").lower()
    if mode_name == "safe":
        return SafeMode(weather, dog_sub_mode, preference_bias)
    if mode_name == "accessibility":
        return AccessibilityMode(weather, dog_sub_mode, preference_bias)
    if mode_name == "dog":
        return DogMode(weather, dog_sub_mode, preference_bias)
    if mode_name == "weather":
        return WeatherMode(weather, dog_sub_mode, preference_bias)
    return CalmMode(weather, dog_sub_mode, preference_bias)
