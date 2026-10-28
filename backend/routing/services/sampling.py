from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta

from .routing_provider import Coord, haversine_mi


@dataclass(frozen=True)
class Checkpoint:
    index: int
    mile: float
    lon: float
    lat: float
    eta: datetime


def cumulative_miles(coords: list[Coord]) -> list[float]:
    cum = [0.0]
    for a, b in zip(coords, coords[1:]):
        cum.append(cum[-1] + haversine_mi(a, b))
    return cum


def sample_checkpoints(
    coords: list[Coord],
    duration_h: float,
    departure: datetime,
    interval_mi: float,
) -> list[Checkpoint]:
    """Place a checkpoint every interval_mi along the route (plus the final point).

    ETA assumes a constant average speed: elapsed time is proportional to
    distance travelled. `departure` should be timezone-aware (UTC).
    """
    if len(coords) < 2:
        raise ValueError("A route needs at least two points")
    if interval_mi <= 0:
        raise ValueError("interval_mi must be positive")

    cum = cumulative_miles(coords)
    total = cum[-1]

    targets = []
    t = 0.0
    while t < total:
        targets.append(t)
        t += interval_mi
    targets.append(total)

    checkpoints = []
    for i, mile in enumerate(targets):
        j = min(bisect_left(cum, mile), len(cum) - 1)
        if j == 0:
            lon, lat = coords[0]
        else:
            seg = cum[j] - cum[j - 1]
            f = (mile - cum[j - 1]) / seg if seg else 0.0
            (lon1, lat1), (lon2, lat2) = coords[j - 1], coords[j]
            lon, lat = lon1 + f * (lon2 - lon1), lat1 + f * (lat2 - lat1)
        eta = departure + timedelta(hours=duration_h * (mile / total if total else 0))
        checkpoints.append(Checkpoint(i, mile, lon, lat, eta))
    return checkpoints