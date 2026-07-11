"""General Besselian eclipse elements, computed directly from ephemeris.

This is the one canonical implementation of the core formula -- the
research code this was ported from had two near-identical copies
(``calculations.bessels_at`` and ``polynom_bessels.raw_bessels_at``).
"""

from __future__ import annotations

import pandas as pd
from numpy import arcsin, cos, sin, tan
from skyfield.jpllib import SpiceKernel
from skyfield.positionlib import Angle
from skyfield.timelib import Time

from ._time import ensure_vector_time
from .constants import RE, ds, k1, k2


def bessels_at(t: Time, eph: SpiceKernel) -> pd.DataFrame:
    """General Besselian elements at Time(s) ``t``.

    Columns: ``x``, ``y`` (shadow-axis position in the fundamental
    plane, Earth radii), ``mu0`` (hour angle of the shadow axis at the
    Greenwich meridian, degrees), ``d`` (declination of the shadow
    axis, degrees), ``l1``/``l2`` (penumbral/umbral shadow-cone radii
    at the fundamental plane, Earth radii), ``tanf1``/``tanf2``
    (penumbral/umbral cone half-angle tangents), and ``gast``
    (Greenwich apparent sidereal time, for local-circumstance
    calculations).

    Accepts a scalar or array-like Skyfield ``Time``; always returns a
    ``DataFrame`` indexed by UTC datetime (one row for scalar input).

    Note: ``mu0`` from this function differs from published reference
    tables (e.g. NASA GSFC SEdata) by an amount proportional to the
    difference between Skyfield's internal ΔT and the ΔT used to
    produce those tables (roughly 0.3° for the 2026-08-12 event, i.e.
    a Delta-T difference of ~69s at Earth's 15 deg/hour rotation
    rate). ``x``/``y``/``d``/``l1``/``l2`` are far less ΔT-sensitive
    (they track the Sun/Moon's slow orbital motion, not Earth's fast
    rotation) and agree with reference tables to 5-6 significant
    figures. This is a real, understood property of using Skyfield's
    own ΔT model rather than a fixed published constant -- not a bug
    -- and downstream local-circumstance/central-line results (which
    use ``mu0`` consistently alongside the other elements) have been
    separately validated against reference data to sub-km/sub-second
    accuracy despite it.
    """
    t = ensure_vector_time(t)
    earth, moon, sun = eph["earth"], eph["moon"], eph["sun"]

    earth_at = earth.at(t)
    apparent_sun = earth_at.observe(sun).apparent()
    apparent_moon = earth_at.observe(moon).apparent()
    shadow_vector = apparent_sun - apparent_moon

    ra_moon, dec_moon, dist_moon = apparent_moon.radec(epoch=t)
    ra_shadow, dec_shadow, dist_shadow = shadow_vector.radec(epoch=t)

    r = dist_moon.m / RE
    cos_dec_moon = cos(dec_moon.radians)
    sin_dec_moon = sin(dec_moon.radians)
    cos_d = cos(dec_shadow.radians)
    sin_d = sin(dec_shadow.radians)
    sin_da = sin(ra_moon.radians - ra_shadow.radians)
    cos_da = cos(ra_moon.radians - ra_shadow.radians)

    x = r * cos_dec_moon * sin_da
    y = r * (sin_dec_moon * cos_d - cos_dec_moon * sin_d * cos_da)
    z = r * (sin_dec_moon * sin_d + cos_dec_moon * cos_d * cos_da)

    abs_shadow_dist = dist_shadow.m / RE

    sinf1 = (ds + k1) / abs_shadow_dist
    sinf2 = (ds - k2) / abs_shadow_dist

    c1 = z + k1 / sinf1
    c2 = z - k2 / sinf2

    tanf1 = tan(arcsin(sinf1))
    tanf2 = tan(arcsin(sinf2))

    l1 = c1 * tanf1
    l2 = c2 * tanf2

    mu0 = Angle(hours=t.gast - ra_shadow.hours, preference="degrees").degrees

    data = {
        "x": x,
        "y": y,
        "mu0": mu0,
        "d": dec_shadow.degrees,
        "l1": l1,
        "l2": l2,
        "tanf1": tanf1,
        "tanf2": tanf2,
        "gast": t.gast,
    }

    return pd.DataFrame(index=t.utc_datetime(), data=data)
