"""Central-line lat/lon, central duration, and path width.

The duration/width formula (Mikhailov 1931, Explanatory Supplement
Sec. 11.99/11.101) is the same regardless of whether the element
derivatives came from numerical differentiation of a dense
raw-ephemeris time series (:func:`bessel_derivs`) or a polynomial
fit's analytic derivative (``BesselianEclipse``) -- the source
material had two copies of this formula, one per derivative source.
Here it's one function taking derivatives as an explicit argument.
"""

from __future__ import annotations

import pandas as pd
from numpy import cos, deg2rad, hypot, sin, sqrt
from scipy.signal import savgol_filter

from .ellipsoid import ksieta_to_latlon


def central_elements(B: pd.DataFrame, *, append: bool = True) -> pd.DataFrame:
    """Central-line lat/lon and on-axis shadow radii L1/L2.

    ``B`` must already carry :func:`eclipse_calc.ellipsoid.aux1_elements`'s
    columns. The central line is simply the ksi=eta=0 point of the
    fundamental plane (the shadow axis itself).
    """
    result = ksieta_to_latlon(B, B.x, B.y, append=True)
    L1 = result.l1 - result.zeta * result.tanf1
    L2 = result.l2 - result.zeta * result.tanf2

    if append:
        return result.assign(L1=L1, L2=L2)
    return pd.DataFrame(
        dict(
            L1=L1, L2=L2, ksi=result.ksi, eta=result.eta, zeta=result.zeta,
            lat=result.lat, lon=result.lon,
        )
    )


def bessel_derivs(B: pd.DataFrame) -> pd.DataFrame:
    """Numerically differentiate a dense, constant-time-step Besselian
    element series (Savitzky-Golay), in units of <quantity>/second.

    ``B``'s index must have a constant time step (e.g. from a dense
    raw ``bessels_at(t)`` call over a ``pandas.date_range``).
    """
    derivs = B.copy()
    step_seconds = B.index.to_series().diff().iloc[1].total_seconds()
    derivs.loc[:] = savgol_filter(B.values, window_length=3, polyorder=2, deriv=1, axis=0) / step_seconds
    return derivs


def central_duration_width(B: pd.DataFrame, derivs: pd.DataFrame) -> pd.DataFrame:
    """Central eclipse duration and path width, along a precomputed central line.

    ``B`` should be the output of :func:`central_elements`. ``derivs``
    must have the same columns as the elements ``B`` was derived from
    (in particular ``x``, ``y``, ``mu0``, ``d``), holding the
    time-derivative of each in units of <quantity>/second -- from
    either :func:`bessel_derivs` (numerical, dense raw-ephemeris path)
    or a polynomial fit's analytic derivative (cached path). Returns
    ``duration_s`` (seconds) and ``width`` (Earth radii, same units as L1/L2).
    """
    d_rad = deg2rad(B.d)
    d_mu0_dt_rad = deg2rad(derivs.mu0)  # deg/s -> rad/s (same scale factor as deg -> rad)
    d_d_dt_rad = deg2rad(derivs.d)

    # local derivatives of fixed momentary locations along the central line
    # (Explanatory Supplement Sec. 11.99)
    ksidot = d_mu0_dt_rad * (-B.y * sin(d_rad) + B.zeta * cos(d_rad))
    etadot = d_mu0_dt_rad * B.x * sin(d_rad) - d_d_dt_rad * B.zeta

    n = hypot(derivs.x - ksidot, derivs.y - etadot)
    duration_s = -2 * B.L2 / n  # negative L2 => total eclipse

    # Mikhailov (1931), Explanatory Supplement Sec. 11.101
    m = sqrt(B.zeta**2 + (B.ksi / n * (derivs.x - ksidot) + B.eta / n * (derivs.y - etadot)) ** 2)
    width = -2 * B.L2 / m

    return pd.DataFrame({"duration_s": duration_s, "width": width})
