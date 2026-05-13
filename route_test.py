# ==========================================================
# IMPORTS
# ==========================================================

import os  # Used for checking file existence
import random  # Used for generating random environmental values
from datetime import datetime  # Used to get current system time

import matplotlib.pyplot as plt  # Used for plotting routes visually
import networkx as nx  # Used for graph algorithms like shortest path
import osmnx as ox  # Used for loading and working with OpenStreetMap graphs


# ==========================================================
# STILLSPACE PROTOTYPE
# Smart Calm Route Recommendation System
# ==========================================================

"""
This project simulates a calm-route navigation system.

Instead of only finding the shortest route,
the system also tries to find the calmest route
based on factors like:

1. Noise level
2. Crowd density
3. Greenery score

The project uses OpenStreetMap road graphs
through the OSMnx library.

Modes:
- DOG    → Best route for dog walking
- YOGA   → Quietest route possible
- NORMAL → Balanced route
"""


# ==========================================================
# CONFIGURATION SECTION
# ==========================================================

"""
All constants are stored in CONFIG
to avoid hardcoded magic numbers.

This makes:
- maintenance easier
- values reusable
- code cleaner
"""

CONFIG = {

    # ---------------- NOISE SETTINGS ---------------- #

    "NOISE": {

        # Base noise range
        "BASE_MIN": 45,
        "BASE_MAX": 65,

        # Extra noise during peak hours
        "PEAK_BONUS_MIN": 15,
        "PEAK_BONUS_MAX": 25,

        # Reduced noise during night
        "NIGHT_REDUCTION_MIN": 5,
        "NIGHT_REDUCTION_MAX": 10,

        # Normal daytime fluctuation
        "NORMAL_VARIATION_MIN": 5,
        "NORMAL_VARIATION_MAX": 10,

        # Noise threshold for DOG mode
        "DOG_THRESHOLD": 65,

        # Noise threshold for YOGA mode
        "YOGA_THRESHOLD": 55,
    },

    # ---------------- CROWD SETTINGS ---------------- #

    "CROWD": {

        # Base crowd density
        "BASE_MIN": 2,
        "BASE_MAX": 6,

        # Crowd increase during peak hours
        "PEAK_INCREASE_MIN": 3,
        "PEAK_INCREASE_MAX": 5,

        # Crowd decrease at night
        "NIGHT_DECREASE_MIN": 1,
        "NIGHT_DECREASE_MAX": 2,
    },

    # ---------------- GREENERY SETTINGS ---------------- #

    "GREEN": {

        # Random greenery score range
        "MIN": 0,
        "MAX": 10
    },

    # ---------------- WEIGHT CALCULATION ---------------- #

    "WEIGHTS": {

        # DOG walking preferences
        "DOG": {
            "CROWD": 5,
            "GREEN": 2,
            "NOISE_MULTIPLIER": 20
        },

        # YOGA mode prefers maximum silence
        "YOGA": {
            "CROWD": 8,
            "GREEN": 5,
            "NOISE_MULTIPLIER": 25
        },

        # NORMAL balanced mode
        "NORMAL": {
            "CROWD": 3,
            "GREEN": 1.5
        }
    },

    # ---------------- GENERAL SETTINGS ---------------- #

    "GENERAL": {

        # Prevent route weight from becoming zero or negative
        "MIN_WEIGHT": 1
    }
}


# ==========================================================
# USER SETTINGS
# ==========================================================

# Available modes:
# "DOG"
# "YOGA"
# "NORMAL"

MODE = "DOG"

# Graph file path
GRAPH_FILE = "city.graphml"


# ==========================================================
# TIME-BASED HELPER FUNCTIONS
# ==========================================================

def is_peak_hour(hour):
    """
    Checks if current hour is a traffic peak hour.

    Morning peak:
    8 AM - 10 AM

    Evening peak:
    5 PM - 8 PM
    """

    return (8 <= hour <= 10) or (17 <= hour <= 20)


def is_night(hour):
    """
    Checks if current hour is considered nighttime.
    """

    return (hour >= 22) or (hour <= 5)


