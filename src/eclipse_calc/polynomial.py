"""Polynomial-cached Besselian eclipse elements anchored at one epoch."""

from __future__ import annotations

from typing import Literal, Optional

import numpy as np
import pandas as pd
from skyfield.timelib import Time

from ._time import ensure_vector_time
from .central_line import central_duration_width, central_elements
from .contacts import eclipsed, find_contact_times, find_maximum_time
from .ellipsoid import aux1_elements
from .elements import bessels_at
from .ephemeris import EphemerisSource, load_ephemeris
from .observer import local_elements
from .shadow import shadow_limits as _shadow_limits
from .shadow import shadow_outlines as _shadow_outlines
from .types import ContactTimes, Location


class BesselianEclipse:
    """Besselian eclipse elements, cached as a polynomial fit around ``t0``.

    Samples the ephemeris-direct :func:`eclipse_calc.elements.bessels_at`
    at ``hour_span_coarse`` points around ``t0``, fits a degree-``degree``
    polynomial per element (the same shape as a locked NASA
    Besselian-elements table, but self-generated from ephemeris), then
    serves all further queries from the cheap cached polynomial rather
    than re-querying the ephemeris each time.
    """

    def __init__(
        self,
        t0: Time,
        ephemeris: EphemerisSource,
        hour_span_coarse: np.ndarray = np.linspace(-3, 3, 5),
        degree: int = 3,
    ):
        eph = load_ephemeris(ephemeris)
        self.t0 = t0
        self.degree = degree

        t_coarse = t0.ts.tt_jd(t0.tt + hour_span_coarse / 24)
        B_coarse = bessels_at(t_coarse, eph)

        # Coefficients are stored in ascending-power order ([a0, a1, a2, ...]);
        # np.polyfit/np.polyval use descending order, hence the [::-1] flips
        # on the way in and out.
        self._coeffs = B_coarse.apply(
            lambda col: np.polyfit(hour_span_coarse, col, degree)[::-1]
        ).reset_index(drop=True)

        self._deriv_coeffs = (
            self._coeffs[::-1].apply(np.polyder)[::-1].reset_index(drop=True)
        )

    def elements_at(
        self, t: Time, location: Optional[Location] = None, derivatives: bool = True
    ) -> pd.DataFrame:
        """Evaluate the cached polynomial at Time(s) ``t``.

        Adds ``d_<col>`` derivative columns (units per second) when
        ``derivatives=True``, and observer-plane local elements
        (``L1``, ``L2``, ``ksi``, ``eta``, ``zeta``, ...) when
        ``location`` is given.
        """
        t = ensure_vector_time(t)
        t_hours = (t - self.t0) * 24
        index = t.utc_datetime()

        Bat = self._coeffs.apply(lambda col: np.polyval(col[::-1], t_hours), axis=0)
        Bat.index = index

        if derivatives:
            dBat = self._deriv_coeffs.apply(
                lambda col: np.polyval(col[::-1], t_hours), axis=0
            ).add_prefix("d_")
            dBat.index = Bat.index
            Bat = Bat.join(dBat / 3600)  # per hour -> per second

        Bat = aux1_elements(Bat, append=True)

        if location is not None:
            Bat = local_elements(Bat, location, append=True)

        return Bat

    def maximum_time(self, location: Location) -> Time:
        """Time of maximum eclipse for ``location``."""
        return find_maximum_time(self.elements_at, self.t0, location)

    def contact_times(self, location: Location) -> ContactTimes:
        """The four contact times for ``location``."""
        t_max = self.maximum_time(location)
        return find_contact_times(self.elements_at, t_max, location)

    def is_eclipsed(
        self, t: Time, location: Location, kind: Literal["partial", "total", "annular"]
    ) -> pd.Series:
        """Whether ``location`` is inside the shadow at Time(s) ``t``."""
        return eclipsed(self.elements_at(t, location=location), kind=kind)

    def central_line(self, t: Time) -> pd.DataFrame:
        """Central-line lat/lon, duration, and width at Time(s) ``t``."""
        Bat = self.elements_at(t, derivatives=True)
        result = central_elements(Bat, append=True)

        derivs = Bat[[c for c in Bat.columns if c.startswith("d_")]].rename(
            columns=lambda c: c[2:]
        )
        return result.join(central_duration_width(result, derivs))

    def shadow_outline(self, t: Time, *, umbra: bool = True, points: int = 60) -> pd.DataFrame:
        """The shadow footprint polygon (umbral or penumbral) at Time(s) ``t``."""
        Bat = self.elements_at(t, derivatives=False)
        return _shadow_outlines(Bat, points=points, umbra=umbra)

    def shadow_limits(self, t: Time, *, umbra: bool = True) -> pd.DataFrame:
        """North/south limit-line points (umbral or penumbral) at Time(s) ``t``."""
        Bat = self.elements_at(t, derivatives=True)
        return _shadow_limits(Bat, umbra=umbra)
