from __future__ import annotations

import heapq
import logging
import math
import os
import time
import uuid
from typing import Dict, Iterable, List, Optional, Tuple

import networkx as nx
import osmnx as ox
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from shapely import wkt

from route_modes import get_mode_instance
from routing_utils import _as_float
from safety_zones import get_safety_zones_geojson
from weather_service import get_current_weather
import database

load_dotenv()

database.init_db()

app = Flask(__name__)

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("stillspace")

GRAPH_PATH = os.getenv("GRAPH_PATH", "city.graphml")
AVERAGE_WALK_MPS = 1.4
MAX_SNAP_DISTANCE_M = float(os.getenv("MAX_SNAP_DISTANCE_M", "250"))
VALID_ROUTE_MODES = {"fastest", "calm", "safe", "accessibility", "dog", "weather"}
VALID_DOG_SUB_MODES = {"quick", "relax", "long", "quiet", "park_priority"}

logger.info("Loading graph from %s ...", GRAPH_PATH)
G = ox.load_graphml(GRAPH_PATH)
logger.info("Graph loaded: %s nodes, %s edges", len(G.nodes), len(G.edges))

_all_lats = [_as_float(data.get("y")) for _, data in G.nodes(data=True)]
_all_lons = [_as_float(data.get("x")) for _, data in G.nodes(data=True)]
GRAPH_BBOX = {
    "min_lat": min(_all_lats),
    "max_lat": max(_all_lats),
    "min_lon": min(_all_lons),
    "max_lon": max(_all_lons),
}

EdgeRef = Tuple[int, int, int]
_EDGE_POINTS_CACHE: Dict[EdgeRef, List[Tuple[float, float]]] = {}


def _json_error(
    message: str,
    status: int = 400,
    *,
    code: str = "bad_request",
    request_id: Optional[str] = None,
    details: Optional[Dict[str, object]] = None,
):
    payload: Dict[str, object] = {"error": message, "code": code}
    if request_id:
        payload["request_id"] = request_id
    if details:
        payload["details"] = details
    return jsonify(payload), status


