# StillSpace

StillSpace is a smart pedestrian route-planning web application that helps users choose between the **fastest route** and a **calmer walking route**.  
Unlike traditional navigation systems that optimize only for distance or time, StillSpace also considers road stress, sharp turns, and busy intersections to generate a more peaceful walking experience.

---

## Overview

Urban walking routes are not always comfortable. The shortest path may pass through noisy roads, high-traffic intersections, or stressful environments.

StillSpace solves this problem by offering two route options:

- **Fastest Route** – shortest walking distance  
- **Calm Route** – safer and less stressful path using custom scoring logic  

This makes StillSpace useful for students, daily commuters, tourists, senior citizens, and anyone who prefers a more comfortable walking experience.

---

## Features

- Smart route comparison system  
- Fastest route using shortest-path algorithm  
- Calm route using custom weighted graph logic  
- Real-world road network data using OpenStreetMap  
- Distance and estimated walking time  
- Interactive map visualization  
- Web-based interface with Flask  

---

## Tech Stack

### Backend
- Python  
- Flask  
- NetworkX  
- OSMnx  
- Shapely  

### Frontend
- HTML  
- CSS  
- JavaScript  
- Leaflet.js  

### Data Source
- OpenStreetMap  

---

## How It Works

StillSpace loads a city road network graph and compares two paths between source and destination.

### 1. Fastest Route

Uses Dijkstra’s shortest path algorithm with road length as weight.

**Formula:**  
`Total Cost = Sum of Road Lengths`

### 2. Calm Route

Uses a custom modified Dijkstra algorithm.

**Formula:**  
`Calm Score = (Length × Road Stress) + Turn Penalty + Intersection Penalty`

The route with the lowest calm score is selected.

---

## Road Stress Values

| Road Type | Stress Score |
|----------|--------------|
| Footway | 0.85 |
| Residential | 1.0 |
| Tertiary Road | 1.4 |
| Secondary Road | 2.0 |
| Primary Road | 2.8 |
| Motorway | 4.0 |

Lower score means more comfortable.

---

## Turn Penalty Logic

| Turn Angle | Penalty |
|-----------|---------|
| < 25° | 0 |
| < 55° | 8 |
| < 95° | 18 |
| < 140° | 36 |
| > 140° | 60 |

Sharp turns increase discomfort.

---

## Installation

### Clone Repository

```bash
git clone https://github.com/your-username/stillspace.git
cd stillspace
```
# Create Virtual Environment
python -m venv .venv
Activate Environment
Windows
.venv\Scripts\activate
Linux / Mac
source .venv/bin/activate
Install Dependencies
pip install flask networkx osmnx shapely
Run Project
python app.py

Open browser:

http://127.0.0.1:5000
Project Structure
stillspace/
│── app.py
│── city.graphml
│── templates/
│   └── index.html
│── download_graph.py
│── route_test.py
Use Cases
Peaceful city walking navigation
Safer route suggestions
Tourist walking assistant
Accessibility-friendly routing
Mental wellness focused navigation
Future Enhancements
Live traffic integration
Noise pollution data
Night safety mode
Wheelchair-friendly routes
Mobile application
AI route preference learning
Why StillSpace?

Most map apps optimize speed.
StillSpace optimizes peace of mind.

Author

Kumar Aryan
Computer Science Engineering Student
Cloud & AI/ML Enthusiast

License

This project is open-source and available under the MIT License.