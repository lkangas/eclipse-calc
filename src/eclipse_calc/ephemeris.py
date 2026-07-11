"""Explicit, caller-controlled ephemeris loading.

The research code this package was ported from loaded a hardcoded
``de440s.bsp`` at *import time*, relative to the current working
directory. That's fragile (depends on cwd) and does file I/O as a side
effect of ``import``. Here, loading is always an explicit call the
caller makes, with a path (or an already-loaded kernel) they choose.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

from skyfield.api import load
from skyfield.jpllib import SpiceKernel

EphemerisSource = Union[str, Path, SpiceKernel]


def load_ephemeris(source: EphemerisSource) -> SpiceKernel:
    """Resolve an ephemeris kernel from a path, or pass one through.

    ``source`` may be a path to a local ``.bsp`` file, or an
    already-loaded ``skyfield`` ``SpiceKernel`` (returned unchanged).
    This function never downloads anything and raises
    ``FileNotFoundError`` with guidance if a given path doesn't exist,
    rather than silently fetching a multi-hundred-MB file. The kernel
    must contain ``earth``, ``moon``, and ``sun`` segments -- any
    standard DE4xx planetary kernel (e.g. ``de440s.bsp``) qualifies.
    """
    if isinstance(source, SpiceKernel):
        return source

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(
            f"Ephemeris kernel not found: {path}. This package does not "
            "download kernels automatically -- point load_ephemeris() at "
            "an existing .bsp file, or fetch one yourself first, e.g.:\n"
            "    from skyfield.api import Loader\n"
            "    Loader('.').download('de440s.bsp')"
        )
    return load(str(path))
