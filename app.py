from flask import Flask, request, jsonify
import osmnx as ox
import networkx as nx
import random
from datetime import datetime
from flask import render_template



app = Flask(__name__)
@app.route("/")
def home():
    return render_template("index.html")
# ----------------------------
# Load Graph Once at Startup
# ----------------------------
print("Loading graph...")
G = ox.load_graphml("city.graphml")
print("Graph loaded successfully!")

# ---------------------------------------------------
# Function: Assign Environmental Calm Weights
# ---------------------------------------------------
def assign_calm_weights(mode):

    current_hour = datetime.now().hour

    for u, v, k, data in G.edges(keys=True, data=True):

        length = data["length"]

        # -------- Noise Simulation --------
        base_noise = random.randint(45, 65)

        if 8 <= current_hour <= 10 or 17 <= current_hour <= 20:
            noise = base_noise + random.randint(15, 25)
        elif 22 <= current_hour or current_hour <= 5:
            noise = base_noise - random.randint(5, 10)
        else:
            noise = base_noise + random.randint(5, 10)

        # -------- Crowd Simulation --------
        base_crowd = random.randint(2, 6)

        if 17 <= current_hour <= 20:
            crowd = base_crowd + random.randint(3, 5)
        elif 22 <= current_hour or current_hour <= 6:
            crowd = base_crowd - random.randint(1, 2)
        else:
            crowd = base_crowd

        crowd = max(crowd, 0)

        # -------- Green Score --------
        green_score = random.randint(0, 10)

        # -------- Mode Logic --------
        if mode == "DOG":
            calm_weight = length

            if noise > 65:
                calm_weight *= 20

            calm_weight += crowd * 5
            calm_weight -= green_score * 2

        elif mode == "YOGA":
            calm_weight = length

            if noise > 55:
                calm_weight *= 25

            calm_weight += crowd * 8
            calm_weight -= green_score * 5

        else:  # NORMAL
            calm_weight = length * (noise / 50)
            calm_weight += crowd * 3
            calm_weight -= green_score * 1.5

        data["calm_weight"] = max(calm_weight, 1)


# ---------------------------------------------------
# API Route Endpoint
# ---------------------------------------------------
@app.route("/route", methods=["POST"])
def calculate_route():

    data = request.json

    start_lat = data["start_lat"]
    start_lon = data["start_lon"]
    end_lat = data["end_lat"]
    end_lon = data["end_lon"]
    mode = data["mode"]

    # Assign weights based on mode
    assign_calm_weights(mode)

    # Find nearest graph nodes
    origin = ox.distance.nearest_nodes(G, start_lon, start_lat)
    destination = ox.distance.nearest_nodes(G, end_lon, end_lat)

    # Compute routes
    shortest = nx.shortest_path(G, origin, destination, weight="length")
    calmest = nx.shortest_path(G, origin, destination, weight="calm_weight")

    # Convert node IDs to coordinates
    shortest_coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in shortest]
    calm_coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in calmest]

    return jsonify({
        "shortest_route": shortest_coords,
        "calm_route": calm_coords,
        "mode": mode
    })


# ---------------------------------------------------
# Run Server
# ---------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
