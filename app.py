from flask import Flask, request, jsonify, render_template
import osmnx as ox
import networkx as nx
import random

app = Flask(__name__)

print("Loading graph...")
G = ox.load_graphml("city.graphml")
print("Graph loaded successfully!")

# Simple rule-based mode detection
def detect_mode(text):
    text = text.lower()

    if "dog" in text:
        return "DOG"
    if "yoga" in text or "peace" in text or "calm" in text:
        return "YOGA"

    return "DEFAULT"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/smart_route", methods=["POST"])
def smart_route():

    data = request.json

    start_lat = data["start_lat"]
    start_lon = data["start_lon"]
    end_lat = data["end_lat"]
    end_lon = data["end_lon"]
    text = data["text"]

    mode = detect_mode(text)

    # Assign random noise for demo
    for u, v, k, edge in G.edges(keys=True, data=True):
        noise = random.randint(40, 100)
        edge["noise"] = noise
        length = edge.get("length", 1)

        if mode == "DOG":
            if noise > 70:
                edge["calm_weight"] = length * 6
            else:
                edge["calm_weight"] = length

        elif mode == "YOGA":
            if noise > 55:
                edge["calm_weight"] = length * 25
            else:
                edge["calm_weight"] = length

        else:
            edge["calm_weight"] = length

    origin = ox.distance.nearest_nodes(G, start_lon, start_lat)
    destination = ox.distance.nearest_nodes(G, end_lon, end_lat)

    shortest_path = nx.shortest_path(G, origin, destination, weight="length")
    calm_path = nx.shortest_path(G, origin, destination, weight="calm_weight")

    shortest_coords = [
        [G.nodes[n]["y"], G.nodes[n]["x"]] for n in shortest_path
    ]

    calm_coords = [
        [G.nodes[n]["y"], G.nodes[n]["x"]] for n in calm_path
    ]

    explanation = {
        "DOG": "Dog Mode: Avoiding high-noise streets.",
        "YOGA": "Yoga Mode: Prioritizing peaceful low-noise routes.",
        "DEFAULT": "Default Mode: Balanced routing."
    }

    return jsonify({
        "mode": mode,
        "explanation": explanation[mode],
        "calm_route": calm_coords,
        "fastest_route": shortest_coords
    })


if __name__ == "__main__":
    app.run(debug=True)
