import os
import osmnx as ox
import networkx as nx
import random
import matplotlib.pyplot as plt
from datetime import datetime

# ==========================================================
# STILLSPACE PROTOTYPE – CLEAN VERSION
# Refactor: Error Handling + No Magic Numbers
# ==========================================================

# ----------------------------
# CONFIGURATION (NO MAGIC NUMBERS)
# ----------------------------

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
        "MIN_WEIGHT": 1
    }
}

MODE = "DOG"   # "DOG", "YOGA", "NORMAL"
GRAPH_FILE = "city.graphml"


# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------

def is_peak_hour(hour):
    return (8 <= hour <= 10) or (17 <= hour <= 20)


def is_night(hour):
    return (hour >= 22) or (hour <= 5)


def generate_noise(hour):
    base = random.randint(CONFIG["NOISE"]["BASE_MIN"], CONFIG["NOISE"]["BASE_MAX"])

    if is_peak_hour(hour):
        return base + random.randint(CONFIG["NOISE"]["PEAK_BONUS_MIN"], CONFIG["NOISE"]["PEAK_BONUS_MAX"])
    elif is_night(hour):
        return base - random.randint(CONFIG["NOISE"]["NIGHT_REDUCTION_MIN"], CONFIG["NOISE"]["NIGHT_REDUCTION_MAX"])
    else:
        return base + random.randint(CONFIG["NOISE"]["NORMAL_VARIATION_MIN"], CONFIG["NOISE"]["NORMAL_VARIATION_MAX"])


def generate_crowd(hour):
    base = random.randint(CONFIG["CROWD"]["BASE_MIN"], CONFIG["CROWD"]["BASE_MAX"])

    if 17 <= hour <= 20:
        crowd = base + random.randint(CONFIG["CROWD"]["PEAK_INCREASE_MIN"], CONFIG["CROWD"]["PEAK_INCREASE_MAX"])
    elif is_night(hour):
        crowd = base - random.randint(CONFIG["CROWD"]["NIGHT_DECREASE_MIN"], CONFIG["CROWD"]["NIGHT_DECREASE_MAX"])
    else:
        crowd = base

    return max(crowd, 0)


def generate_green_score():
    return random.randint(CONFIG["GREEN"]["MIN"], CONFIG["GREEN"]["MAX"])


def calculate_calm_weight(mode, length, noise, crowd, green):
    weights = CONFIG["WEIGHTS"]

    if mode == "DOG":
        calm = length

        if noise > CONFIG["NOISE"]["DOG_THRESHOLD"]:
            calm *= weights["DOG"]["NOISE_MULTIPLIER"]

        calm += crowd * weights["DOG"]["CROWD"]
        calm -= green * weights["DOG"]["GREEN"]

    elif mode == "YOGA":
        calm = length

        if noise > CONFIG["NOISE"]["YOGA_THRESHOLD"]:
            calm *= weights["YOGA"]["NOISE_MULTIPLIER"]

        calm += crowd * weights["YOGA"]["CROWD"]
        calm -= green * weights["YOGA"]["GREEN"]

    else:  # NORMAL
        calm = length * (noise / 50)
        calm += crowd * weights["NORMAL"]["CROWD"]
        calm -= green * weights["NORMAL"]["GREEN"]

    return max(calm, CONFIG["GENERAL"]["MIN_WEIGHT"])


# ----------------------------
# GRAPH LOADING
# ----------------------------

def load_graph(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Graph file not found: {filepath}")

    try:
        graph = ox.load_graphml(filepath)
        print("Graph loaded successfully!")
        return graph
    except Exception as e:
        raise RuntimeError(f"Error loading graph: {e}")


# ----------------------------
# MAIN PROCESSING
# ----------------------------

def assign_edge_scores(G, hour, mode):
    for u, v, k, data in G.edges(keys=True, data=True):

        try:
            length = data.get("length", 1)

            noise = generate_noise(hour)
            crowd = generate_crowd(hour)
            green = generate_green_score()

            calm_weight = calculate_calm_weight(mode, length, noise, crowd, green)

            data["noise"] = noise
            data["crowd"] = crowd
            data["green_score"] = green
            data["calm_weight"] = calm_weight

        except Exception as e:
            print(f"Skipping edge ({u},{v}) due to error: {e}")


def get_routes(G):
    nodes = list(G.nodes)

    if len(nodes) < 201:
        raise ValueError("Graph does not contain enough nodes.")

    origin = nodes[10]
    destination = nodes[200]

    try:
        shortest = nx.shortest_path(G, origin, destination, weight="length")
        calmest = nx.shortest_path(G, origin, destination, weight="calm_weight")
        return shortest, calmest
    except nx.NetworkXNoPath:
        raise RuntimeError("No path found between selected nodes.")


def plot_routes(G, shortest, calmest, hour, mode):
    try:
        fig, ax = ox.plot_graph_routes(
            G,
            [shortest, calmest],
            route_colors=["red", "green"],
            route_linewidth=4,
            node_size=0,
            show=False,
            close=False
        )

        plt.title(f"StillSpace Mode: {mode} | Hour: {hour}")
        plt.show()

    except Exception as e:
        print(f"Plotting failed: {e}")


# ----------------------------
# ENTRY POINT
# ----------------------------

def main():
    try:
        current_hour = datetime.now().hour
        print(f"Simulated Hour: {current_hour}")

        G = load_graph(GRAPH_FILE)

        assign_edge_scores(G, current_hour, MODE)
        print(f"Calm scores assigned for {MODE} mode!")

        shortest_route, calmest_route = get_routes(G)

        print("Shortest route node count:", len(shortest_route))
        print("Calmest route node count:", len(calmest_route))

        plot_routes(G, shortest_route, calmest_route, current_hour, MODE)

    except Exception as e:
        print(f"Fatal Error: {e}")


if __name__ == "__main__":
    main()