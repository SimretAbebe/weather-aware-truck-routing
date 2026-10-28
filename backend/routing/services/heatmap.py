from datetime import datetime, timedelta, timezone
from typing import Callable

from .risk import assess
from .routing_provider import Route
from .sampling import sample_checkpoints
from .weather import fetch_hourly, weather_at

HEATMAP_HOURS = 48
GRID_DEG = 0.2  # ~14 miles; one sample point per grid cell avoids overlapping routes


def corridor_points(routes: list[Route], start: datetime, step_mi: float = 20.0):
    seen, pts = set(), []
    for r in routes:
        for cp in sample_checkpoints(r.coords, r.duration_h, start, step_mi):
            key = (round(cp.lat / GRID_DEG), round(cp.lon / GRID_DEG))
            if key not in seen:
                seen.add(key)
                pts.append((cp.lon, cp.lat))
    return pts


def build_heatmap(
    routes: list[Route],
    start: datetime,
    load_lb: float,
    fetch: Callable[[list], list] = fetch_hourly,
    hours: int = HEATMAP_HOURS,
) -> dict:
    """Risk level (0-4) at each corridor point for each of the next `hours` hours,
    starting at the departure hour. The slider just indexes into `levels`."""
    t0 = start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    pts = corridor_points(routes, start)
    hourly = fetch(pts)
    if len(hourly) != len(pts):
        raise RuntimeError("weather provider returned an unexpected number of points")

    out = []
    for (lon, lat), data in zip(pts, hourly):
        levels = []
        for h in range(hours):
            w = weather_at(data, t0 + timedelta(hours=h))
            levels.append(int(assess(w.wind_mph, w.rain_in_hr, w.snow_in_hr, load_lb).level))
        out.append({"lat": round(lat, 4), "lon": round(lon, 4), "levels": levels})
    return {"start": t0.isoformat(), "hours": hours, "points": out}