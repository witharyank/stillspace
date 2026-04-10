from __future__ import annotations

import ast
import heapq
import logging
import math
from typing import Dict, Iterable, List, Optional, Tuple

import networkx as nx
import osmnx as ox
from flask import Flask, jsonify, render_template, request
from shapely import wkt

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("stillspace")

logger.info("Loading graph from city.graphml...")
G = ox.load_graphml("city.graphml")
logger.info("Graph loaded: %s nodes, %s edges", len(G.nodes), len(G.edges))

AVERAGE_WALK_MPS = 1.4

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

EdgeRef = Tuple[int, int, int]


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


def _calm_base_weight(edge_data: Dict[str, object]) -> float:
    length = _as_float(edge_data.get("length"), 1.0)
    highway = _normalize_highway(edge_data.get("highway", "unclassified"))
    stress = HIGHWAY_STRESS.get(highway, 1.5)
    return max(length * stress, 0.1)


def _initialize_edge_metrics() -> None:
    for _, _, _, edge_data in G.edges(keys=True, data=True):
        edge_data["length"] = _as_float(edge_data.get("length"), 1.0)
        edge_data["calm_base_weight"] = _calm_base_weight(edge_data)


def _distance_sq(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return dx * dx + dy * dy


def _edge_lon_lat_points(u: int, v: int, edge_data: Dict[str, object]) -> List[Tuple[float, float]]:
    ux = _as_float(G.nodes[u].get("x"))
    uy = _as_float(G.nodes[u].get("y"))
    vx = _as_float(G.nodes[v].get("x"))
    vy = _as_float(G.nodes[v].get("y"))
    points: List[Tuple[float, float]] = []

    geometry = edge_data.get("geometry")
    if geometry is not None:
        try:
            if isinstance(geometry, str):
                geometry = wkt.loads(geometry)
            if hasattr(geometry, "coords"):
                points = [(float(x), float(y)) for x, y in geometry.coords]
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
) -> float:
    prev_data = G.get_edge_data(prev_u, curr_u, prev_k)
    next_data = G.get_edge_data(curr_u, next_v, next_k)
    if not prev_data or not next_data:
        return 0.0

    prev_points = _edge_lon_lat_points(prev_u, curr_u, prev_data)
    next_points = _edge_lon_lat_points(curr_u, next_v, next_data)
    if len(prev_points) < 2 or len(next_points) < 2:
        return 0.0

    incoming = _bearing_degrees(prev_points[-2], prev_points[-1])
    outgoing = _bearing_degrees(next_points[0], next_points[1])
    delta = _turn_angle(incoming, outgoing)

    if delta < 25:
        return 0.0
    if delta < 55:
        return 8.0
    if delta < 95:
        return 18.0
    if delta < 140:
        return 36.0
    return 60.0


def _intersection_penalty_meters(node: int) -> float:
    street_count = _as_float(G.nodes[node].get("street_count"), 0.0)
    return max(street_count - 2.0, 0.0) * 2.5


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


def _calm_edge_path(origin: int, destination: int) -> Tuple[List[EdgeRef], float]:
    if origin == destination:
        return [], 0.0

    # State-space Dijkstra: cost depends on the previously traversed edge because of turn penalties.
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
            edge_cost = _as_float(next_edge_data.get("calm_base_weight"), 1.0)
            turn_cost = 0.0
            if prev_node is not None and prev_key is not None:
                turn_cost = _turn_penalty_meters(prev_node, curr_node, prev_key, next_node, next_key)
            intersection_cost = _intersection_penalty_meters(curr_node)
            total_step_cost = edge_cost + turn_cost + intersection_cost

            next_state = (next_node, curr_node, next_key)
            new_cost = curr_cost + total_step_cost
            if new_cost < dist.get(next_state, float("inf")):
                dist[next_state] = new_cost
                parent[next_state] = (state, (curr_node, next_node, next_key))
                heapq.heappush(heap, (new_cost, next_node, curr_node, next_key))

    if best_destination_state is None:
        raise nx.NetworkXNoPath(f"No calm route between {origin} and {destination}")

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

    # Merge edge geometries into one continuous LineString-like coordinate list for Leaflet.
    route_coords: List[List[float]] = []
    for idx, (u, v, k) in enumerate(edge_path):
        edge_data = G.get_edge_data(u, v, k)
        if not edge_data:
            continue

        lon_lat_points = _edge_lon_lat_points(u, v, edge_data)
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
    return {
        "dist_km": round(distance_meters / 1000.0, 2),
        "time_min": round(minutes),
    }


