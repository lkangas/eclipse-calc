"""Physical constants used throughout the Besselian-element calculations.

Values match the IAU/Explanatory Supplement conventions used by the
research code this package was ported from.
"""

import numpy as np

RE = 6.3781370e6
"""Earth equatorial radius, in meters."""

ds = 109.123
"""Sun radius, in Earth radii."""

k1 = 0.2725076
"""Moon radius used for the penumbra, in Earth radii."""

k2 = 0.272281
"""Moon radius used for the umbra, in Earth radii."""

f = 1 / 298.25642
"""Flattening of the Earth (WGS-style ellipsoid)."""

e = np.sqrt(2 * f - f * f)
"""Ellipticity of the Earth, derived from the flattening ``f``."""