# ==========================================================
# ENVIRONMENT GENERATION FUNCTIONS
# ==========================================================

def generate_noise(hour):
    """
    Generates a simulated noise level
    based on time of day.
    """

    # Generate base noise
    base = random.randint(
        CONFIG["NOISE"]["BASE_MIN"],
        CONFIG["NOISE"]["BASE_MAX"]
    )

    # Peak hours are noisier
    if is_peak_hour(hour):

        return base + random.randint(
            CONFIG["NOISE"]["PEAK_BONUS_MIN"],
            CONFIG["NOISE"]["PEAK_BONUS_MAX"]
        )

    # Nighttime is quieter
    elif is_night(hour):

        return base - random.randint(
            CONFIG["NOISE"]["NIGHT_REDUCTION_MIN"],
            CONFIG["NOISE"]["NIGHT_REDUCTION_MAX"]
        )

    # Normal daytime
    else:

        return base + random.randint(
            CONFIG["NOISE"]["NORMAL_VARIATION_MIN"],
            CONFIG["NOISE"]["NORMAL_VARIATION_MAX"]
        )


def generate_crowd(hour):
    """
    Generates simulated crowd density
    based on current time.
    """

    base = random.randint(
        CONFIG["CROWD"]["BASE_MIN"],
        CONFIG["CROWD"]["BASE_MAX"]
    )

    # Evening rush hour
    if 17 <= hour <= 20:

        crowd = base + random.randint(
            CONFIG["CROWD"]["PEAK_INCREASE_MIN"],
            CONFIG["CROWD"]["PEAK_INCREASE_MAX"]
        )

    # Nighttime crowd reduction
    elif is_night(hour):

        crowd = base - random.randint(
            CONFIG["CROWD"]["NIGHT_DECREASE_MIN"],
            CONFIG["CROWD"]["NIGHT_DECREASE_MAX"]
        )

    # Regular daytime
    else:

        crowd = base

    # Prevent negative crowd values
    return max(crowd, 0)


def generate_green_score():
    """
    Generates random greenery score.

    Higher score means:
    - more trees
    - more parks
    - calmer environment
    """

    return random.randint(
        CONFIG["GREEN"]["MIN"],
        CONFIG["GREEN"]["MAX"]
    )


# ==========================================================
# CALMNESS WEIGHT CALCULATION
# ==========================================================

def calculate_calm_weight(mode, length, noise, crowd, green):
    """
    Calculates route calmness weight.

    Lower weight = better calm route.

    Factors used:
    - distance
    - noise
    - crowd
    - greenery
    """

    weights = CONFIG["WEIGHTS"]

    # ---------------- DOG MODE ---------------- #

    if mode == "DOG":

        # Start with road length
        calm = length

        # Penalize high noise heavily
        if noise > CONFIG["NOISE"]["DOG_THRESHOLD"]:

            calm *= weights["DOG"]["NOISE_MULTIPLIER"]

        # Increase penalty for crowd
        calm += crowd * weights["DOG"]["CROWD"]

        # Green areas reduce stress
        calm -= green * weights["DOG"]["GREEN"]

    # ---------------- YOGA MODE ---------------- #

    elif mode == "YOGA":

        calm = length

        # Yoga mode is very sensitive to noise
        if noise > CONFIG["NOISE"]["YOGA_THRESHOLD"]:

            calm *= weights["YOGA"]["NOISE_MULTIPLIER"]

        calm += crowd * weights["YOGA"]["CROWD"]

        calm -= green * weights["YOGA"]["GREEN"]

    # ---------------- NORMAL MODE ---------------- #

    else:

        # Balanced route calculation
        calm = length * (noise / 50)

        calm += crowd * weights["NORMAL"]["CROWD"]

        calm -= green * weights["NORMAL"]["GREEN"]

    # Prevent negative or zero values
    return max(
        calm,
        CONFIG["GENERAL"]["MIN_WEIGHT"]
    )


# ==========================================================
# GRAPH LOADING
# ==========================================================

