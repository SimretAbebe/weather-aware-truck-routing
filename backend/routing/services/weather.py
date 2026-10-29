import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall"
CHUNK = 50                    # coordinates per request, keeps the URL short
RETRYABLE = {429, 500, 502, 503, 504}
RETRY_DELAYS = (3, 8, 20)     # seconds between attempts
CACHE_TTL = 30 * 60           # seconds
CACHE_MAX = 4000              # entries; cleared wholesale if exceeded

# Forecasts are cached per 0.1 degree cell (about 7 miles), which is finer than
# the weather models' own grid, so nearby checkpoints share one forecast.
_cache: dict[tuple[float, float], tuple[float, dict]] = {}
_lock = threading.Lock()


@dataclass(frozen=True)
class WeatherSample:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float
    snow_in_hr: float
    forecast_time: datetime
    beyond_forecast: bool  # ETA fell outside the available forecast window


def _key(lon: float, lat: float) -> tuple[float, float]:
    return (round(lat, 1), round(lon, 1))


def _fetch_chunk(chunk: list[tuple[float, float]]) -> list[dict]:
    """chunk holds (lon, lat) pairs. Retries on rate limits and server errors."""
    params = {
        "latitude": ",".join(f"{lat:.4f}" for _, lat in chunk),
        "longitude": ",".join(f"{lon:.4f}" for lon, _ in chunk),
        "hourly": HOURLY_VARS,
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "GMT",
        "forecast_days": 16,
    }
    for delay in (*RETRY_DELAYS, None):
        r = requests.get(FORECAST_URL, params=params, timeout=30)
        if r.status_code in RETRYABLE and delay is not None:
            time.sleep(delay)
            continue
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else [data]


def _load_chunk(keys: list[tuple[float, float]]) -> None:
    data = _fetch_chunk([(lon, lat) for lat, lon in keys])
    now = time.time()
    for k, d in zip(keys, data):  # stored per chunk, so progress survives a later failure
        _cache[k] = (now, d)


def fetch_hourly(points: list[tuple[float, float]]) -> list[dict]:
    """points are (lon, lat). Returns one hourly-forecast dict per point, in order."""
    keys = [_key(lon, lat) for lon, lat in points]
    with _lock:
        now = time.time()
        if len(_cache) > CACHE_MAX:
            _cache.clear()
        missing = list(dict.fromkeys(
            k for k in keys if k not in _cache or now - _cache[k][0] > CACHE_TTL
        ))
        chunks = [missing[i : i + CHUNK] for i in range(0, len(missing), CHUNK)]
        if chunks:
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(_load_chunk, chunks))
    return [_cache[k][1] for k in keys]


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