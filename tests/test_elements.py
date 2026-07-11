"""Sanity checks for the core ephemeris-direct Besselian element formula.

Only x/y/d/l1/l2/tanf1/tanf2 are checked precisely against the
published a0 values -- mu0 is checked with a much looser tolerance,
since it differs from published tables by an amount proportional to
the difference between Skyfield's own Delta-T and the Delta-T those
tables were built with (documented in elements.py). This is expected,
not a regression to guard tightly.
"""

import pytest

from eclipse_calc.elements import bessels_at

# NASA GSFC SEdata a0 values, T0 = 2026-08-12 18.000 TD.
REFERENCE_A0 = dict(x=0.4755140, y=0.7711830, d=14.79667, l1=0.537955, l2=-0.008142,
                     tanf1=0.0046141, tanf2=0.0045911)


def test_bessels_at_matches_reference_a0(ephemeris, t0):
    B = bessels_at(t0, ephemeris)
    row = B.iloc[0]

    for col in ("x", "y", "d", "l1", "l2", "tanf1", "tanf2"):
        assert row[col] == pytest.approx(REFERENCE_A0[col], abs=2e-4), col

    # mu0: loose tolerance, see module docstring.
    assert row["mu0"] == pytest.approx(88.747787, abs=0.5)


def test_bessels_at_accepts_scalar_or_vector_time(ephemeris, t0, timescale):
    scalar_result = bessels_at(t0, ephemeris)
    vector_result = bessels_at(timescale.tt_jd([t0.tt]), ephemeris)
    assert scalar_result.equals(vector_result)
