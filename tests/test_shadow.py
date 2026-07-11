"""Sanity checks for the shadow footprint outline and N/S limits.

Unlike the central-line/site tests, there's no independently-published
reference for the *full* umbral outline shape (only its two N/S limit
points, tested in test_central_line.py) or for penumbral limits at
all -- these checks confirm the geometry is well-formed and physically
plausible, not exact position agreement.
"""

import pytest


def test_umbral_outline_is_a_closed_finite_polygon(eclipse, timescale):
    t = timescale.utc(2026, 8, 12, 18, 26, 0)
    outline = eclipse.shadow_outline(t, umbra=True, points=36)

    assert len(outline) == 37  # points + 1
    assert outline["Q_lat"].notna().all()
    assert outline["Q_lon"].notna().all()

    first, last = outline.iloc[0], outline.iloc[-1]
    assert first["Q_lat"] == pytest.approx(last["Q_lat"], abs=1e-6)
    assert first["Q_lon"] == pytest.approx(last["Q_lon"], abs=1e-6)


def test_umbral_outline_brackets_the_central_line(eclipse, timescale):
    """The outline's centroid should sit close to the central line, and
    the umbral path's known ~300km width should show up as the outline's
    latitude spread (roughly perpendicular to the path here)."""
    t = timescale.utc(2026, 8, 12, 18, 26, 0)
    outline = eclipse.shadow_outline(t, umbra=True, points=72)
    central = eclipse.central_line(t)

    centroid_lat = outline["Q_lat"].mean()
    centroid_lon = outline["Q_lon"].mean()
    assert centroid_lat == pytest.approx(central.lat.iloc[0], abs=1.0)
    assert centroid_lon == pytest.approx(central.lon.iloc[0], abs=1.0)

    lat_span_km = (outline["Q_lat"].max() - outline["Q_lat"].min()) * 111
    assert 50 < lat_span_km < 1000  # sanity bounds, not a precise width check


def test_umbral_limits_are_north_and_south_of_the_central_line(eclipse, timescale):
    """N/S here means "either side of the path", not simple compass
    order -- the path runs diagonally across Spain, so N_lat can be
    smaller than S_lat at a given instant (confirmed against the
    review brief's own reference table). What must hold regardless of
    labeling is that the central line sits between them."""
    t = timescale.utc(2026, 8, 12, 18, 26, 0)
    central = eclipse.central_line(t)
    limits = eclipse.shadow_limits(t, umbra=True)

    lats = sorted([limits.N_lat.iloc[0], limits.S_lat.iloc[0]])
    assert lats[0] < central.lat.iloc[0] < lats[1]


def test_south_limit_converges_independently_of_north_failure(eclipse, timescale):
    """Regression test: shadow_limits used to declare `L` once outside the
    `for offset in (0, pi)` loop instead of resetting it per offset. When
    the first offset (north) failed to converge -- expected and correct
    this close to this event's sunset cusp, the north limit genuinely
    stops existing from 18:31 UT onward -- the resulting NaN leaked into
    `L` for the second offset (south)'s starting point, spuriously
    failing it too, even though south converges cleanly on its own.
    Reference values: ytliu.epizy.com's independently-published south
    limit for these two minutes (PYTHON_REVIEW_BRIEF.md Sec 0)."""
    cases = [
        # (hour, minute, ref_s_lat, ref_s_lon)
        (18, 31, 41.5517, -5.8850),
        (18, 32, 40.7233, -4.1417),
    ]
    for hour, minute, ref_s_lat, ref_s_lon in cases:
        t = timescale.utc(2026, 8, 12, hour, minute, 0)
        limits = eclipse.shadow_limits(t, umbra=True)
        assert "S_lat" in limits.columns and limits["S_lat"].notna().all(), (
            f"south limit failed to converge at 18:{minute} -- "
            "regression of the L-not-reset-per-offset bug"
        )
        assert limits.S_lat.iloc[0] == pytest.approx(ref_s_lat, abs=0.02)
        assert limits.S_lon.iloc[0] == pytest.approx(ref_s_lon, abs=0.02)
        # North is expected to genuinely not exist this close to the
        # sunset cusp -- its absence here is correct, not a bug.


def test_penumbral_shadow_limits_does_not_crash(eclipse, timescale):
    """umbra=False is not independently validated (see shadow.py's
    docstring) and can legitimately drop a non-converging tangent
    point -- this just confirms it degrades gracefully rather than
    raising or silently returning an off-Earth result."""
    t = timescale.utc(2026, 8, 12, 18, 26, 0)
    limits = eclipse.shadow_limits(t, umbra=False)

    for col in ("N_lat", "S_lat"):
        if col in limits.columns and limits[col].notna().any():
            assert -90 <= limits[col].iloc[0] <= 90
