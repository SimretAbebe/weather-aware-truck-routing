import math
import os
from dataclasses import dataclass

import requests

M_PER_MI = 1609.344
ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"

Coord = tuple[float, float]  # (lon, lat)


@dataclass
class Route:
    source: str
    coords: list[Coord]
    distance_mi: float
    duration_h: float


def haversine_mi(a: Coord, b: Coord) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def offset_via(origin: Coord, dest: Coord, side: int, ratio: float = 0.12) -> Coord:
    """Point at the midpoint of origin->dest, pushed sideways (side = +1 or -1)."""
    mid_lon = (origin[0] + dest[0]) / 2
    mid_lat = (origin[1] + dest[1]) / 2
    k = math.cos(math.radians(mid_lat))
    dx = (dest[0] - origin[0]) * k
    dy = dest[1] - origin[1]
    length = math.hypot(dx, dy) or 1e-9
    px, py = -dy / length, dx / length
    off = ratio * length
    return (mid_lon + side * px * off / k, mid_lat + side * py * off)


def fetch_ors(waypoints: list[Coord]) -> Route:
    key = os.getenv("ORS_API_KEY")
    if not key:
        raise RuntimeError("ORS_API_KEY is not set")
    r = requests.post(
        ORS_URL,
        headers={"Authorization": key},
        json={
            "coordinates": [list(w) for w in waypoints],
            "radiuses": [-1] * len(waypoints),
        },
        timeout=60,
    )
    r.raise_for_status()
    feature = r.json()["features"][0]
    s = feature["properties"]["summary"]
    coords = [(c[0], c[1]) for c in feature["geometry"]["coordinates"]]
    return Route("ors", coords, s["distance"] / M_PER_MI, s["duration"] / 3600)


def fetch_osrm_alternatives(origin: Coord, dest: Coord) -> list[Route]:
    url = f"{OSRM_URL}/{origin[0]},{origin[1]};{dest[0]},{dest[1]}"
    r = requests.get(
        url,
        params={"alternatives": "true", "overview": "full", "geometries": "geojson"},
        timeout=60,
    )
    r.raise_for_status()
    return [
        Route(
            "osrm",
            [(c[0], c[1]) for c in rt["geometry"]["coordinates"]],
            rt["distance"] / M_PER_MI,
            rt["duration"] / 3600,
        )
        for rt in r.json().get("routes", [])
    ]


def _thin(coords: list[Coord], n: int) -> list[Coord]:
    return coords[:: max(1, len(coords) // n)]


def overlap(a: Route, b: Route, tol_mi: float = 3.0) -> float:
    """Fraction of route a's sampled points lying within tol_mi of route b."""
    sa, sb = _thin(a.coords, 60), _thin(b.coords, 600)
    near = sum(1 for p in sa if min(haversine_mi(p, q) for q in sb) <= tol_mi)
    return near / len(sa)


def _add_distinct(chosen, candidates, want, max_overlap):
    for c in candidates:
        if len(chosen) == want:
            break
        if all(overlap(c, k) < max_overlap for k in chosen):
            chosen.append(c)


def get_route_options(
    origin: Coord,
    dest: Coord,
    want: int = 3,
    max_overlap: float = 0.85,
    max_slowdown: float = 1.5,
) -> list[Route]:
    chosen: list[Route] = []

       # 1) ORS truck routes: base + detours of increasing/decreasing size
    try:
        base = fetch_ors([origin, dest])
        chosen.append(base)
        for ratio in (0.12, 0.25, 0.06):
            for side in (1, -1):
                if len(chosen) == want:
                    break
                try:
                    alt = fetch_ors([origin, offset_via(origin, dest, side, ratio), dest])
                except requests.RequestException:
                    continue
                if alt.duration_h <= base.duration_h * max_slowdown:
                    _add_distinct(chosen, [alt], want, max_overlap)
    except (requests.RequestException, RuntimeError):
        pass

    # 2) Fallback: OSRM's own alternatives
    if len(chosen) < want:
        try:
            _add_distinct(chosen, fetch_osrm_alternatives(origin, dest), want, max_overlap)
        except requests.RequestException:
            pass

    return chosen