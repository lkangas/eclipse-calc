"""Observer-plane local elements for one location on Earth."""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy import arctan, cos, deg2rad, sin, sqrt, tan
from skyfield.toposlib import wgs84

from .constants import RE, f
from .types import Location


def local_elements(B: pd.DataFrame, location: Location, *, append: bool = True) -> pd.DataFrame:
    """ksi/eta/zeta and the observer-plane shadow radii L1/L2 for one observer.

    ``B`` must already carry :func:`eclipse_calc.ellipsoid.aux1_elements`'s
    ``rho1`` column.
    """
    lat_deg, lon_deg, elevation_m = location

    d_rad = deg2rad(B.d)
    lat_rad = deg2rad(lat_deg)

    geocentric_lat = arctan((1 - f) ** 2 * tan(lat_rad))
    position = wgs84.latlon(lat_deg, lon_deg, elevation_m=elevation_m)

    theta_rad = deg2rad(B.mu0 + lon_deg)

    rho = sqrt((position.itrs_xyz.m**2).sum()) / RE

    ksi = rho * cos(geocentric_lat) * sin(theta_rad)
    eta = rho * sin(geocentric_lat) * cos(d_rad) - rho * cos(geocentric_lat) * sin(d_rad) * cos(
        theta_rad
    )
    zeta = rho * sin(geocentric_lat) * sin(d_rad) + rho * cos(geocentric_lat) * cos(
        d_rad
    ) * cos(theta_rad)

    eta1 = eta / B.rho1
    # See ellipsoid.ksieta_to_latlon: NaN is the expected result when the
    # observer is off the shadow ellipse, not an error.
    with np.errstate(invalid="ignore"):
        zeta1 = sqrt(1 - ksi**2 - eta1**2)

    L1 = B.l1 - zeta * B.tanf1
    L2 = B.l2 - zeta * B.tanf2

    data = dict(L1=L1, L2=L2, ksi=ksi, eta=eta, zeta=zeta, eta1=eta1, zeta1=zeta1, rho=rho)

    if append:
        return B.assign(**data)
    return pd.DataFrame(data)
