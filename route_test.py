import os  # For file handling (checking if graph file exists)
import osmnx as ox  # For loading and working with map graphs
import networkx as nx  # For graph algorithms like shortest path
import random  # For generating random values (noise, crowd, etc.)
import matplotlib.pyplot as plt  # For plotting routes
from datetime import datetime  # To get current system time


# ==========================================================
# STILLSPACE PROTOTYPE – CLEAN VERSION
# Refactor: Error Handling + No Magic Numbers
# ==========================================================


# ----------------------------
# CONFIGURATION (NO MAGIC NUMBERS)
# ----------------------------

# All constants are stored here to avoid hardcoding values in logic
CONFIG = {
    "NOISE": {
        "BASE_MIN": 45,
        "BASE_MAX": 65,
        "PEAK_BONUS_MIN": 15,
        "PEAK_BONUS_MAX": 25,
        "NIGHT_REDUCTION_MIN": 5,
        "NIGHT_REDUCTION_MAX": 10,
        "NORMAL_VARIATION_MIN": 5,
        "NORMAL_VARIATION_MAX": 10,
        "DOG_THRESHOLD": 65,
        "YOGA_THRESHOLD": 55,
    },
    "CROWD": {
        "BASE_MIN": 2,
        "BASE_MAX": 6,
        "PEAK_INCREASE_MIN": 3,
        "PEAK_INCREASE_MAX": 5,
        "NIGHT_DECREASE_MIN": 1,
        "NIGHT_DECREASE_MAX": 2,
    },
    "GREEN": {
        "MIN": 0,
        "MAX": 10
    },
    "WEIGHTS": {
        "DOG": {"CROWD": 5, "GREEN": 2, "NOISE_MULTIPLIER": 20},
        "YOGA": {"CROWD": 8, "GREEN": 5, "NOISE_MULTIPLIER": 25},
        "NORMAL": {"CROWD": 3, "GREEN": 1.5}
    },
    "GENERAL": {
        "MIN_WEIGHT": 1  # Minimum allowed weight
    }
}

# Mode defines how calmness is calculated
MODE = "DOG"   # Options: "DOG", "YOGA", "NORMAL"

# Graph file to load
GRAPH_FILE = "city.graphml"


# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------

# Check if current hour is peak traffic time
def is_peak_hour(hour):
    return (8 <= hour <= 10) or (17 <= hour <= 20)


# Check if current hour is night time
def is_night(hour):
    return (hour >= 22) or (hour <= 5)


# Generate noise level based on time of day
def generate_noise(hour):
    base = random.randint(CONFIG["NOISE"]["BASE_MIN"], CONFIG["NOISE"]["BASE_MAX"])

    if is_peak_hour(hour):
        # Higher noise during peak hours
        return base + random.randint(CONFIG["NOISE"]["PEAK_BONUS_MIN"], CONFIG["NOISE"]["PEAK_BONUS_MAX"])
    elif is_night(hour):
        # Lower noise during night
        return base - random.randint(CONFIG["NOISE"]["NIGHT_REDUCTION_MIN"], CONFIG["NOISE"]["NIGHT_REDUCTION_MAX"])
    else:
        # Normal variation during regular hours
        return base + random.randint(CONFIG["NOISE"]["NORMAL_VARIATION_MIN"], CONFIG["NOISE"]["NORMAL_VARIATION_MAX"])


# Generate crowd level based on time
def generate_crowd(hour):
    base = random.randint(CONFIG["CROWD"]["BASE_MIN"], CONFIG["CROWD"]["BASE_MAX"])

    if 17 <= hour <= 20:
        # Increase crowd during evening peak
        crowd = base + random.randint(CONFIG["CROWD"]["PEAK_INCREASE_MIN"], CONFIG["CROWD"]["PEAK_INCREASE_MAX"])
    elif is_night(hour):
        # Decrease crowd at night
        crowd = base - random.randint(CONFIG["CROWD"]["NIGHT_DECREASE_MIN"], CONFIG["CROWD"]["NIGHT_DECREASE_MAX"])
    else:
        # Normal crowd
        crowd = base

    # Ensure crowd is never negative
    return max(crowd, 0)


# Generate random greenery score
def generate_green_score():
    return random.randint(CONFIG["GREEN"]["MIN"], CONFIG["GREEN"]["MAX"])


