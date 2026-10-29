# Weather-Aware Truck Routing

A web app that helps a truck driver choose the safest route based on **weather, load weight, and travel time**.

- **Live app:** <your-vercel-link>
- **Walkthrough video (Loom):** <your-loom-link>

> The backend runs on a free server that sleeps when idle. The first request can take up to a minute. After that it is fast.

## What it does

1. The driver enters an origin, a destination, a departure time, and a load weight.
2. The app finds **up to 3 route options** using a truck routing profile.
3. It places a **weather checkpoint every 10, 25, or 50 miles** (the driver chooses).
4. For each checkpoint, it estimates when the truck will arrive, then looks up the forecast **for that exact hour**.
5. It classifies the risk (Low, Moderate, High, Severe, No Travel) using the wind, rain, snow, and load rules.
6. It **recommends the best route** and explains why in plain words.
7. The map shows all routes colored by risk, checkpoint details, and a **weather heatmap with a 0 to 48 hour slider**.

## Tech stack

| Part | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Leaflet |
| Backend | Python, Django, Django REST Framework |
| Routing | OpenRouteService (`driving-hgv` truck profile), OSRM as a fallback |
| Weather | Open-Meteo (free, hourly forecast) |
| Geocoding | Photon (OpenStreetMap data) |
| Tests | pytest |

## How it works

The backend is split into small modules in `backend/routing/services/`:

| File | Job |
|---|---|
| `routing_provider.py` | Gets route options |
| `sampling.py` | Places checkpoints along a route and calculates ETAs |
| `weather.py` | Fetches forecasts (batched, cached, with retries) |
| `risk.py` | Risk rules for wind, rain, snow, and load weight |
| `analysis.py` | Combines everything, totals miles per risk level, ranks the routes |
| `heatmap.py` | Builds the 49-hour heatmap data |
| `geocode.py` | Place search for the form |

### Risk rules

Each checkpoint gets a risk level for wind, rain, and snow. The checkpoint's risk is the **worst of the three**. Then the load rules are applied:

- Wind 55 mph or more: **No Travel** for any load.
- Wind 45 to 54 mph and load over 30,000 lb: **No Travel**.
- Wind 35 to 44 mph and load over 40,000 lb: **Severe**.

Load rules can only raise the risk, never lower it. Checkpoints raised by a load rule are marked with `*` in the table.

### Route recommendation

Routes are compared in this order. The first difference decides:

1. Fewest **No Travel** miles
2. Fewest **Severe** miles
3. Fewest **High** miles
4. Lowest average risk (weighted by miles)
5. Shortest travel time

Each route shows a one-line reason, for example "Better than the next-best route on Severe miles (0 vs 50)."

## Decisions and assumptions

These choices were not fully defined in the task, so I made them on purpose:

- **Third route.** OpenRouteService only allows its built-in alternative routes for trips under 100 km. For long trips, the app builds extra routes by routing through a point placed to the left or right of the trip. It keeps a route only if it is not much slower than the base route and is clearly different from the others. If the OSRM fallback is used, those routes come from a car network, not a truck profile. Some trips only have 1 or 2 real options, and the app says so.
- **ETAs use a constant average speed.** Time to each checkpoint is proportional to the distance driven, based on the route's total duration.
- **Each checkpoint covers the road halfway to its neighbors.** This makes the risk miles add up to the full route length.
- **No Travel is ranked before Severe.** The task lists Severe first, but a route with No Travel miles should not beat a route without them.
- **Band edges.** The lower edge of each band is included (wind of exactly 25 mph is Moderate). The task says No Travel is "above 1.00" for rain and "above 3.0" for snow, so exactly 1.00 and 3.0 are Severe.
- **Rain** is `rain + showers`. **Snow** is Open-Meteo's hourly snowfall in inches, used as inches per hour. **Wind** is the sustained 10 m wind speed. Gusts are shown but not used for classification.
- **Forecast hour.** Each ETA uses the nearest forecast hour. If an ETA is beyond the forecast, the last hour is used and the route is flagged.
- **Departure time** must be within the next 14 days so that the 48-hour heatmap stays inside the forecast window.
- **Heatmap.** All 49 hourly frames (0 to 48 hours after departure) are sent in one response, so moving the slider makes **no network requests**. It also uses the entered load weight.

## Performance

- Weather for all checkpoints on all routes is requested in **batches**, not one call per point.
- Forecasts are **cached for 30 minutes** on a 0.1 degree grid (about 7 miles), so nearby checkpoints and the heatmap share forecasts.
- Requests are **retried with backoff** on rate limits and server errors.
- Route analysis and the heatmap are built in parallel.
- On the map, routes and the heatmap use canvas rendering, and the slider uses a deferred value to stay responsive.

## Run it locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows (Git Bash): source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env             # then add your ORS_API_KEY
python manage.py runserver
```

Get a free OpenRouteService key at https://account.heigit.org/signup.

| Variable | Purpose |
|---|---|
| `ORS_API_KEY` | OpenRouteService key (required) |
| `DJANGO_SECRET_KEY` | Django secret (set a long random value in production) |
| `DJANGO_DEBUG` | `1` for development, `0` in production |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend URLs |

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. To point at another backend, set `VITE_API_URL`.

### Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

The tests cover the risk boundaries and load rules, checkpoint sampling and ETAs, weather caching and retries, route ranking, and the API. They run offline using fake routing and weather data.

## API

| Endpoint | Description |
|---|---|
| `POST /api/analyze` | Takes origin, destination, departure, load, and interval. Returns ranked routes, checkpoints, and heatmap data |
| `GET /api/geocode?q=` | Place search |
| `GET /api/health` | Health check |

## Known limits and next steps

- The free weather and routing APIs have rate limits. The 10-mile interval on a long trip makes many requests, so it can be slow the first time. Repeats are fast because of the cache.
- ETAs assume a constant speed. Using per-segment durations from the routing API would be more accurate.
- The extra routes are built from via-points, so they are good options but not always the best possible roads.
- Weather is a model forecast at a point, not a measurement at the road. It does not include live road closures or chain laws.
- Next steps: per-segment ETAs, a persistent cache (such as Redis), route sharing links, and truck restrictions such as height and weight limits.