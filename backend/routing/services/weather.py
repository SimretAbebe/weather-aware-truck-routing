from dataclasses import dataclass
from datetime import datetime, timezone

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
CHUNK = 50  # coordinates per request, keeps the URL short


@dataclass(frozen=True)
class WeatherSample:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float
    forecast_time: datetime
    beyond_forecast: bool  # ETA fell outside the available forecast window


def fetch_hourly(points: list[tuple[float, float]]) -> list[dict]:
    """points are (lon, lat). Returns one hourly-forecast dict per point, in order."""
    results: list[dict] = []
    for i in range(0, len(points), CHUNK):
        chunk = points[i : i + CHUNK]
        r = requests.get(
            FORECAST_URL,
            params={
                "latitude": ",".join(f"{lat:.4f}" for _, lat in chunk),
                "longitude": ",".join(f"{lon:.4f}" for lon, _ in chunk),
                "hourly": HOURLY_VARS,
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "GMT",
                "forecast_days": 16,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        results.extend(data if isinstance(data, list) else [data])
    return results


def _parse(t: str) -> datetime:
    return datetime.fromisoformat(t).replace(tzinfo=timezone.utc)


def weather_at(hourly: dict, eta: datetime) -> WeatherSample:
    """Pick the forecast hour nearest to eta (UTC-aware)."""
    h = hourly["hourly"]
    times = h["time"]
    start = _parse(times[0])
    idx = round((eta - start).total_seconds() / 3600)
    beyond = idx < 0 or idx >= len(times)
    idx = max(0, min(idx, len(times) - 1))

    def val(name: str) -> float:
        v = h[name][idx]
        return float(v) if v is not None else 0.0

    return WeatherSample(
        wind_mph=val("wind_speed_10m"),
        gust_mph=val("wind_gusts_10m"),
        rain_in_hr=val("rain") + val("showers"),
        snow_in_hr=val("snowfall"),
        forecast_time=_parse(times[idx]),
        beyond_forecast=beyond,
    )