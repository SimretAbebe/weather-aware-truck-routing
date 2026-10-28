from datetime import datetime, timedelta, timezone

import pytest

from routing.services.analysis import analyze_routes, segment_bounds
from routing.services.risk import Risk
from routing.services.routing_provider import Route

T0 = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)


def hourly(wind=0.0, rain=0.0, snow=0.0, hours=48):
    return {"hourly": {
        "time": [(T0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)],
        "wind_speed_10m": [wind] * hours,
        "wind_gusts_10m": [wind] * hours,
        "rain": [rain] * hours,
        "showers": [0.0] * hours,
        "snowfall": [snow] * hours,
    }}


def fetcher(fn):
    """fn(lon, lat) -> dict of weather kwargs."""
    return lambda points: [hourly(**fn(lon, lat)) for lon, lat in points]


def line(lat, duration):
    return Route("test", [(0.0, lat), (1.0, lat), (2.0, lat)], 138, duration)


def test_segments_cover_whole_route():
    b = segment_bounds([0, 50, 100, 138])
    assert b[0][0] == 0 and b[-1][1] == 138
    assert sum(e - s for s, e in b) == pytest.approx(138)


def test_load_rules_applied_per_checkpoint():
    calm_heavy = fetcher(lambda lon, lat: {"wind": 40})
    heavy = analyze_routes([line(0, 4)], T0, 45_000, 50, calm_heavy)[0]
    assert heavy.max_risk == Risk.SEVERE
    assert heavy.miles_by_level[Risk.SEVERE] == pytest.approx(heavy.total_mi)

    light = analyze_routes([line(0, 4)], T0, 20_000, 50, calm_heavy)[0]
    assert light.max_risk == Risk.HIGH


def test_fewer_severe_miles_beats_faster_route():
    wx = fetcher(lambda lon, lat: {"wind": 50 if lat > 0.5 else 10})
    slow_safe, fast_risky = line(0, 5), line(1, 3)
    result = analyze_routes([fast_risky, slow_safe], T0, 20_000, 25, wx)
    assert result[0].route is slow_safe and result[0].recommended
    assert result[1].rank == 2 and "Severe" in result[1].reason


def test_no_travel_ranks_below_severe():
    wx = fetcher(lambda lon, lat: {"wind": 55 if lat < 0.5 else 50})
    no_travel_fast, severe_slow = line(0, 3), line(1, 5)
    result = analyze_routes([no_travel_fast, severe_slow], T0, 20_000, 25, wx)
    assert result[0].route is severe_slow


def test_duration_breaks_ties():
    wx = fetcher(lambda lon, lat: {"wind": 10})
    slow, fast = line(0, 5), line(1, 3)
    result = analyze_routes([slow, fast], T0, 20_000, 25, wx)
    assert result[0].route is fast


def test_rejects_bad_interval():
    with pytest.raises(ValueError):
        analyze_routes([line(0, 4)], T0, 20_000, 30, fetcher(lambda a, b: {}))