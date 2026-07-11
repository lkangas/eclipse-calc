"""Earth-ellipsoid auxiliary quantities.

These depend only on the shadow-axis declination (``d``) or on a
ksi/eta position, and are shared by the central-line, shadow-outline,
shadow-limit, and terminator calculations -- factored out here so
those four callers don't each carry their own copy.
"""

from __future__ import annotations

import pandas as pd
from numpy import arcsin, arctan, arctan2, cos, deg2rad, rad2deg, sin, sqrt, tan

from .constants import e, f


def aux1_elements(B: pd.DataFrame, append: bool = True) -> pd.DataFrame:
    """Earth-flattening-dependent quantities that depend only on ``d``.

    Adds ``rho1``, ``rho2`` (ellipsoid radii at the shadow-axis
    declination) and ``sind1``/``cosd1``/``sind1d2``/``cosd1d2``
    (auxiliary sine/cosine products used by the ksi/eta <-> lat/lon
    conversion below).
    """
    d_rad = deg2rad(B.d)

    sind = sin(d_rad)
    cosd = cos(d_rad)

    rho1 = sqrt(1 - e**2 * cos(d_rad) ** 2)
    rho2 = sqrt(1 - e**2 * sin(d_rad) ** 2)

    sind1 = sind / rho1
    cosd1 = sqrt(1 - e**2) * cosd / rho1

    sind1d2 = e**2 * sind * cosd / rho1 / rho2
    cosd1d2 = sqrt(1 - e**2) / rho1 / rho2

    data = dict(rho1=rho1, rho2=rho2, sind1=sind1, cosd1=cosd1, sind1d2=sind1d2, cosd1d2=cosd1d2)

    if append:
        return B.assign(**data)
    return pd.DataFrame(data)


def ksieta_to_latlon(
    B: pd.DataFrame, ksi, eta, *, append: bool = True, terminator: bool = False
) -> pd.DataFrame:
    """Convert a fundamental-plane ksi/eta position to lat/lon (+ zeta).

    ``B`` must already carry ``aux1_elements``'s columns. This is the
    one canonical ellipsoid-intersection conversion, used by the
    central line, shadow outline, shadow limits, and terminator events
    alike.

    With ``terminator=True``, ``ksi``/``eta`` are taken to already lie
    on the ellipsoid's day/night terminator (zeta = 0), skipping the
    ellipsoid-intersection solve -- used by ``terminator.py``.
    """
    rho1, rho2 = B.rho1, B.rho2
    cosd1d2, sind1d2 = B.cosd1d2, B.sind1d2
    cosd1, sind1 = B.cosd1, B.sind1

    eta1 = eta / rho1

    if terminator:
        zeta1 = 0
        zeta = 0
    else:
        zeta1 = sqrt(1 - ksi**2 - eta1**2)
        zeta = rho2 * (zeta1 * cosd1d2 - eta1 * sind1d2)

    phi1 = arcsin(eta1 * cosd1 + zeta1 * sind1)
    sintheta = ksi / cos(phi1)
    costheta = (-eta1 * sind1 + zeta1 * cosd1) / cos(phi1)
    theta = arctan2(sintheta, costheta)

    phi = arctan(tan(phi1) / (1 - f))

    theta_deg = rad2deg(theta)
    lat_deg = rad2deg(phi)
    lon_deg = theta_deg - B["mu0"]

    data = dict(
        ksi=ksi, eta=eta, eta1=eta1, zeta1=zeta1, zeta=zeta,
        theta=theta_deg, lat=lat_deg, lon=lon_deg,
    )

    if append:
        return B.assign(**data)
    return pd.DataFrame(data)