def load_graph(filepath):
    """
    Loads OpenStreetMap graph from GraphML file.
    """

    # Check if graph file exists
    if not os.path.exists(filepath):

        raise FileNotFoundError(
            f"Graph file not found: {filepath}"
        )

    try:

        # Load graph using OSMnx
        graph = ox.load_graphml(filepath)

        print("Graph loaded successfully!")

        return graph

    except Exception as e:

        raise RuntimeError(
            f"Error loading graph: {e}"
        )


# ==========================================================
# EDGE SCORE ASSIGNMENT
# ==========================================================

def assign_edge_scores(G, hour, mode):
    """
    Assigns environmental data
    to every edge in the graph.

    Each edge receives:
    - noise score
    - crowd score
    - greenery score
    - calmness weight
    """

    # Iterate through all edges
    for u, v, k, data in G.edges(
        keys=True,
        data=True
    ):

        try:

            # Get edge length
            # Default value = 1 if missing
            length = data.get("length", 1)

            # Generate environment data
            noise = generate_noise(hour)

            crowd = generate_crowd(hour)

            green = generate_green_score()

            # Calculate calmness
            calm_weight = calculate_calm_weight(
                mode,
                length,
                noise,
                crowd,
                green
            )

            # Store generated values inside edge
            data["noise"] = noise

            data["crowd"] = crowd

            data["green_score"] = green

            data["calm_weight"] = calm_weight

        except Exception as e:

            print(
                f"Skipping edge ({u},{v}) due to error: {e}"
            )


# ==========================================================
# ROUTE CALCULATION
# ==========================================================

def get_routes(G):
    """
    Calculates:
    1. Shortest route
    2. Calmest route
    """

    nodes = list(G.nodes)

    # Ensure graph contains enough nodes
    if len(nodes) < 201:

        raise ValueError(
            "Graph does not contain enough nodes."
        )

    # Sample origin and destination
    origin = nodes[10]

    destination = nodes[200]

    try:

        # Shortest route using distance
        shortest = nx.shortest_path(
            G,
            origin,
            destination,
            weight="length"
        )

        # Calmest route using calmness weight
        calmest = nx.shortest_path(
            G,
            origin,
            destination,
            weight="calm_weight"
        )

        return shortest, calmest

    except nx.NetworkXNoPath:

        raise RuntimeError(
            "No path found between selected nodes."
        )


# ==========================================================
# ROUTE VISUALIZATION
# ==========================================================

def plot_routes(G, shortest, calmest, hour, mode):
    """
    Plots shortest and calmest routes.
    """

    try:

        fig, ax = ox.plot_graph_routes(

            G,

            [shortest, calmest],

            # Red = shortest route
            # Green = calmest route
            route_colors=["red", "green"],

            route_linewidth=4,

            node_size=0,

            show=False,

            close=False
        )

        # Add graph title
        plt.title(
            f"StillSpace Mode: {mode} | Hour: {hour}"
        )

        # Display plot
        plt.show()

    except Exception as e:

        print(f"Plotting failed: {e}")


# ==========================================================
# MAIN FUNCTION
# ==========================================================

def main():
    """
    Main execution function.
    """

    try:

        # Get current system hour
        current_hour = datetime.now().hour

        print(f"Simulated Hour: {current_hour}")

        # Load graph
        G = load_graph(GRAPH_FILE)

        # Assign edge scores
        assign_edge_scores(
            G,
            current_hour,
            MODE
        )

        print(
            f"Calm scores assigned for {MODE} mode!"
        )

        # Generate routes
        shortest_route, calmest_route = get_routes(G)

        # Display route statistics
        print(
            "Shortest route node count:",
            len(shortest_route)
        )

        print(
            "Calmest route node count:",
            len(calmest_route)
        )

        # Plot routes visually
        plot_routes(
            G,
            shortest_route,
            calmest_route,
            current_hour,
            MODE
        )

    except Exception as e:

        print(f"Fatal Error: {e}")


# ==========================================================
# PROGRAM ENTRY POINT
# ==========================================================

"""
Python automatically sets __name__ to "__main__"
when this file is executed directly.

This prevents accidental execution
when imported as a module.
"""

if __name__ == "__main__":

    main()