# Calculate calmness weight based on mode
def calculate_calm_weight(mode, length, noise, crowd, green):
    weights = CONFIG["WEIGHTS"]

    if mode == "DOG":
        # Start with base length
        calm = length

        # Penalize high noise heavily
        if noise > CONFIG["NOISE"]["DOG_THRESHOLD"]:
            calm *= weights["DOG"]["NOISE_MULTIPLIER"]

        # Add crowd penalty and subtract greenery benefit
        calm += crowd * weights["DOG"]["CROWD"]
        calm -= green * weights["DOG"]["GREEN"]

    elif mode == "YOGA":
        calm = length

        # Yoga mode is more sensitive to noise
        if noise > CONFIG["NOISE"]["YOGA_THRESHOLD"]:
            calm *= weights["YOGA"]["NOISE_MULTIPLIER"]

        calm += crowd * weights["YOGA"]["CROWD"]
        calm -= green * weights["YOGA"]["GREEN"]

    else:  # NORMAL mode
        # Balance between noise and length
        calm = length * (noise / 50)
        calm += crowd * weights["NORMAL"]["CROWD"]
        calm -= green * weights["NORMAL"]["GREEN"]

    # Ensure weight is not below minimum
    return max(calm, CONFIG["GENERAL"]["MIN_WEIGHT"])


# ----------------------------
# GRAPH LOADING
# ----------------------------

# Load graph from file
def load_graph(filepath):
    # Check if file exists
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Graph file not found: {filepath}")

    try:
        # Load graph using osmnx
        graph = ox.load_graphml(filepath)
        print("Graph loaded successfully!")
        return graph
    except Exception as e:
        raise RuntimeError(f"Error loading graph: {e}")


# ----------------------------
# MAIN PROCESSING
# ----------------------------

# Assign noise, crowd, green score, and calm weight to each edge
def assign_edge_scores(G, hour, mode):
    for u, v, k, data in G.edges(keys=True, data=True):

        try:
            # Get edge length (default = 1 if missing)
            length = data.get("length", 1)

            # Generate environmental factors
            noise = generate_noise(hour)
            crowd = generate_crowd(hour)
            green = generate_green_score()

            # Calculate calmness weight
            calm_weight = calculate_calm_weight(mode, length, noise, crowd, green)

            # Store values in edge data
            data["noise"] = noise
            data["crowd"] = crowd
            data["green_score"] = green
            data["calm_weight"] = calm_weight

        except Exception as e:
            # Skip problematic edges
            print(f"Skipping edge ({u},{v}) due to error: {e}")


# Get shortest and calmest routes between two nodes
def get_routes(G):
    nodes = list(G.nodes)

    # Ensure enough nodes exist
    if len(nodes) < 201:
        raise ValueError("Graph does not contain enough nodes.")

    origin = nodes[10]
    destination = nodes[200]

    try:
        # Shortest route based on distance
        shortest = nx.shortest_path(G, origin, destination, weight="length")

        # Calmest route based on calculated calm weight
        calmest = nx.shortest_path(G, origin, destination, weight="calm_weight")

        return shortest, calmest

    except nx.NetworkXNoPath:
        raise RuntimeError("No path found between selected nodes.")


# Plot both routes on graph
def plot_routes(G, shortest, calmest, hour, mode):
    try:
        fig, ax = ox.plot_graph_routes(
            G,
            [shortest, calmest],
            route_colors=["red", "green"],  # Red = shortest, Green = calmest
            route_linewidth=4,
            node_size=0,
            show=False,
            close=False
        )

        # Add title to plot
        plt.title(f"StillSpace Mode: {mode} | Hour: {hour}")
        plt.show()

    except Exception as e:
        print(f"Plotting failed: {e}")


# ----------------------------
# ENTRY POINT
# ----------------------------

def main():
    try:
        # Get current system hour
        current_hour = datetime.now().hour
        print(f"Simulated Hour: {current_hour}")

        # Load graph
        G = load_graph(GRAPH_FILE)

        # Assign scores to edges
        assign_edge_scores(G, current_hour, MODE)
        print(f"Calm scores assigned for {MODE} mode!")

        # Get routes
        shortest_route, calmest_route = get_routes(G)

        print("Shortest route node count:", len(shortest_route))
        print("Calmest route node count:", len(calmest_route))

        # Plot routes
        plot_routes(G, shortest_route, calmest_route, current_hour, MODE)

    except Exception as e:
        print(f"Fatal Error: {e}")


# Run program
if __name__ == "__main__":
    main()