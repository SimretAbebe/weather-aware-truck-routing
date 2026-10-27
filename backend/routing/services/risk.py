from dataclasses import dataclass
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


# Upper bound (exclusive) of each band: LOW, MODERATE, HIGH, SEVERE.
# Anything at or above the last bound is NO_TRAVEL.
WIND_BOUNDS = (25, 35, 45, 55)           # mph
RAIN_BOUNDS = (0.10, 0.25, 0.50, 1.00)   # in/hr
SNOW_BOUNDS = (0.5, 1.0, 2.0, 3.0)       # in/hr


def _classify(value: float, bounds: tuple, *, top_inclusive: bool = False) -> Risk:
    """Map a value to a Risk level. Lower bound of each band is inclusive."""
    for level, upper in zip(
        (Risk.LOW, Risk.MODERATE, Risk.HIGH, Risk.SEVERE), bounds
    ):
        last = level == Risk.SEVERE
        if value < upper or (last and top_inclusive and value == upper):
            return level
    return Risk.NO_TRAVEL


def classify_wind(mph: float) -> Risk:
    return _classify(mph, WIND_BOUNDS)


def classify_rain(in_hr: float) -> Risk:
    # Spec: Severe is 0.50-1.00, No Travel is >1.00, so 1.00 itself is Severe.
    return _classify(in_hr, RAIN_BOUNDS, top_inclusive=True)


def classify_snow(in_hr: float) -> Risk:
    # Spec: Severe is 2.0-3.0, No Travel is >3.0, so 3.0 itself is Severe.
    return _classify(in_hr, SNOW_BOUNDS, top_inclusive=True)


@dataclass(frozen=True)
class RiskResult:
    level: Risk
    wind: Risk
    rain: Risk
    snow: Risk
    load_override: bool  # True if the load rules raised the level


def apply_load_rules(wind_mph: float, load_lb: float, base: Risk) -> Risk:
    if wind_mph >= 55:
        return Risk.NO_TRAVEL
    if 45 <= wind_mph < 55 and load_lb > 30_000:
        return Risk.NO_TRAVEL
    if 35 <= wind_mph < 45 and load_lb > 40_000:
        return max(base, Risk.SEVERE)
    return base


def assess(wind_mph: float, rain_in_hr: float, snow_in_hr: float, load_lb: float) -> RiskResult:
    wind = classify_wind(wind_mph)
    rain = classify_rain(rain_in_hr)
    snow = classify_snow(snow_in_hr)
    base = max(wind, rain, snow)
    final = apply_load_rules(wind_mph, load_lb, base)
    return RiskResult(final, wind, rain, snow, load_override=final > base)