def _comparison(shortest_dist: float, calm_dist: float) -> Dict[str, float]:
    extra_m = calm_dist - shortest_dist
    shortest_time = (shortest_dist / AVERAGE_WALK_MPS) / 60.0
    calm_time = (calm_dist / AVERAGE_WALK_MPS) / 60.0
    pct = (extra_m / shortest_dist * 100.0) if shortest_dist else 0.0
    return {
        "extra_dist_km": round(extra_m / 1000.0, 2),
        "extra_time_min": round(calm_time - shortest_time),
        "dist_diff_pct": round(pct, 1),
    }


def _edge_path_to_nodes(origin: int, edge_path: List[EdgeRef]) -> List[int]:
    if not edge_path:
        return [origin]
    nodes = [origin]
    for _, v, _ in edge_path:
        nodes.append(v)
    return nodes


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/smart_route", methods=["POST"])
def smart_route():
    data = request.get_json(silent=True) or {}
    required = ("start_lat", "start_lon", "end_lat", "end_lon")
    missing = [key for key in required if key not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    start_lat = _as_float(data["start_lat"])
    start_lon = _as_float(data["start_lon"])
    end_lat = _as_float(data["end_lat"])
    end_lon = _as_float(data["end_lon"])
    calm_mode_enabled = bool(data.get("calm_mode", False))

    logger.info(
        "Routing request calm_mode=%s start=(%.6f, %.6f) end=(%.6f, %.6f)",
        calm_mode_enabled,
        start_lat,
        start_lon,
        end_lat,
        end_lon,
    )

    origin = ox.distance.nearest_nodes(G, start_lon, start_lat)
    destination = ox.distance.nearest_nodes(G, end_lon, end_lat)
    logger.info("Nearest graph nodes origin=%s destination=%s", origin, destination)

    try:
        shortest_nodes = nx.shortest_path(G, origin, destination, weight="length")
        shortest_edges = _node_path_to_edge_path(shortest_nodes, "length")

        calm_edges, calm_cost = _calm_edge_path(origin, destination)
        calm_nodes = _edge_path_to_nodes(origin, calm_edges)

        shortest_coords = _edge_path_to_leaflet_coords(shortest_edges, fallback_node=origin)
        calm_coords = _edge_path_to_leaflet_coords(calm_edges, fallback_node=origin)

        shortest_dist = _path_length_meters(shortest_edges)
        calm_dist = _path_length_meters(calm_edges)

        logger.info("Shortest node path (%s nodes): %s", len(shortest_nodes), shortest_nodes)
        logger.info("Calm node path (%s nodes): %s", len(calm_nodes), calm_nodes)
        logger.info("Shortest edges (%s): %s", len(shortest_edges), shortest_edges)
        logger.info("Calm edges (%s): %s", len(calm_edges), calm_edges)
        logger.info("Shortest route coords: %s points", len(shortest_coords))
        logger.info("Calm route coords: %s points", len(calm_coords))
        if shortest_coords:
            logger.info(
                "Shortest coords start=%s end=%s",
                shortest_coords[0],
                shortest_coords[-1],
            )
            logger.debug("Shortest route coords full: %s", shortest_coords)
        if calm_coords:
            logger.info(
                "Calm coords start=%s end=%s",
                calm_coords[0],
                calm_coords[-1],
            )
            logger.debug("Calm route coords full: %s", calm_coords)
        logger.info(
            "Route lengths shortest=%.0fm calm=%.0fm calm_cost=%.1f",
            shortest_dist,
            calm_dist,
            calm_cost,
        )

        return jsonify(
            {
                "fastest_route": shortest_coords,
                "calm_route": calm_coords,
                "shortest_stats": _stats(shortest_dist),
                "calm_stats": _stats(calm_dist),
                "comparison": _comparison(shortest_dist, calm_dist),
            }
        )
    except nx.NetworkXNoPath:
        logger.warning("No path found between %s and %s", origin, destination)
        return jsonify({"error": "No path found between selected points."}), 404
    except Exception:
        logger.exception("Unexpected routing failure")
        return jsonify({"error": "Failed to calculate route."}), 500


_initialize_edge_metrics()

if __name__ == "__main__":
    app.run(debug=True)
