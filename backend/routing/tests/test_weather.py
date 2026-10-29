from datetime import datetime, timedelta, timezone

import requests

from routing.services import weather
from routing.services.weather import weather_at

T0 = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)


def fake(hours=48):
    return {"hourly": {
        "time": [(T0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)],
        "wind_speed_10m": [float(i) for i in range(hours)],
        "wind_gusts_10m": [float(i) + 10 for i in range(hours)],
        "rain": [0.01 * i for i in range(hours)],
        "showers": [0.0] * hours,
        "snowfall": [None] * hours,
    }}


def test_picks_nearest_hour():
    s = weather_at(fake(), T0 + timedelta(hours=5, minutes=20))
    assert s.wind_mph == 5 and not s.beyond_forecast
    s = weather_at(fake(), T0 + timedelta(hours=5, minutes=40))
    assert s.wind_mph == 6


def test_none_values_become_zero():
    assert weather_at(fake(), T0).snow_in_hr == 0.0


def test_flags_eta_beyond_forecast():
    s = weather_at(fake(), T0 + timedelta(hours=100))
    assert s.beyond_forecast and s.wind_mph == 47  # clamped to last hour



def test_fetch_hourly_dedupes_and_caches(monkeypatch):
    weather._cache.clear()
    calls = []

    def fake_chunk(chunk):
        calls.append(list(chunk))
        return [{"hourly": {}, "pt": p} for p in chunk]

    monkeypatch.setattr(weather, "_fetch_chunk", fake_chunk)
    pts = [(-96.801, 32.701), (-96.804, 32.704), (-90.0, 40.0)]  # first two share a cell
    out = weather.fetch_hourly(pts)
    assert len(out) == 3 and out[0] is out[1]
    assert sum(len(c) for c in calls) == 2
    weather.fetch_hourly(pts)
    assert len(calls) == 1  # second call served from cache


def test_retries_on_rate_limit(monkeypatch):
    class Resp:
        def __init__(self, code):
            self.status_code = code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError()

        def json(self):
            return {"ok": 1}

    responses = iter([Resp(429), Resp(200)])
    monkeypatch.setattr(weather.requests, "get", lambda *a, **k: next(responses))
    monkeypatch.setattr(weather.time, "sleep", lambda s: None)
    assert weather._fetch_chunk([(0.0, 0.0)]) == [{"ok": 1}]
