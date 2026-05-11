from routing_utils import _as_float, _normalize_highway


def get_dog_weight(edge_data: dict, sub_mode: str) -> float:
    """
    Calculate route weight for dog-friendly navigation.

    Lower weight = more preferred route.

    Parameters:
    ----------
    edge_data : dict
        Road/edge information from map data.

    sub_mode : str
        Type of dog walk:
        - quick           -> short toilet break
        - relax           -> balanced/default walk
        - long            -> longer scenic walk
        - quiet           -> avoid noisy roads
        - park_priority   -> strongly prefer parks/green areas

    Returns:
    -------
    float
        Final weighted cost for the edge.
    """

    # Distance/length of the edge in meters.
    # Default to 1.0 if missing.
    length = _as_float(edge_data.get("length"), 1.0)

    # Normalize highway type for consistent comparisons.
    highway = _normalize_highway(
        edge_data.get("highway", "unclassified")
    )

    # Leisure tag helps detect parks or green spaces.
    leisure = edge_data.get("leisure", "")

    # Base stress value.
    # Lower stress = more dog-friendly.
    stress = 1.0

    # ---------------------------------------------------------
    # Parks and green areas are highly preferred for dogs.
    # ---------------------------------------------------------
    if (
        isinstance(leisure, str)
        and leisure.lower() in (
            "park",
            "garden",
            "nature_reserve",
            "pitch",
        )
    ):
        stress = 0.1

    # ---------------------------------------------------------
    # Evaluate road type suitability.
    # ---------------------------------------------------------

    # Very dog-friendly walking paths.
    if highway in ("footway", "pedestrian", "path"):
        stress = min(stress, 0.3)

    # Cycleways are okay but may contain fast bikes.
    elif highway in ("cycleway",):
        stress = 0.8

    # Quiet residential streets are acceptable.
    elif highway in ("living_street", "residential"):
        stress = 0.7

    # Service roads/unclassified roads are less ideal.
    elif highway in ("service", "unclassified"):
        stress = 1.5

    # Medium traffic roads are stressful for dogs.
    elif highway in ("tertiary", "secondary"):
        stress = 5.0

    # Major highways are extremely noisy and unsafe.
    elif highway in ("primary", "trunk", "motorway"):
        stress = 20.0

    # ---------------------------------------------------------
    # Modify behavior depending on walk style.
    # ---------------------------------------------------------

    if sub_mode == "quick":
        # Quick walks should avoid large detours.
        # Move stress slightly closer to neutral.
        stress = (stress + 1.0) / 2.0

    elif sub_mode == "long":
        # Long walks are willing to detour more
        # if the route is especially pleasant.
        if stress < 0.5:
            stress *= 0.5

    elif sub_mode == "quiet":
        # Strongly avoid loud arterial roads.
        if highway in (
            "primary",
            "secondary",
            "trunk",
            "motorway",
        ):
            stress *= 1.5

        # Extra preference for calm walking areas.
        if highway in (
            "footway",
            "pedestrian",
            "path",
            "living_street",
        ):
            stress *= 0.75

    elif sub_mode == "park_priority":
        # Strongly prefer parks and green areas.
        if (
            isinstance(leisure, str)
            and leisure.lower() in (
                "park",
                "garden",
                "nature_reserve",
                "pitch",
            )
        ):
            stress *= 0.3
        else:
            # Slight penalty for non-park routes.
            stress *= 1.25

    # Final route cost:
    # distance × environmental stress.
    # Minimum value prevents zero-weight edges.
    return max(length * stress, 0.1)


def get_dog_turn_penalty(delta: float) -> float:
    """
    Penalize sharp turns for dog routes.

    Parameters:
    ----------
    delta : float
        Turn angle in degrees.

    Returns:
    -------
    float
        Turn penalty value.
    """

    # Small turns are ignored.
    if delta < 45:
        return 0.0

    # Larger turns get moderate penalty.
    return 10.0


def get_dog_intersection_penalty(street_count: float) -> float:
    """
    Penalize complex intersections.

    More connecting streets usually means:
    - more traffic
    - more noise
    - more crossing difficulty for dogs

    Parameters:
    ----------
    street_count : float
        Number of connected streets.

    Returns:
    -------
    float
        Intersection penalty.
    """

    # Penalize intersections bigger than 2-way.
    return max(street_count - 2.0, 0.0) * 2.0