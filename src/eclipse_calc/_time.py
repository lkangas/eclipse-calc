"""Scalar/vector Skyfield Time normalization.

All public functions in this package accept either a scalar or an
array-like ``skyfield.timelib.Time`` and always return a ``DataFrame``
(never raise on scalar input, unlike the research code this was ported
from).
"""

from __future__ import annotations

import numpy as np
from skyfield.timelib import Time


def ensure_vector_time(t: Time) -> Time:
    """Normalize a possibly-scalar Skyfield Time into a vector Time.

    A scalar Time (``t.shape == ()``) becomes a length-1 vector Time,
    built via ``t.ts`` (the Timescale that produced ``t``) so no
    separate ``load.timescale()`` call is needed. A vector Time is
    returned unchanged.
    """
    if t.shape == ():
        return t.ts.tt_jd(np.array([t.tt]))
    return t
