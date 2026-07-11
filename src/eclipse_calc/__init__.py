"""Besselian solar eclipse geometry, computed directly from JPL ephemeris via Skyfield."""

from .ephemeris import EphemerisSource, load_ephemeris
from .polynomial import BesselianEclipse
from .types import ContactTimes, Location

__version__ = "0.1.0"

__all__ = [
    "BesselianEclipse",
    "ContactTimes",
    "EphemerisSource",
    "Location",
    "load_ephemeris",
]
