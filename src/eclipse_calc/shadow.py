"""Umbral/penumbral shadow footprint outline, and north/south limit lines.

Both solve a tangency condition between the shadow cone and the WGS84
ellipsoid, iterating in the fundamental (ksi/eta) plane. ``shadow_limits``
finds just the two tangent points (the path edges); ``shadow_outlines``
sweeps a full position angle to trace the whole footprint polygon.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from numpy import arctan, cos, deg2rad, pi, rad2deg, sin, sqrt

from .ellipsoid import ksieta_to_latlon

logger = logging.getLogger(__name__)


def shadow_outlines(B: pd.DataFrame, *, points: int = 60, umbra: bool = True) -> pd.DataFrame:
    """The shadow footprint polygon (umbral or penumbral) at each time in ``B``.

    Returns a `DataFrame` with a ``(time, Q)`` MultiIndex, ``Q`` being
    ``points + 1`` evenly-spaced position angles around the shadow-cone
    circle in the fundamental plane; columns are the ``Q_``-prefixed
    output of :func:`eclipse_calc.ellipsoid.ksieta_to_latlon` (in
    particular ``Q_lat``/``Q_lon``). Rows where the swept point falls
    outside the Earth's disk are ``NaN`` -- expected, not an error;
    skip them when plotting.

    ``B`` must already carry :func:`eclipse_calc.ellipsoid.aux1_elements`'s
    columns.
    """
    l_col = "l2" if umbra else "l1"
    tanf_col = "tanf2" if umbra else "tanf1"

    q_values = np.linspace(0, 2 * pi, points + 1)
    index = pd.MultiIndex.from_product((B.index, q_values), names=["time", "Q"])
    result = pd.DataFrame(index=index)

    for time, row in B.iterrows():
        logger.debug("shadow_outlines: %s", time)

        for q in q_values:
            ksi = row.x - row[l_col] * sin(q)
            eta = row.y - row[l_col] * cos(q)
            eta1 = eta / row.rho1
            with np.errstate(invalid="ignore"):
                zeta1 = sqrt(1 - ksi**2 - eta1**2)
            zeta = row.rho2 * (zeta1 * row.cosd1d2 - eta1 * row.sind1d2)

            shadow_radius = row[l_col] - zeta * row[tanf_col]

            for _ in range(10):
                ksi = row.x - shadow_radius * sin(q)
                eta = row.y - shadow_radius * cos(q)
                eta1 = eta / row.rho1
                with np.errstate(invalid="ignore"):
                    zeta1 = sqrt(1 - ksi**2 - eta1**2)

                prev_zeta = zeta
                zeta = row.rho2 * (zeta1 * row.cosd1d2 - eta1 * row.sind1d2)
                if abs(prev_zeta - zeta) < 1e-8:
                    break
                shadow_radius = row[l_col] - zeta * row[tanf_col]

            latlon = ksieta_to_latlon(row.to_frame().T, ksi, eta, append=False).iloc[0].add_prefix("Q_")
            result.loc[(time, q), latlon.index] = latlon.values
            result.loc[(time, q), "Q_deg"] = rad2deg(q)

    return result.sort_index()


def _limit_tangent_coefficients(B: pd.DataFrame, *, umbra: bool):
    """Coefficients (a, b, c) of the linearized tangent-Q condition used
    by :func:`shadow_limits` (Explanatory Supplement Sec. 11.77), for
    either the umbral (``l2``/``tanf2``) or penumbral (``l1``/``tanf1``)
    shadow cone.

    Renamed and scoped to this module (was a general-purpose
    ``_aux2_elements`` in the source material that always computed
    both umbral and penumbral coefficients even though only one set is
    ever used per call).

    Requires ``B`` to carry analytic derivative columns (``d_x``,
    ``d_y``, ``d_mu0``, ``d_d``, ``d_l1``, ``d_l2``).
    """
    l_col = "l2" if umbra else "l1"
    tanf_col = "tanf2" if umbra else "tanf1"
    dl_col = "d_l2" if umbra else "d_l1"

    d_rad = deg2rad(B.d)
    d_mu0_dt_rad = deg2rad(B.d_mu0)
    d_d_dt_rad = deg2rad(B.d_d)

    a = -B[dl_col] - d_mu0_dt_rad * B.x * cos(d_rad) * B[tanf_col] + B.y * d_d_dt_rad * B[tanf_col]
    b = -B.d_y + d_mu0_dt_rad * B.x * sin(d_rad) + B[l_col] * d_d_dt_rad * B[tanf_col]
    c = B.d_x + d_mu0_dt_rad * B.y * sin(d_rad) + B[l_col] * d_mu0_dt_rad * B[tanf_col] * cos(d_rad)

    return a, b, c


def shadow_limits(
    B: pd.DataFrame, *, umbra: bool = True, maxiter: int = 10, zeta_tol: float = 1e-8
) -> pd.DataFrame:
    """North and south limit-line points (umbral or penumbral) at each time in ``B``.

    Returns a `DataFrame` indexed like ``B``, with ``N_``/``S_``-prefixed
    columns from :func:`eclipse_calc.ellipsoid.ksieta_to_latlon`. A
    prefix is simply absent for a given time if that tangent point's
    iteration didn't converge (see the ``umbra=False`` note below) --
    rather than writing out a value that isn't actually on the shadow
    ellipse.

    ``B`` must carry :func:`eclipse_calc.ellipsoid.aux1_elements`'s
    columns and analytic derivatives (``d_x``, ``d_y``, ``d_mu0``,
    ``d_d``, ``d_l1``, ``d_l2``).

    ``umbra=True`` (the umbral/totality limits) is well-tested: it
    matches an independent reference table for the 2026-08-12 event to
    ~200-900m. ``umbra=False`` (penumbral limits) is NOT independently
    validated -- the source material never actually exercised this
    path (it was present but commented out) -- and its initial guess
    (assuming the two tangent points sit ~180 degrees apart in the
    fundamental plane, which holds for the umbral cone) can converge
    to a self-consistent but unphysical fixed point for the much wider
    penumbral cone. Use with caution; a better initial-guess strategy
    for the penumbral case is a known follow-up, not attempted here.
    """
    l_col = "l2" if umbra else "l1"
    tanf_col = "tanf2" if umbra else "tanf1"
    a, b_coef, c = _limit_tangent_coefficients(B, umbra=umbra)

    result = pd.DataFrame(index=B.index)

    for time, row in B.iterrows():
        logger.debug("shadow_limits: %s", time)

        ra, rb, rc = a.loc[time], b_coef.loc[time], c.loc[time]
        d_rad = deg2rad(row.d)
        d_mu0_dt_rad = deg2rad(row.d_mu0)
        d_d_dt_rad = deg2rad(row.d_d)
        sec2f = 1 + row[tanf_col] ** 2

        L = row[l_col]  # initial guess, zeta = 0
        q1 = arctan(rb / rc)  # unnecessary initial guess, given the quick convergence

        for offset in (0, pi):
            q = q1 + offset

            ksi = row.x - L * sin(q)
            eta1 = (row.y - L * cos(q)) / row.rho1
            with np.errstate(invalid="ignore"):
                zeta1 = sqrt(1 - ksi**2 - eta1**2)
            zeta = row.rho2 * (zeta1 * row.cosd1d2 - eta1 * row.sind1d2)

            converged = False
            for _ in range(maxiter):
                tan_q = (rb - d_d_dt_rad * zeta * sec2f - ra / cos(q)) / (
                    rc - d_mu0_dt_rad * zeta * sec2f * cos(d_rad)
                )
                q = arctan(tan_q) + offset
                L = row[l_col] - zeta * row[tanf_col]

                ksi = row.x - L * sin(q)
                eta = row.y - L * cos(q)
                eta1 = eta / row.rho1
                with np.errstate(invalid="ignore"):
                    zeta1 = sqrt(1 - ksi**2 - eta1**2)

                prev_zeta = zeta
                zeta = row.rho2 * (zeta1 * row.cosd1d2 - eta1 * row.sind1d2)
                if abs(prev_zeta - zeta) < zeta_tol:
                    converged = True
                    break

            if not converged or not np.isfinite(zeta1):
                logger.warning(
                    "shadow_limits: no convergence at %s (umbra=%s, offset=%.2f) -- "
                    "dropping this tangent point rather than reporting an invalid one",
                    time, umbra, offset,
                )
                continue

            prefix = "S_" if L * cos(q) > 0 else "N_"
            latlon = ksieta_to_latlon(row.to_frame().T, ksi, eta, append=False).iloc[0].add_prefix(prefix)
            result.loc[time, latlon.index] = latlon.values

    return result
