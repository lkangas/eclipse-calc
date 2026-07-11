"""Whole-path (terminator-limited) contact times vs. the review brief's global facts."""

import pytest

# From PYTHON_REVIEW_BRIEF.md Sec. 0: "C1 of the whole path" / "C2 of the whole
# path" -- these are the shadow AXIS first/last touching Earth (this
# package's CE1/CE2), not the umbral outer edge (U1/U4).
REFERENCE_CE1 = dict(hour=17, minute=0, second=7, lat=75.0783, lon=113.4433)
REFERENCE_CE2 = dict(hour=18, minute=32, second=12, lat=38.6800, lon=5.4017)

POSITION_TOL_DEG = 0.01
TIME_TOL_S = 2


def test_terminator_events_ce1_ce2_match_whole_path_reference(eclipse):
    events = eclipse.terminator_events()

    assert "CE1" in events.index
    assert "CE2" in events.index

    ce1, ce2 = events.loc["CE1"], events.loc["CE2"]

    ce1_ref_seconds = REFERENCE_CE1["hour"] * 3600 + REFERENCE_CE1["minute"] * 60 + REFERENCE_CE1["second"]
    ce1_seconds = ce1.time.hour * 3600 + ce1.time.minute * 60 + ce1.time.second
    assert ce1_seconds == pytest.approx(ce1_ref_seconds, abs=TIME_TOL_S)
    assert ce1.lat == pytest.approx(REFERENCE_CE1["lat"], abs=POSITION_TOL_DEG)
    assert ce1.lon == pytest.approx(REFERENCE_CE1["lon"], abs=POSITION_TOL_DEG)

    ce2_ref_seconds = REFERENCE_CE2["hour"] * 3600 + REFERENCE_CE2["minute"] * 60 + REFERENCE_CE2["second"]
    ce2_seconds = ce2.time.hour * 3600 + ce2.time.minute * 60 + ce2.time.second
    assert ce2_seconds == pytest.approx(ce2_ref_seconds, abs=TIME_TOL_S)
    assert ce2.lat == pytest.approx(REFERENCE_CE2["lat"], abs=POSITION_TOL_DEG)
    assert ce2.lon == pytest.approx(REFERENCE_CE2["lon"], abs=POSITION_TOL_DEG)


def test_terminator_events_omits_events_that_dont_occur(eclipse):
    """P2/P3 (the whole penumbral shadow being on Earth at once)
    legitimately don't occur for this deep an eclipse -- confirms they're
    cleanly omitted rather than crashing the whole call (see terminator.py)."""
    events = eclipse.terminator_events()
    assert "P2" not in events.index
    assert "P3" not in events.index
    # but the ones that do occur should still all be present
    for name in ("P1", "P4", "U1", "U2", "U3", "U4", "CE1", "CE2"):
        assert name in events.index


def test_all_reported_longitudes_are_normalized(eclipse):
    """Regression check for the longitude-wrapping fix in ellipsoid.py --
    terminator_events evaluates far enough from t0 that an unwrapped
    longitude would show up here (it did, before the fix)."""
    events = eclipse.terminator_events()
    assert (events.lon >= -180).all()
    assert (events.lon < 180).all()
