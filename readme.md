# StillSpace

StillSpace is a Flask + OSMnx web app for intelligent urban walking routes.

Instead of showing only the shortest path, it can compare:
- Fastest
- Calm
- Safe
- Accessibility
- Dog Walk
- Weather Smart

The app uses OpenStreetMap graph data (`city.graphml`), computes routes with NetworkX, and renders them in Leaflet.

## Features

- Multi-mode route planning over a real street graph
- Geometry-accurate route rendering (curves, not straight node jumps)
- Marker-to-route connector segments for seamless visual start/end alignment
- Coverage guardrails (rejects clicks too far from mapped streets)
- Weather-aware weighting with mock/live weather support
- Safety-zone overlay API
- Search history persistence using SQLite
- Responsive UI with simple and advanced route mode flows

## Tech Stack

- Backend: Python, Flask, NetworkX, OSMnx, Shapely
- Frontend: HTML, CSS, JavaScript, Leaflet
- Data: OpenStreetMap GraphML
- Storage: SQLite (`search_history.db`)

## Project Structure

```text
stillspace/
  app.py
  wsgi.py
  city.graphml
  database.py
  routing_utils.py
  route_modes.py
  weather_service.py
  safety_zones.py
  accessibility.py
  dog_mode.py
  qa_smoke.py
  templates/
    index.html
  static/
    css/app.css
    js/app.js
  docs/screenshots/
  .env.example
  requirements.txt
```

## API Endpoints

### `POST /smart_route`

Request body:

```json
{
  "start_lat": 30.7333,
  "start_lon": 76.7794,
  "end_lat": 30.7392,
  "end_lon": 76.7739,
  "route_mode": "calm",
  "dog_sub_mode": "relax",
  "preference_bias": 50
}
```

Main response fields:
- `fastest_route`
- `smart_route`
- `shortest_stats`
- `smart_stats`
- `comparison`
- `connectors` (visual bridge segments)
- `snapped_nodes`
- `snap_distances_m`

### `GET /api/safety_zones`

Returns GeoJSON polygons for safety overlays.

### `GET /api/history`

Returns recent searches from SQLite.

### `DELETE /api/history/<id>`

Deletes one search history row.

### `GET /health`

Health metadata including graph bounds and max snap distance.

## Local Setup

1. Create and activate a virtual environment.

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from template:

```bash
cp .env.example .env
```

4. Run:

```bash
python app.py
```

Open `http://127.0.0.1:5000`.

## Environment Variables

Defined in `.env.example`:

- `FLASK_DEBUG`
- `FLASK_HOST`
- `FLASK_PORT`
- `LOG_LEVEL`
- `GRAPH_PATH`
- `MAX_SNAP_DISTANCE_M`
- `DB_PATH`
- `USE_MOCK_WEATHER`
- `OPENWEATHER_API_KEY`
- `WEATHER_CACHE_TTL_SEC`
- `WEATHER_REQUEST_TIMEOUT_SEC`

## Smoke Test

```bash
python qa_smoke.py
```

## Production Run

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 2 --threads 4
```

## Notes

- `city.graphml` is loaded at startup.
- Very large graphs require more RAM and slower cold starts.
- For best UX, keep selected points within the graph coverage bounds.
