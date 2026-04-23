from routing_utils import _as_float, _normalize_highway

def get_dog_weight(edge_data: dict, sub_mode: str) -> float:
    """
    sub_mode can be: quick, relax, long, quiet, park_priority.
    We will adjust the weight based on this.
    """
    length = _as_float(edge_data.get("length"), 1.0)
    highway = _normalize_highway(edge_data.get("highway", "unclassified"))
    leisure = edge_data.get("leisure", "")
    
    # Dogs love parks, avoid cars
    stress = 1.0
    
    # Highly prioritize parks, grass
    if isinstance(leisure, str) and leisure.lower() in ("park", "garden", "nature_reserve", "pitch"):
        stress = 0.1
    
    # Highway evaluation
    if highway in ("footway", "pedestrian", "path"):
        stress = min(stress, 0.3)
    elif highway in ("cycleway",):
        stress = 0.8
    elif highway in ("living_street", "residential"):
        stress = 0.7
    elif highway in ("service", "unclassified"):
        stress = 1.5
    elif highway in ("tertiary", "secondary"):
        stress = 5.0
    elif highway in ("primary", "trunk", "motorway"):
        stress = 20.0 # loud, stressful for dogs
        
    # Adjust based on sub_mode
    if sub_mode == 'quick':
        # Don't deviate too much for quick toilet break
        stress = (stress + 1.0) / 2.0 
    elif sub_mode == 'long':
        # Willing to walk far out of the way for parks
        if stress < 0.5:
            stress *= 0.5
    elif sub_mode == 'quiet':
        # Strongly avoid noisy arterial roads.
        if highway in ("primary", "secondary", "trunk", "motorway"):
            stress *= 1.5
        if highway in ("footway", "pedestrian", "path", "living_street"):
            stress *= 0.75
    elif sub_mode == 'park_priority':
        # Bias harder toward parks/green edges.
        if isinstance(leisure, str) and leisure.lower() in ("park", "garden", "nature_reserve", "pitch"):
            stress *= 0.3
        else:
            stress *= 1.25
            
    return max(length * stress, 0.1)

def get_dog_turn_penalty(delta: float) -> float:
    if delta < 45:
        return 0.0
    return 10.0 # moderate penalty

def get_dog_intersection_penalty(street_count: float) -> float:
    return max(street_count - 2.0, 0.0) * 2.0
