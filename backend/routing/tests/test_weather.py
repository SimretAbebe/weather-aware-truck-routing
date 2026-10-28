from datetime import datetime, timedelta, timezone

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