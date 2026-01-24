import osmnx as ox
import networkx as nx
import random
import matplotlib.pyplot as plt
from datetime import datetime

# ==========================================================
# STILLSPACE PROTOTYPE – Multi-Factor Calm Routing Engine
#
# Factors:
#   - Time-based Noise
#   - Crowd Density Simulation
#   - Green Coverage Bonus
#   - Mode Sensitivity Profiles
# ==========================================================

MODE = "DOG"   # "DOG", "YOGA", "NORMAL"

current_hour = datetime.now().hour
print(f"Simulated Hour: {current_hour}")

G = ox.load_graphml("city.graphml")
print("Graph loaded!")

for u, v, k, data in G.edges(keys=True, data=True):

    length = data["length"]

    # ----------------------------
    # 1️⃣ TIME-BASED NOISE
    # ----------------------------
    base_noise = random.randint(45, 65)

    if 8 <= current_hour <= 10 or 17 <= current_hour <= 20:
        noise = base_noise + random.randint(15, 25)
    elif 22 <= current_hour or current_hour <= 5:
        noise = base_noise - random.randint(5, 10)
    else:
        noise = base_noise + random.randint(5, 10)

    data["noise"] = noise

    # ----------------------------
    # 2️⃣ CROWD DENSITY SIMULATION
    # ----------------------------
    base_crowd = random.randint(2, 6)

    if 17 <= current_hour <= 20:
        crowd = base_crowd + random.randint(3, 5)
    elif 22 <= current_hour or current_hour <= 6:
        crowd = base_crowd - random.randint(1, 2)
    else:
        crowd = base_crowd

    crowd = max(crowd, 0)
    data["crowd"] = crowd

    # ----------------------------
    # 3️⃣ GREEN SCORE
    # ----------------------------
    green_score = random.randint(0, 10)
    data["green_score"] = green_score

    # --------------------------------------------------
    # CALM WEIGHT CALCULATION
    # --------------------------------------------------

    if MODE == "DOG":
        calm_weight = length

        # Noise penalty
        if noise > 65:
            calm_weight *= 20

        # Crowd penalty (dogs react to chaos)
        calm_weight += crowd * 5

        # Green bonus
        calm_weight -= green_score * 2

    elif MODE == "YOGA":
        calm_weight = length

        # Strict noise penalty
        if noise > 55:
            calm_weight *= 25

        # Crowd strongly discouraged
        calm_weight += crowd * 8

        # Strong green preference
        calm_weight -= green_score * 5

    else:  # NORMAL
        calm_weight = length * (noise / 50)
        calm_weight += crowd * 3
        calm_weight -= green_score * 1.5

    calm_weight = max(calm_weight, 1)
    data["calm_weight"] = calm_weight

print(f"Calm scores assigned for {MODE} mode!")

nodes = list(G.nodes)
origin = nodes[10]
destination = nodes[200]

shortest_route = nx.shortest_path(G, origin, destination, weight="length")
calmest_route = nx.shortest_path(G, origin, destination, weight="calm_weight")

print("Shortest route node count:", len(shortest_route))
print("Calmest route node count:", len(calmest_route))

fig, ax = ox.plot_graph_routes(
    G,
    [shortest_route, calmest_route],
    route_colors=["red", "green"],
    route_linewidth=4,
    node_size=0,
    show=False,
    close=False
)

plt.title(f"StillSpace Mode: {MODE} | Hour: {current_hour}")
plt.show()