def _distance_sq(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def _edge_lon_lat_points(
    u: int,
    v: int,
    edge_data: Dict[str, object],
    edge_key: Optional[int] = None,
) -> List[Tuple[float, float]]:
    cache_key = (u, v, edge_key) if edge_key is not None else None
    if cache_key and cache_key in _EDGE_POINTS_CACHE:
        return _EDGE_POINTS_CACHE[cache_key]

    ux = _as_float(G.nodes[u].get("x"))
    uy = _as_float(G.nodes[u].get("y"))
    vx = _as_float(G.nodes[v].get("x"))
    vy = _as_float(G.nodes[v].get("y"))
    points: List[Tuple[float, float]] = []

    geometry = edge_data.get("geometry")
    if geometry is not None:
        try:
            parsed = wkt.loads(geometry) if isinstance(geometry, str) else geometry
            if hasattr(parsed, "coords"):
                points = [(float(x), float(y)) for x, y in parsed.coords]
        except Exception:
            points = []

    if len(points) < 2:
        points = [(ux, uy), (vx, vy)]

    start = points[0]
    end = points[-1]
    source = (ux, uy)
    target = (vx, vy)

    forward_cost = _distance_sq(start, source) + _distance_sq(end, target)
    reverse_cost = _distance_sq(start, target) + _distance_sq(end, source)
    if reverse_cost < forward_cost:
        points.reverse()

    if cache_key:
        _EDGE_POINTS_CACHE[cache_key] = points

    return points


def _bearing_degrees(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    angle = math.degrees(math.atan2(dy, dx))
    return (angle + 360.0) % 360.0


def _turn_angle(incoming_bearing: float, outgoing_bearing: float) -> float:
    delta = abs(outgoing_bearing - incoming_bearing) % 360.0
    if delta > 180.0:
        delta = 360.0 - delta
    return delta


def _turn_penalty_meters(
    prev_u: int,
    curr_u: int,
    prev_k: int,
    next_v: int,
    next_k: int,
    route_mode,
) -> float:
    prev_data = G.get_edge_data(prev_u, curr_u, prev_k)
    next_data = G.get_edge_data(curr_u, next_v, next_k)
    if not prev_data or not next_data:
        return 0.0

    prev_points = _edge_lon_lat_points(prev_u, curr_u, prev_data, prev_k)
    next_points = _edge_lon_lat_points(curr_u, next_v, next_data, next_k)
    if len(prev_points) < 2 or len(next_points) < 2:
        return 0.0

    incoming = _bearing_degrees(prev_points[-2], prev_points[-1])
    outgoing = _bearing_degrees(next_points[0], next_points[1])
    delta = _turn_angle(incoming, outgoing)
    return route_mode.get_turn_penalty(delta)


def _intersection_penalty_meters(node: int, route_mode) -> float:
    street_count = _as_float(G.nodes[node].get("street_count"), 0.0)
    return route_mode.get_intersection_penalty(street_count)


def _pick_best_edge(u: int, v: int, weight_attr: str) -> EdgeRef:
    edge_candidates = G.get_edge_data(u, v)
    if not edge_candidates:
        raise ValueError(f"No edge data for pair ({u}, {v})")

    best_k = min(
        edge_candidates,
        key=lambda k: _as_float(edge_candidates[k].get(weight_attr), float("inf")),
    )
    return u, v, best_k


def _node_path_to_edge_path(node_path: List[int], weight_attr: str) -> List[EdgeRef]:
    if len(node_path) < 2:
        return []
    edges: List[EdgeRef] = []
    for u, v in zip(node_path[:-1], node_path[1:]):
        edges.append(_pick_best_edge(u, v, weight_attr))
    return edges


def _smart_edge_path(origin: int, destination: int, route_mode) -> Tuple[List[EdgeRef], float]:
    if origin == destination:
        return [], 0.0

    start_state = (origin, None, None)
    dist: Dict[Tuple[Optional[int], Optional[int], Optional[int]], float] = {start_state: 0.0}
    parent: Dict[
        Tuple[Optional[int], Optional[int], Optional[int]],
        Tuple[Tuple[Optional[int], Optional[int], Optional[int]], EdgeRef],
    ] = {}
    heap: List[Tuple[float, int, Optional[int], Optional[int]]] = [(0.0, origin, None, None)]
    best_destination_state: Optional[Tuple[Optional[int], Optional[int], Optional[int]]] = None

    while heap:
        curr_cost, curr_node, prev_node, prev_key = heapq.heappop(heap)
        state = (curr_node, prev_node, prev_key)
        if curr_cost > dist.get(state, float("inf")):
            continue

        if curr_node == destination:
            best_destination_state = state
            break

        for _, next_node, next_key, next_edge_data in G.out_edges(curr_node, keys=True, data=True):
            lon_lat_points = _edge_lon_lat_points(curr_node, next_node, next_edge_data, next_key)
            edge_cost = route_mode.get_weight(curr_node, next_node, next_edge_data, lon_lat_points)

            turn_cost = 0.0
            if prev_node is not None and prev_key is not None:
                turn_cost = _turn_penalty_meters(
                    prev_node,
                    curr_node,
                    prev_key,
                    next_node,
                    next_key,
                    route_mode,
                )
            intersection_cost = _intersection_penalty_meters(curr_node, route_mode)
            total_step_cost = edge_cost + turn_cost + intersection_cost

            next_state = (next_node, curr_node, next_key)
            new_cost = curr_cost + total_step_cost
            if new_cost < dist.get(next_state, float("inf")):
                dist[next_state] = new_cost
                parent[next_state] = (state, (curr_node, next_node, next_key))
                heapq.heappush(heap, (new_cost, next_node, curr_node, next_key))

    if best_destination_state is None:
        raise nx.NetworkXNoPath(f"No smart route between {origin} and {destination}")

    edge_path: List[EdgeRef] = []
    cursor = best_destination_state
    while cursor in parent:
        prev_state, edge = parent[cursor]
        edge_path.append(edge)
        cursor = prev_state
    edge_path.reverse()
    return edge_path, dist[best_destination_state]


def _edge_path_to_leaflet_coords(edge_path: List[EdgeRef], fallback_node: Optional[int] = None) -> List[List[float]]:
    if not edge_path:
        if fallback_node is None:
            return []
        return [[_as_float(G.nodes[fallback_node]["y"]), _as_float(G.nodes[fallback_node]["x"])]]

    route_coords: List[List[float]] = []
    for idx, (u, v, k) in enumerate(edge_path):
        edge_data = G.get_edge_data(u, v, k)
        if not edge_data:
            continue

        lon_lat_points = _edge_lon_lat_points(u, v, edge_data, k)
        lat_lon_points = [[lat, lon] for lon, lat in lon_lat_points]

        if idx == 0:
            route_coords.extend(lat_lon_points)
            continue

        if route_coords and lat_lon_points:
            prev = route_coords[-1]
            curr = lat_lon_points[0]
            same = abs(prev[0] - curr[0]) < 1e-9 and abs(prev[1] - curr[1]) < 1e-9
            if same:
                route_coords.extend(lat_lon_points[1:])
            else:
                route_coords.extend(lat_lon_points)
    return route_coords


def _path_length_meters(edge_path: Iterable[EdgeRef]) -> float:
    total = 0.0
    for u, v, k in edge_path:
        edge_data = G.get_edge_data(u, v, k)
        if edge_data:
            total += _as_float(edge_data.get("length"), 0.0)
    return total


def _stats(distance_meters: float) -> Dict[str, float]:
    minutes = (distance_meters / AVERAGE_WALK_MPS) / 60.0
    return {"dist_km": round(distance_meters / 1000.0, 2), "time_min": round(minutes)}


def _comparison(shortest_dist: float, smart_dist: float) -> Dict[str, float]:
    extra_m = smart_dist - shortest_dist
    shortest_time = (shortest_dist / AVERAGE_WALK_MPS) / 60.0
    smart_time = (smart_dist / AVERAGE_WALK_MPS) / 60.0
    pct = (extra_m / shortest_dist * 100.0) if shortest_dist else 0.0
    return {
        "extra_dist_km": round(extra_m / 1000.0, 2),
        "extra_time_min": round(smart_time - shortest_time),
        "dist_diff_pct": round(pct, 1),
    }


def _coords_close(a: List[float], b: List[float], tolerance: float = 1e-6) -> bool:
    return abs(a[0] - b[0]) < tolerance and abs(a[1] - b[1]) < tolerance


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _connector_segments(
    core_route_coords: List[List[float]],
    start_click: List[float],
    end_click: List[float],
) -> Dict[str, Optional[List[List[float]]]]:
    if not core_route_coords:
        segment = [start_click, end_click] if not _coords_close(start_click, end_click) else None
        return {"start": segment, "end": None}

    start_segment = None
    end_segment = None
    if not _coords_close(core_route_coords[0], start_click):
        start_segment = [start_click, core_route_coords[0]]
    if not _coords_close(core_route_coords[-1], end_click):
        end_segment = [core_route_coords[-1], end_click]
    return {"start": start_segment, "end": end_segment}


def _parse_float_input(data: Dict[str, object], key: str) -> float:
    if key not in data:
        raise ValueError(f"Missing required field: {key}")
    value = _as_float(data.get(key), float("nan"))
    if not math.isfinite(value):
        raise ValueError(f"Invalid numeric value for {key}")
    return value


def _validate_coordinates(start_lat: float, start_lon: float, end_lat: float, end_lon: float) -> None:
    if not (-90.0 <= start_lat <= 90.0 and -90.0 <= end_lat <= 90.0):
        raise ValueError("Latitude must be between -90 and 90.")
    if not (-180.0 <= start_lon <= 180.0 and -180.0 <= end_lon <= 180.0):
        raise ValueError("Longitude must be between -180 and 180.")


def _extract_mode_params(data: Dict[str, object]) -> Tuple[str, str]:
    route_mode_name = str(data.get("route_mode", "calm")).strip().lower()
    if route_mode_name not in VALID_ROUTE_MODES:
        raise ValueError(f"Unsupported route_mode: {route_mode_name}")

    dog_sub_mode = str(data.get("dog_sub_mode", "relax")).strip().lower()
    if dog_sub_mode not in VALID_DOG_SUB_MODES:
        raise ValueError(f"Unsupported dog_sub_mode: {dog_sub_mode}")

    return route_mode_name, dog_sub_mode


def _extract_preference_bias(data: Dict[str, object]) -> int:
    raw = data.get("preference_bias", 50)
    value = int(_as_float(raw, 50.0))
    if value < 0 or value > 100:
        raise ValueError("preference_bias must be between 0 and 100.")
    return value


@app.route("/")
def home():
    carto_api_key = os.getenv("CARTO_API_KEY", "")
    return render_template("index.html", carto_api_key=carto_api_key)


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "graph_path": GRAPH_PATH,
            "graph_nodes": len(G.nodes),
            "graph_edges": len(G.edges),
            "graph_bbox": GRAPH_BBOX,
            "max_snap_distance_m": MAX_SNAP_DISTANCE_M,
        }
    )


