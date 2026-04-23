# StillSpace

StillSpace is a production-ready Flask + OSMnx routing app that compares the fastest route against intelligent alternatives:

- `calm`
- `safe`
- `accessibility`
- `dog`
- `weather`

It renders continuous road geometry in Leaflet and provides route comparison metrics (distance, ETA, and deltas).

## UI Preview

![StillSpace UI overview](docs/screenshots/ui-overview.svg)

## What Is Included

- Multi-mode routing engine over an OSMnx `MultiDiGraph`
- Continuous route reconstruction using edge geometries
- Safety-zone overlay endpoint
- Weather-aware mode weighting with cache + mock/live weather switch
- Premium responsive Leaflet frontend (desktop + mobile sheet)
- API smoke test script for quick regression checks
- Deployment-ready configuration for Render/Railway/Gunicorn

## Architecture

### Backend

- `app.py`: Flask app, routing API, graph loading, edge-path reconstruction
- `route_modes.py`: mode strategies (`calm`, `safe`, `accessibility`, `dog`, `weather`)
- `routing_utils.py`: shared highway normalization and parsing helpers
- `weather_service.py`: cached weather provider (mock/live OpenWeather)
- `safety_zones.py`: mock danger polygons + geometry checks

### Frontend

- `templates/index.html`: semantic app shell
- `static/css/app.css`: premium responsive styling
- `static/js/app.js`: map state, routing calls, animations, UI state machine

## API

### `POST /smart_route`

Request:

```json
{
  "start_lat": 30.7333,
  "start_lon": 76.7794,
  "end_lat": 30.7392,
  "end_lon": 76.7739,
  "route_mode": "calm",
  "dog_sub_mode": "relax"
}
```

Key response fields:

- `fastest_route`: `[[lat, lng], ...]`
- `smart_route`: `[[lat, lng], ...]` (empty for `fastest` mode)
- `shortest_stats`: `{ dist_km, time_min }`
- `smart_stats`: `{ dist_km, time_min } | null`
- `comparison`: `{ extra_dist_km, extra_time_min, dist_diff_pct } | null`
- `weather`: current weather flags used by weather-aware scoring

### `GET /api/safety_zones`

Returns GeoJSON polygons for danger-zone visualization.

### `GET /health`

Basic health and graph metadata for deployment probes.

## Local Development

1. Create and activate a virtual environment
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy environment template:

```bash
cp .env.example .env
```

4. Run app:

```bash
python app.py
```

Open: `http://127.0.0.1:5000`

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `FLASK_DEBUG` | Flask debug mode | `false` |
| `FLASK_HOST` | Bind host | `0.0.0.0` |
| `FLASK_PORT` | Bind port | `5000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `GRAPH_PATH` | GraphML path | `city.graphml` |
| `USE_MOCK_WEATHER` | Use mock weather instead of API | `true` |
| `OPENWEATHER_API_KEY` | OpenWeather API key | empty |
| `WEATHER_CACHE_TTL_SEC` | Weather cache TTL | `900` |
| `WEATHER_REQUEST_TIMEOUT_SEC` | Weather API timeout | `4` |

## QA Smoke Checks

Run:

```bash
python qa_smoke.py
```

This checks:

- `/health`
- `/api/safety_zones`
- `/smart_route` for all modes

## Production Run

Use Gunicorn:

```bash
gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 2 --threads 4
```

## Deployment Guides

### Render

1. Create Web Service from repo
2. Build command:

```bash
pip install -r requirements.txt
```

3. Start command:

```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
```

4. Set env vars from `.env.example`

### Railway

1. New project from repo
2. Set start command:

```bash
gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
```

3. Configure environment variables in Railway dashboard

### Vercel (Backend Alternative)

If you need a serverless backend variant, expose Flask via a Vercel Python function (for light traffic). For heavy routing traffic, prefer Render/Railway because graph routing is CPU-heavy and better suited to a persistent process.

## Notes

- `city.graphml` is loaded once at startup.
- Route continuity depends on real edge geometry reconstruction, not straight node-to-node segments.
- Safety/weather logic is deterministic and testable (mock weather can be enabled in `.env`).
