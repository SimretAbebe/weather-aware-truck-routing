import math
from bisect import bisect_left, bisect_right

from .services.analysis import RouteAnalysis
from .services.sampling import cumulative_miles


def _thin(points: list, max_pts: int) -> list:
    if len(points) <= max_pts:
        return points
    stride = math.ceil(len(points) / max_pts)
    out = points[::stride]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def segment_path(coords, cum, start_mi, end_mi, max_pts=30):
    """[lat, lon] pairs (Leaflet order) for the road between two mileposts."""
    i0 = max(bisect_left(cum, start_mi) - 1, 0)
    i1 = min(bisect_right(cum, end_mi) + 1, len(coords))
    return [[round(lat, 5), round(lon, 5)] for lon, lat in _thin(coords[i0:i1], max_pts)]


def present_analysis(a: RouteAnalysis) -> dict:
    coords = a.route.coords
    cum = cumulative_miles(coords)
    return {
        "rank": a.rank,
        "recommended": a.recommended,
        "reason": a.reason,
        "source": a.route.source,
        "distance_mi": round(a.route.distance_mi, 1),
        "duration_h": round(a.duration_h, 2),
        "avg_risk": round(a.avg_risk, 2),
        "max_risk": a.max_risk.name.lower(),
        "miles_by_level": {lvl.name.lower(): round(mi, 1) for lvl, mi in a.miles_by_level.items()},
        "beyond_forecast": a.beyond_forecast,
        "checkpoints": [
            {
                "index": r.checkpoint.index,
                "mile": round(r.checkpoint.mile, 1),
                "lat": round(r.checkpoint.lat, 5),
                "lon": round(r.checkpoint.lon, 5),
                "eta": r.checkpoint.eta.isoformat(),
                "risk": r.risk.level.name.lower(),
                "levels": {
                    "wind": r.risk.wind.name.lower(),
                    "rain": r.risk.rain.name.lower(),
                    "snow": r.risk.snow.name.lower(),
                },
                "load_override": r.risk.load_override,
                "wind_mph": round(r.weather.wind_mph, 1),
                "gust_mph": round(r.weather.gust_mph, 1),
                "rain_in_hr": round(r.weather.rain_in_hr, 2),
                "snow_in_hr": round(r.weather.snow_in_hr, 2),
                "segment_start_mi": round(r.segment_start_mi, 1),
                "segment_end_mi": round(r.segment_end_mi, 1),
                "path": segment_path(coords, cum, r.segment_start_mi, r.segment_end_mi),
            }
            for r in a.checkpoints
        ],
    }