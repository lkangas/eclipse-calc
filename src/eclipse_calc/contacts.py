"""Contact-time search: when an eclipse starts/ends for one observer.

Parametrized over an ``elements_at`` callable so the same search logic
serves both the raw ephemeris-direct path and the polynomial-cached
``BesselianEclipse`` path -- the research code this was ported from had
two near-identical copies of this search differing only in which
elements source they called.
"""

from __future__ import annotations

from typing import Callable, Literal

import pandas as pd
from skyfield.searchlib import find_discrete, find_minima
from skyfield.timelib import Time

from .types import ContactTimes, Location

ElementsAt = Callable[..., pd.DataFrame]
"""A callable ``(t, location=...) -> DataFrame`` returning local elements
(at minimum ``x``, ``y``, ``ksi``, ``eta``, ``L1``, ``L2``) for Time(s)
``t`` at one observer location."""


def _distance2(local_elements: pd.DataFrame) -> pd.Series:
    """Squared distance between observer and shadow axis, in the observer plane."""
    return (local_elements.x - local_elements.ksi) ** 2 + (
        local_elements.y - local_elements.eta
    ) ** 2


def eclipsed(
    local_elements: pd.DataFrame, kind: Literal["partial", "total", "annular"]
) -> pd.Series:
    """Whether the observer is inside the shadow, as a 0/1 series.

    ``kind='partial'`` tests the penumbral (L1) radius; ``'total'``/
    ``'annular'`` both test the umbral (L2) radius -- which one
    actually occurs depends on the sign of L2 (negative => total,
    positive => annular), which the caller already knows from context.
    """
    dist2 = _distance2(local_elements)
    if kind == "partial":
        radius2 = local_elements["L1"] ** 2
    elif kind in ("total", "annular"):
        radius2 = local_elements["L2"] ** 2
    else:
        raise ValueError('kind must be one of "partial", "total", "annular"')
    return (dist2 < radius2).astype(int)


def find_maximum_time(elements_at: ElementsAt, t_guess: Time, location: Location) -> Time:
    """Time of maximum eclipse for ``location``, searched within a day of ``t_guess``."""

    def distance2_at(t: Time) -> pd.Series:
        return _distance2(elements_at(t, location=location))

    distance2_at.step_days = 1 / 24
    t_start = t_guess - 12 / 24
    t_max, _ = find_minima(t_start, t_start + 1, distance2_at)
    return t_max[0]


def find_contact_times(elements_at: ElementsAt, t_max: Time, location: Location) -> ContactTimes:
    """The four contact times around ``t_max`` for ``location``.

    C2/C3 (or the whole result, if there's no eclipse at all here) may
    be ``None`` -- see :class:`eclipse_calc.types.ContactTimes`.
    """
    partial_radius_days = 5 / 24

    def partial_eclipsed_at(t: Time) -> pd.Series:
        return eclipsed(elements_at(t, location=location), kind="partial")

    partial_eclipsed_at.step_days = 1 / 24
    c1_c4, _ = find_discrete(
        t_max - partial_radius_days, t_max + partial_radius_days, partial_eclipsed_at
    )

    if len(c1_c4) != 2:
        return ContactTimes(None, None, None, None)
    c1, c4 = c1_c4

    def total_eclipsed_at(t: Time) -> pd.Series:
        return eclipsed(elements_at(t, location=location), kind="total")

    total_eclipsed_at.step_days = 1 / 3600 / 24
    c2_c3, _ = find_discrete(c1, c4, total_eclipsed_at)

    if len(c2_c3) == 2:
        c2, c3 = c2_c3
    else:
        return ContactTimes(c1, None, None, c4)

    return ContactTimes(c1, c2, c3, c4)
