from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from .risk import Risk, RiskResult, assess
from .routing_provider import Route
from .sampling import Checkpoint, sample_checkpoints
from .weather import WeatherSample, fetch_hourly, weather_at

VALID_INTERVALS = (10, 25, 50)
RANK_LABELS = ("No Travel miles", "Severe miles", "High miles", "average risk", "travel time")


@dataclass(frozen=True)
class CheckpointResult:
    checkpoint: Checkpoint
    weather: WeatherSample
    risk: RiskResult
    segment_start_mi: float
    segment_end_mi: float

    @property
    def segment_mi(self) -> float:
        return self.segment_end_mi - self.segment_start_mi


@dataclass
class RouteAnalysis:
    route: Route
    checkpoints: list[CheckpointResult]
    miles_by_level: dict[Risk, float]
    total_mi: float
    avg_risk: float          # mile-weighted, 0 (Low) to 4 (No Travel)
    max_risk: Risk
    duration_h: float
    beyond_forecast: bool
    rank: int = 0
    recommended: bool = False
    reason: str = ""


def segment_bounds(miles: list[float]) -> list[tuple[float, float]]:
    """Each checkpoint owns the road halfway to its neighbours.
    The first starts at mile 0 and the last ends at the route's total, so the
    segments always add up to the full distance."""
    total = miles[-1]
    bounds = []
    for i, m in enumerate(miles):
        start = 0.0 if i == 0 else (miles[i - 1] + m) / 2
        end = total if i == len(miles) - 1 else (m + miles[i + 1]) / 2
        bounds.append((start, end))
    return bounds


def summarize(route: Route, results: list[CheckpointResult]) -> RouteAnalysis:
    by_level = {lvl: 0.0 for lvl in Risk}
    for r in results:
        by_level[r.risk.level] += r.segment_mi
    total = sum(by_level.values())
    weighted = sum(int(lvl) * mi for lvl, mi in by_level.items())
    return RouteAnalysis(
        route=route,
        checkpoints=results,
        miles_by_level=by_level,
        total_mi=total,
        avg_risk=weighted / total if total else 0.0,
        max_risk=max((r.risk.level for r in results), default=Risk.LOW),
        duration_h=route.duration_h,
        beyond_forecast=any(r.weather.beyond_forecast for r in results),
    )


def rank_key(a: RouteAnalysis) -> tuple:
    """Lower is better. Order: No Travel miles, Severe, High, avg risk, time.
    Miles are rounded to 0.1 so floating-point noise can't decide a ranking."""
    m = a.miles_by_level
    return (
        round(m[Risk.NO_TRAVEL], 1),
        round(m[Risk.SEVERE], 1),
        round(m[Risk.HIGH], 1),
        round(a.avg_risk, 2),
        round(a.duration_h, 2),
    )


def first_difference(a: RouteAnalysis, b: RouteAnalysis):
    for label, x, y in zip(RANK_LABELS, rank_key(a), rank_key(b)):
        if x != y:
            return label, x, y
    return None


def rank_routes(analyses: list[RouteAnalysis]) -> list[RouteAnalysis]:
    ordered = sorted(analyses, key=rank_key)
    best = ordered[0]
    for i, a in enumerate(ordered, start=1):
        a.rank = i
        a.recommended = i == 1
        if len(ordered) == 1:
            a.reason = "Only route available."
        elif i == 1:
            d = first_difference(a, ordered[1])
            a.reason = (
                f"Better than the next-best route on {d[0]} ({d[1]} vs {d[2]})."
                if d else "Tied with the next-best route on every criterion."
            )
        else:
            d = first_difference(a, best)
            a.reason = (
                f"Worse than the recommended route on {d[0]} ({d[1]} vs {d[2]})."
                if d else "Tied with the recommended route on every criterion."
            )
    return ordered


def analyze_routes(
    routes: list[Route],
    departure: datetime,
    load_lb: float,
    interval_mi: int = 25,
    fetch: Callable[[list], list] = fetch_hourly,
) -> list[RouteAnalysis]:
    if interval_mi not in VALID_INTERVALS:
        raise ValueError(f"interval_mi must be one of {VALID_INTERVALS}")
    if departure.tzinfo is None:
        raise ValueError("departure must be timezone-aware")
    if not routes:
        raise ValueError("no routes to analyze")

    sampled = [
        sample_checkpoints(r.coords, r.duration_h, departure, interval_mi) for r in routes
    ]

    # One batched weather request for every checkpoint on every route.
    points = [(c.lon, c.lat) for cps in sampled for c in cps]
    hourly = fetch(points)
    if len(hourly) != len(points):
        raise RuntimeError("weather provider returned an unexpected number of points")

    analyses, pos = [], 0
    for route, cps in zip(routes, sampled):
        bounds = segment_bounds([c.mile for c in cps])
        results = []
        for cp, (start, end) in zip(cps, bounds):
            w = weather_at(hourly[pos], cp.eta)
            pos += 1
            risk = assess(w.wind_mph, w.rain_in_hr, w.snow_in_hr, load_lb)
            results.append(CheckpointResult(cp, w, risk, start, end))
        analyses.append(summarize(route, results))

    return rank_routes(analyses)