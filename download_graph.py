import osmnx as ox

print("Downloading expanded map (4km radius)...")

# Center point: Sector 17 Chandigarh
center_point = (30.7333, 76.7794)

G = ox.graph_from_point(center_point, dist=4000, network_type="walk")

ox.save_graphml(G, "city.graphml")

print("Graph saved successfully!")
