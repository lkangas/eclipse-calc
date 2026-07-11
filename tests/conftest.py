"""Shared fixtures for the 2026-08-12 total solar eclipse (Spain) test event.

Reference numbers throughout the test suite come from the eclipse
dashboard app's PYTHON_REVIEW_BRIEF.md Sec. 0 (cross-checked against
NASA GSFC SEdata and ytliu.epizy.com/DE441 independently), and from
the earlier review session's own spot-checks recorded in
PYTHON_REVIEW_SUMMARY.md / PYTHON_REVIEW_FINDINGS.md.
"""

import os
from pathlib import Path

import pytest
from skyfield.api import load

from eclipse_calc import load_ephemeris
from eclipse_calc.polynomial import BesselianEclipse

DEFAULT_EPHEMERIS = Path(r"C:\Users\lauri.kangas\OneDrive\python\eclipse\de440s.bsp")


@pytest.fixture(scope="session")
def ephemeris():
    """The DE440s ephemeris kernel, from ECLIPSE_CALC_TEST_EPHEMERIS or the
    known-local copy in the python/eclipse research sandbox.

    Deliberately doesn't default to downloading one: this network has
    an FTP block and Python-specific TLS trust-store gaps that make
    automatic downloads unreliable here (see the eclipse-calc project
    history) -- point the env var at a kernel you already have.
    """
    path = Path(os.environ.get("ECLIPSE_CALC_TEST_EPHEMERIS", DEFAULT_EPHEMERIS))
    if not path.exists():
        pytest.skip(
            f"No ephemeris kernel at {path}. Set ECLIPSE_CALC_TEST_EPHEMERIS to a "
            "local .bsp file to run tests that need real ephemeris data."
        )
    return load_ephemeris(path)


@pytest.fixture(scope="session")
def timescale():
    return load.timescale()


@pytest.fixture(scope="session")
def t0(timescale):
    """T0 = 2026-08-12 18.000 TD, matching both reference tables' element epoch."""
    return timescale.tt(2026, 8, 12, 18, 0, 0)


@pytest.fixture(scope="session")
def eclipse(t0, ephemeris):
    return BesselianEclipse(t0, ephemeris)
