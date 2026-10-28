from datetime import datetime, timedelta, timezone

import pytest
from rest_framework.test import APIClient

from routing import views
from routing.services.routing_provider import Route


def today0():
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def fake_hourly(wind=10.0, hours=24 * 16):
    t0 = today0()
    return {"hourly": {
        "time": [(t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(hours)],
        "wind_speed_10m": [wind] * hours,
        "wind_gusts_10m": [wind] * hours,
        "rain": [0.0] * hours,
        "showers": [0.0] * hours,
        "snowfall": [0.0] * hours,
    }}


def two_routes(*args, **kwargs):
    return [
        Route("test", [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)], 138, 4.0),
        Route("test", [(0.0, 0.0), (1.0, 0.5), (2.0, 0.0)], 150, 5.0),
    ]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(views, "get_route_options", two_routes)
    monkeypatch.setattr(views, "fetch_hourly", lambda pts: [fake_hourly() for _ in pts])
    return APIClient()


def payload(**over):
    body = {
        "origin": {"lat": 0.0, "lon": 0.0},
        "destination": {"lat": 0.0, "lon": 2.0},
        "departure": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        "load_lb": 42_000,
        "interval_mi": 25,
    }
    body.update(over)
    return body


def test_analyze_returns_ranked_routes_and_heatmap(client):
    r = client.post("/api/analyze", payload(), format="json")
    assert r.status_code == 200
    data = r.json()
    assert len(data["routes"]) == 2
    assert sum(1 for x in data["routes"] if x["recommended"]) == 1
    assert data["routes"][0]["rank"] == 1
    assert data["routes"][0]["checkpoints"][0]["path"]
    assert data["heatmap"]["hours"] == 48
    assert len(data["heatmap"]["points"][0]["levels"]) == 48


def test_rejects_bad_load(client):
    assert client.post("/api/analyze", payload(load_lb=0), format="json").status_code == 400


def test_rejects_departure_beyond_forecast(client):
    far = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    assert client.post("/api/analyze", payload(departure=far), format="json").status_code == 400


def test_no_route_gives_404(client, monkeypatch):
    monkeypatch.setattr(views, "get_route_options", lambda *a, **k: [])
    assert client.post("/api/analyze", payload(), format="json").status_code == 404


def test_geocode(client, monkeypatch):
    monkeypatch.setattr(views, "search_places", lambda q: [{"label": "Dallas, Texas", "lat": 32.7, "lon": -96.8}])
    r = client.get("/api/geocode", {"q": "dallas"})
    assert r.json()["results"][0]["label"] == "Dallas, Texas"