@app.route("/api/safety_zones")
def safety_zones():
    return jsonify(get_safety_zones_geojson())

@app.route("/api/history")
def search_history():
    recent = database.get_recent_searches()
    return jsonify({"history": recent})

@app.route("/api/history/<int:search_id>", methods=["DELETE"])
def delete_search_history(search_id):
    success = database.delete_search(search_id)
    if success:
        return jsonify({"success": True, "message": "Search history deleted."})
    return jsonify({"success": False, "error": "History not found."}), 404


@app.route("/smart_route", methods=["POST"])
def smart_route():
    started_at = time.perf_counter()
    request_id = uuid.uuid4().hex[:8]

    data = request.get_json(silent=True)
    if data is None:
        return _json_error(
            "Expected JSON body.",
            400,
            code="invalid_json",
            request_id=request_id,
        )

    try:
        start_lat = _parse_float_input(data, "start_lat")
        start_lon = _parse_float_input(data, "start_lon")
        end_lat = _parse_float_input(data, "end_lat")
        end_lon = _parse_float_input(data, "end_lon")
        _validate_coordinates(start_lat, start_lon, end_lat, end_lon)
        route_mode_name, dog_sub_mode = _extract_mode_params(data)
        preference_bias = _extract_preference_bias(data)
    except ValueError as exc:
        return _json_error(str(exc), 400, code="validation_error", request_id=request_id)

    logger.info(
        "request=%s mode=%s start=(%.6f, %.6f) end=(%.6f, %.6f)",
        request_id,
        route_mode_name,
        start_lat,
        start_lon,
        end_lat,
        end_lon,
    )

    try:
        origin = ox.distance.nearest_nodes(G, start_lon, start_lat)
        destination = ox.distance.nearest_nodes(G, end_lon, end_lat)
    except Exception:
        logger.exception("request=%s nearest_nodes failure", request_id)
        return _json_error(
            "Unable to find nearest routable nodes for the selected points.",
            400,
            code="nearest_node_failure",
            request_id=request_id,
        )

    weather = get_current_weather(start_lat, start_lon)
    origin_lat = _as_float(G.nodes[origin].get("y"))
    origin_lon = _as_float(G.nodes[origin].get("x"))
    destination_lat = _as_float(G.nodes[destination].get("y"))
    destination_lon = _as_float(G.nodes[destination].get("x"))

    start_snap_distance_m = _haversine_m(start_lat, start_lon, origin_lat, origin_lon)
    end_snap_distance_m = _haversine_m(end_lat, end_lon, destination_lat, destination_lon)
    if start_snap_distance_m > MAX_SNAP_DISTANCE_M or end_snap_distance_m > MAX_SNAP_DISTANCE_M:
        return _json_error(
            "Selected point is outside supported map coverage. Choose points closer to mapped streets.",
            400,
            code="outside_coverage",
            request_id=request_id,
            details={
                "start_snap_distance_m": round(start_snap_distance_m, 1),
                "end_snap_distance_m": round(end_snap_distance_m, 1),
                "max_snap_distance_m": MAX_SNAP_DISTANCE_M,
                "graph_bbox": GRAPH_BBOX,
            },
        )

    try:
        shortest_nodes = nx.shortest_path(G, origin, destination, weight="length")
        shortest_edges = _node_path_to_edge_path(shortest_nodes, "length")
        fastest_route_core = _edge_path_to_leaflet_coords(shortest_edges, fallback_node=origin)
        click_start = [start_lat, start_lon]
        click_end = [end_lat, end_lon]
        fastest_route = fastest_route_core
        shortest_dist = _path_length_meters(shortest_edges)
        fastest_connectors = _connector_segments(fastest_route_core, click_start, click_end)

        smart_route_coords: List[List[float]] = []
        smart_route_core: List[List[float]] = []
        smart_dist = 0.0
        smart_cost = 0.0
        smart_connectors = {"start": None, "end": None}

        if route_mode_name != "fastest":
            mode_instance = get_mode_instance(route_mode_name, weather, dog_sub_mode, preference_bias)
            smart_edges, smart_cost = _smart_edge_path(origin, destination, mode_instance)
            smart_route_core = _edge_path_to_leaflet_coords(smart_edges, fallback_node=origin)
            smart_route_coords = smart_route_core
            smart_dist = _path_length_meters(smart_edges)
            smart_connectors = _connector_segments(smart_route_core, click_start, click_end)

        response_payload: Dict[str, object] = {
            "request_id": request_id,
            "mode_requested": route_mode_name,
            "mode_used": route_mode_name,
            "dog_sub_mode": dog_sub_mode,
            "preference_bias": preference_bias,
            "weather": weather,
            "fastest_route": fastest_route,
            "smart_route": smart_route_coords,
            "fastest_route_core": fastest_route_core,
            "smart_route_core": smart_route_core,
            "connectors": {
                "fastest": fastest_connectors,
                "smart": smart_connectors,
            },
            "snapped_nodes": {
                "origin": [origin_lat, origin_lon],
                "destination": [destination_lat, destination_lon],
            },
            "snap_distances_m": {
                "start": round(start_snap_distance_m, 1),
                "end": round(end_snap_distance_m, 1),
            },
            "shortest_stats": _stats(shortest_dist),
            "smart_stats": _stats(smart_dist) if smart_route_coords else None,
            "comparison": _comparison(shortest_dist, smart_dist) if smart_route_coords else None,
            # Additional structured contract for future clients:
            "routes": {
                "fastest": fastest_route,
                "smart": smart_route_coords,
            },
            "stats": {
                "fastest": _stats(shortest_dist),
                "smart": _stats(smart_dist) if smart_route_coords else None,
                "comparison": _comparison(shortest_dist, smart_dist) if smart_route_coords else None,
            },
        }

        duration_ms = (time.perf_counter() - started_at) * 1000.0
        logger.info(
            "request=%s success mode=%s fastest_points=%s smart_points=%s smart_cost=%.2f duration_ms=%.1f",
            request_id,
            route_mode_name,
            len(fastest_route),
            len(smart_route_coords),
            smart_cost,
            duration_ms,
        )
        logger.debug("request=%s fastest_route=%s", request_id, fastest_route)
        logger.debug("request=%s smart_route=%s", request_id, smart_route_coords)

        # Store in search history
        database.insert_search(start_lat, start_lon, end_lat, end_lon, route_mode_name)

        return jsonify(response_payload)
    except nx.NetworkXNoPath:
        logger.warning("request=%s no_path origin=%s destination=%s", request_id, origin, destination)
        return _json_error(
            "No path found between selected points.",
            404,
            code="no_path",
            request_id=request_id,
        )
    except Exception:
        logger.exception("request=%s unexpected_routing_failure", request_id)
        return _json_error(
            "Failed to calculate route.",
            500,
            code="routing_failure",
            request_id=request_id,
        )


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(debug=debug, host=host, port=port)
