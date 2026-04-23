from routing_utils import _as_float, _normalize_highway

def get_accessibility_weight(edge_data: dict) -> float:
    length = _as_float(edge_data.get("length"), 1.0)
    highway = _normalize_highway(edge_data.get("highway", "unclassified"))
    
    # Base stress is low for pedestrian areas, high for rough/major roads
    stress = 1.0
    
    if highway in ("footway", "pedestrian", "path"):
        # Prefer sidewalks and pedestrian areas
        stress = 0.5
    elif highway in ("steps",):
        # Strongly avoid steps for accessibility
        stress = 20.0
    elif highway in ("cycleway",):
        stress = 1.2
    elif highway in ("living_street", "residential"):
        stress = 1.0
    elif highway in ("service", "unclassified", "tertiary"):
        stress = 2.0
    elif highway in ("secondary", "primary", "trunk", "motorway"):
        stress = 10.0
    # Additional logic for slope, smooth vs rough surfaces can be added here
    # assuming we had surface tags
    surface = edge_data.get("surface", "")
    if isinstance(surface, str):
        if surface.lower() in ("paved", "asphalt", "concrete", "paving_stones"):
            stress *= 0.8  # prefer smooth
        elif surface.lower() in ("unpaved", "gravel", "dirt", "cobblestone"):
            stress *= 3.0  # avoid rough
            
    return max(length * stress, 0.1)

def get_accessibility_turn_penalty(delta: float) -> float:
    # Elderly/injured/wheelchairs might find sharp turns or many crossings difficult
    # We penalize more heavily compared to calm mode
    if delta < 25:
        return 0.0
    if delta < 45:
        return 15.0
    if delta < 90:
        return 30.0
    return 60.0

def get_accessibility_intersection_penalty(street_count: float) -> float:
    # Crossings are much harder
    return max(street_count - 2.0, 0.0) * 5.0
