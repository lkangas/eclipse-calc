"""Small shared value types."""

from __future__ import annotations

from typing import NamedTuple, Optional

from skyfield.timelib import Time


class Location(NamedTuple):
    """An observer's position on the Earth's surface."""

    lat_deg: float
    lon_deg: float
    elevation_m: float


class ContactTimes(NamedTuple):
    """The four eclipse contact times for one observer.

    ``c2``/``c3`` are ``None`` when the observer only sees a partial
    eclipse (outside the umbral path); all four are ``None`` when the
    observer sees no eclipse at all.
    """

    c1: Optional[Time]
    c2: Optional[Time]
    c3: Optional[Time]
    c4: Optional[Time]

    @property
    def is_total_or_annular(self) -> bool:
        return self.c2 is not None and self.c3 is not None
