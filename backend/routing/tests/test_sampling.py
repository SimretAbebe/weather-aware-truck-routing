from datetime import datetime, timezone

import pytest

from routing.services.sampling import sample_checkpoints

DEP = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)
# ~138 miles due east along the equator (2 degrees of longitude)
LINE = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]


def test_first_and_last_checkpoints():
    cps = sample_checkpoints(LINE, duration_h=4, departure=DEP, interval_mi=50)
    assert cps[0].mile == 0 and cps[0].eta == DEP
    assert cps[-1].lon == pytest.approx(2.0)
    assert (cps[-1].eta - DEP).total_seconds() == pytest.approx(4 * 3600)


def test_checkpoint_spacing_and_count():
    cps = sample_checkpoints(LINE, duration_h=4, departure=DEP, interval_mi=50)
    assert [round(c.mile) for c in cps[:3]] == [0, 50, 100]
    assert len(cps) == 4  # 0, 50, 100, end (~138)


def test_eta_proportional_to_distance():
    cps = sample_checkpoints(LINE, duration_h=4, departure=DEP, interval_mi=50)
    total = cps[-1].mile
    mid = cps[1]
    assert (mid.eta - DEP).total_seconds() == pytest.approx(4 * 3600 * mid.mile / total)


def test_interpolates_between_points():
    cps = sample_checkpoints(LINE, duration_h=4, departure=DEP, interval_mi=50)
    assert 0.7 < cps[1].lon < 0.8  # 50 mi is ~0.72 degrees of longitude


def test_rejects_bad_input():
    with pytest.raises(ValueError):
        sample_checkpoints(LINE, 4, DEP, 0)
    with pytest.raises(ValueError):
        sample_checkpoints([(0, 0)], 4, DEP, 10)