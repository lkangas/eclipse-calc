"""Terminator-limited (sunrise/sunset) path edges.

Where the shadow cone crosses the Earth's day/night terminator, and
the whole-path contact times (P1-P4 penumbral, U1-U4 umbral, CE1-CE2
central) -- relevant when an eclipse's path is itself sunset/sunrise
-limited, as the 2026-08-12 Spain event's is.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional, Tuple

import numpy as np
import pandas as pd
from numpy import arctan2, cos, hypot, pi, sign, sin
from scipy.optimize import brentq, minimize_scalar
from skyfield.searchlib import find_discrete
from skyfield.timelib import Time

from .contacts import ElementsAt
from .ellipsoid import ksieta_to_latlon

logger = logging.getLogger(__name__)


def solve_gamma(B: pd.DataFrame, *, umbra: bool = False) -> pd.DataFrame:
    """Position angle(s) where the shadow-cone circle crosses the Earth's
    day/night terminator, at each time in ``B``.

    Returns ``Y1``/``Y2`` (the two crossing angles, radians) and their
    corresponding ``rho_Y1``/``rho_Y2`` (distance from the fundamental
    plane's origin). A time with no row in the result means the shadow
    cone doesn't reach the terminator at all (either it misses the
    Earth, or is entirely within the sunlit/dark side).
    """
    l_col = "l2" if umbra else "l1"

    def f(y: float, row: pd.Series) -> float:
        # Distance from a terminator point (ksi, eta) = (sin y, cos y * rho1)
        # to the shadow-cone edge; negative where the cone covers the
        # terminator, so a root of f is a crossing point.
        ksi = sin(y)
        eta = cos(y) * row.rho1
        return hypot(row.x - ksi, row.y - eta) - abs(row[l_col])

    result = pd.DataFrame(index=B.index)
    for time, row in B.iterrows():
        closest = minimize_scalar(f, bracket=(-1e-6, 1e-6), args=(row,))
        if closest.fun > 0:
            continue  # cone doesn't reach the terminator at this instant

        middle_y = closest.x
        y1 = brentq(f, middle_y - pi, middle_y, args=(row,))
        y2 = brentq(f, middle_y, middle_y + pi, args=(row,))

        y1p = arctan2(sin(y1), row.rho1 * cos(y1))
        y2p = arctan2(sin(y2), row.rho1 * cos(y2))

        result.loc[time, "Y1"] = y1p
        result.loc[time, "Y2"] = y2p
        result.loc[time, "rho_Y1"] = hypot(sin(y1), row.rho1 * cos(y1))
        result.loc[time, "rho_Y2"] = hypot(sin(y2), row.rho1 * cos(y2))

    return result


def rise_set_curves(B: pd.DataFrame, *, umbra: bool = False, append: bool = True) -> pd.DataFrame:
    """The two sunrise/sunset-limited path-edge curves, as lat/lon.

    ``B`` must already carry :func:`eclipse_calc.ellipsoid.aux1_elements`'s
    columns.
    """
    gamma = solve_gamma(B, umbra=umbra)

    latlon1 = ksieta_to_latlon(B, sin(gamma.Y1), cos(gamma.Y1), terminator=True, append=False)
    latlon1["Q"] = arctan2(B.x - latlon1.ksi, B.y - latlon1.eta)

    latlon2 = ksieta_to_latlon(B, sin(gamma.Y2), cos(gamma.Y2), terminator=True, append=False)
    latlon2["Q"] = arctan2(B.x - latlon2.ksi, B.y - latlon2.eta)

    curves = latlon1.join(latlon2, lsuffix="1", rsuffix="2")
    if append:
        return B.join(curves)
    return curves


ShadowKind = Literal["umbra", "penumbra", "center"]


def shadow_contact_times(
    elements_at: ElementsAt, t0: Time, shadow: ShadowKind, radius_days: float = 4 / 24
) -> Tuple[Optional[Time], ...]:
    """Whole-path contact times for the shadow's outer/inner edge, searched
    within ``radius_days`` of ``t0``.

    For ``shadow='center'``, returns ``(t1, t2)`` -- when the shadow
    axis itself first/last touches the Earth. For ``'umbra'``/
    ``'penumbra'``, returns ``(t1, t2, t3, t4)`` -- when the outer edge
    of that shadow first/last touches the Earth (t1/t4), and when the
    inner edge does (t2/t3, i.e. when the *whole* shadow is/stops being
    on the Earth). Any entry may be ``None`` if that crossing doesn't
    occur within ``radius_days``.
    """

    def edge_sign(t: Time, *, outer: bool) -> pd.Series:
        b = elements_at(t, derivatives=False)
        shadow_center_angle = arctan2(b.x, b.y)
        earth_edge_distance = hypot(sin(shadow_center_angle), b.rho1 * cos(shadow_center_angle))

        if shadow == "umbra":
            radius = np.abs(b.l2)
        elif shadow == "penumbra":
            radius = b.l1
        elif shadow == "center":
            radius = 0
        else:
            raise ValueError('shadow must be one of "umbra", "penumbra", "center"')

        shadow_center_distance = hypot(b.x, b.y)
        diff = shadow_center_distance - (radius if outer else -radius) - earth_edge_distance
        return sign(diff)

    def outer_sign(t: Time) -> pd.Series:
        return edge_sign(t, outer=True)

    def inner_sign(t: Time) -> pd.Series:
        return edge_sign(t, outer=False)

    outer_sign.step_days = 0.1 / 24
    inner_sign.step_days = 0.1 / 24

    t_start, t_end = t0 - radius_days, t0 + radius_days

    if shadow == "center":
        t_1_2, _ = find_discrete(t_start, t_end, outer_sign)
        if len(t_1_2) == 2:
            return t_1_2[0], t_1_2[1]
        return None, None

    t_1_4, _ = find_discrete(t_start, t_end, outer_sign)
    t_2_3, _ = find_discrete(t_start, t_end, inner_sign)

    t1, t4 = t_1_4 if len(t_1_4) == 2 else (None, None)
    t2, t3 = t_2_3 if len(t_2_3) == 2 else (None, None)
    return t1, t2, t3, t4


_TERMINATOR_EVENT_NAMES = ["P1", "P2", "P3", "P4", "U1", "U2", "U3", "U4", "CE1", "CE2"]


def terminator_events(elements_at: ElementsAt, t0: Time) -> pd.DataFrame:
    """The whole-path contact events (penumbral P1-P4, umbral U1-U4,
    central CE1-CE2) that occur, as a `DataFrame` indexed by event name
    with ``time``, ``lat``, ``lon`` columns.

    An event is simply absent from the result if it doesn't occur
    within the default 4-day search radius -- this is expected, not an
    error: P2/P3 (the penumbral shadow being *entirely* on the Earth's
    disk at once) commonly don't exist for a large-magnitude eclipse
    like this one, whose penumbra can exceed Earth's diameter for much
    of the event. (The source material's original implementation
    crashed with an opaque ``AttributeError`` on ``None`` in this
    case, rather than handling it.)
    """
    p1, p2, p3, p4 = shadow_contact_times(elements_at, t0, "penumbra")
    u1, u2, u3, u4 = shadow_contact_times(elements_at, t0, "umbra")
    ce1, ce2 = shadow_contact_times(elements_at, t0, "center")

    all_events = [p1, p2, p3, p4, u1, u2, u3, u4, ce1, ce2]
    names, events = [], []
    for name, event in zip(_TERMINATOR_EVENT_NAMES, all_events):
        if event is None:
            logger.info("terminator_events: %s does not occur within the search radius", name)
            continue
        names.append(name)
        events.append(event)

    t = t0.ts.tt_jd([event.tt for event in events])
    b = elements_at(t, derivatives=False)

    shadow_center_angle = arctan2(b.x, b.y)
    earth_edge_distance = hypot(sin(shadow_center_angle), b.rho1 * cos(shadow_center_angle))
    ksi = earth_edge_distance * sin(shadow_center_angle)
    eta = earth_edge_distance * cos(shadow_center_angle)

    latlon = ksieta_to_latlon(b, ksi, eta, append=False, terminator=True)

    result = pd.DataFrame(index=latlon.index.rename("time"))
    result["event"] = names
    return result.join(latlon).sort_index().reset_index().set_index("event")
