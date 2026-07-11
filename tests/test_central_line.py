"""Central line and N/S umbral limits vs. the review brief's reference table."""

import pytest

# Central-line lat/lon fixes, from PYTHON_REVIEW_BRIEF.md Sec. 0 (ytliu/DE441).
CENTRAL_LINE_REFERENCE = [
    # (hour, minute, ref_lat, ref_lon)
    (18, 18, 49.3100, -14.2783),
    (18, 22, 47.1267, -11.7600),
    (18, 26, 44.7417, -8.4567),
    (18, 30, 41.8567, -3.2833),
]

# N/S umbral limit fixes, from the same table.
LIMIT_REFERENCE = [
    # (hour, minute, ref_n_lat, ref_n_lon, ref_s_lat, ref_s_lon)
    (18, 18, 49.3533, -11.5883, 49.2050, -16.8017),
    (18, 22, 47.0650, -8.8517, 47.1067, -14.4383),
    (18, 26, 44.4883, -5.0217, 44.8583, -11.4717),
    (18, 30, 40.7483, 3.0400, 42.2950, -7.3083),
]

# Reference lat/lon fixes are given to 4 decimal places (~10m); real-world
# tolerance here is dominated by the ~200-400m agreement already established
# between this event's oracle and the ytliu/DE441 reference (see
# PYTHON_REVIEW_FINDINGS.md), not by floating-point precision.
POSITION_TOL_DEG = 0.02


@pytest.mark.parametrize("hour,minute,ref_lat,ref_lon", CENTRAL_LINE_REFERENCE)
def test_central_line_matches_reference(eclipse, timescale, hour, minute, ref_lat, ref_lon):
    t = timescale.utc(2026, 8, 12, hour, minute, 0)
    central = eclipse.central_line(t)

    assert central.lat.iloc[0] == pytest.approx(ref_lat, abs=POSITION_TOL_DEG)
    assert central.lon.iloc[0] == pytest.approx(ref_lon, abs=POSITION_TOL_DEG)


def test_central_duration_and_width_are_positive_near_max(eclipse, timescale):
    t = timescale.utc(2026, 8, 12, 18, 26, 0)
    central = eclipse.central_line(t)

    assert central.duration_s.iloc[0] > 0
    assert central.width.iloc[0] > 0


@pytest.mark.parametrize("hour,minute,ref_n_lat,ref_n_lon,ref_s_lat,ref_s_lon", LIMIT_REFERENCE)
def test_umbral_limits_match_reference(
    eclipse, timescale, hour, minute, ref_n_lat, ref_n_lon, ref_s_lat, ref_s_lon
):
    t = timescale.utc(2026, 8, 12, hour, minute, 0)
    limits = eclipse.shadow_limits(t, umbra=True)

    assert limits.N_lat.iloc[0] == pytest.approx(ref_n_lat, abs=POSITION_TOL_DEG)
    assert limits.N_lon.iloc[0] == pytest.approx(ref_n_lon, abs=POSITION_TOL_DEG)
    assert limits.S_lat.iloc[0] == pytest.approx(ref_s_lat, abs=POSITION_TOL_DEG)
    assert limits.S_lon.iloc[0] == pytest.approx(ref_s_lon, abs=POSITION_TOL_DEG)
