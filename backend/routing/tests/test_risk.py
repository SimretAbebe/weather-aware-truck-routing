import pytest
from routing.services.risk import Risk, assess, classify_wind, classify_rain, classify_snow


@pytest.mark.parametrize("mph,expected", [
    (0, Risk.LOW), (24.9, Risk.LOW),
    (25, Risk.MODERATE), (34.9, Risk.MODERATE),
    (35, Risk.HIGH), (44.9, Risk.HIGH),
    (45, Risk.SEVERE), (54.9, Risk.SEVERE),
    (55, Risk.NO_TRAVEL), (80, Risk.NO_TRAVEL),
])
def test_wind_bands(mph, expected):
    assert classify_wind(mph) == expected


@pytest.mark.parametrize("v,expected", [
    (0.09, Risk.LOW), (0.10, Risk.MODERATE), (0.24, Risk.MODERATE),
    (0.25, Risk.HIGH), (0.49, Risk.HIGH), (0.50, Risk.SEVERE),
    (1.00, Risk.SEVERE), (1.01, Risk.NO_TRAVEL),
])
def test_rain_bands(v, expected):
    assert classify_rain(v) == expected


@pytest.mark.parametrize("v,expected", [
    (0.4, Risk.LOW), (0.5, Risk.MODERATE), (1.0, Risk.HIGH),
    (2.0, Risk.SEVERE), (3.0, Risk.SEVERE), (3.01, Risk.NO_TRAVEL),
])
def test_snow_bands(v, expected):
    assert classify_snow(v) == expected


def test_worst_of_three_wins():
    assert assess(10, 0.6, 0.0, 10_000).level == Risk.SEVERE


def test_extreme_wind_is_no_travel_for_any_load():
    assert assess(55, 0, 0, 1_000).level == Risk.NO_TRAVEL


def test_severe_wind_heavy_load_is_no_travel():
    assert assess(50, 0, 0, 30_001).level == Risk.NO_TRAVEL
    assert assess(50, 0, 0, 30_000).level == Risk.SEVERE  # not strictly >


def test_high_wind_very_heavy_load_is_severe():
    r = assess(40, 0, 0, 40_001)
    assert r.level == Risk.SEVERE and r.load_override
    assert assess(40, 0, 0, 40_000).level == Risk.HIGH


def test_load_rule_never_lowers_risk():
    assert assess(40, 1.5, 0, 50_000).level == Risk.NO_TRAVEL