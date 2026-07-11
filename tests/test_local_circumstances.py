"""Contact times, totality duration, and altitude vs. the review brief's site table.

Sun altitude isn't part of eclipse_calc's scope (it's plain topocentric
geometry, not Besselian-element-specific -- computed here directly via
Skyfield, matching how the app itself will do it) but is included as an
extra cross-check alongside duration, since both were independently
verified together in the review brief.
"""

import pytest
from skyfield.toposlib import wgs84

from eclipse_calc import Location

# (name, lat_deg, lon_deg, elevation_m, ref_alt_deg, ref_duration_s, alt_tol_deg, duration_tol_s)
REFERENCE_SITES = [
    ("A Coruna", 43.36, -8.41, 0, 12.0, 76, 0.5, 3),
    ("Oviedo/Gijon", 43.36, -5.85, 0, 10.0, 105, 0.5, 5),
    ("Zaragoza", 41.65, -0.89, 0, 5.9, 85, 0.5, 3),
    ("Bilbao", 43.26, -2.94, 0, 8.2, 32, 0.5, 3),
    ("Valencia", 39.47, -0.38, 0, 4.0, 58, 0.5, 3),
    ("Palma de Mallorca", 39.57, 2.65, 0, 2.4, 96, 0.5, 3),
    # Calamocha: the app's actual default site. Reference is this project's
    # own earlier computed result (not an independently published number),
    # hence the tight tolerance -- this is a regression check, not a
    # cross-source validation.
    ("Calamocha", 40.92, -1.30, 884, 5.93, 101.6, 0.2, 1),
]


@pytest.mark.parametrize(
    "name,lat,lon,elevation,ref_alt,ref_duration,alt_tol,duration_tol", REFERENCE_SITES
)
def test_site_totality_duration_and_altitude(
    eclipse, ephemeris, timescale, name, lat, lon, elevation, ref_alt, ref_duration, alt_tol, duration_tol
):
    location = Location(lat_deg=lat, lon_deg=lon, elevation_m=elevation)
    contacts = eclipse.contact_times(location)

    assert contacts.is_total_or_annular, f"{name}: expected totality, got no C2/C3"

    duration_s = (contacts.c3.tt - contacts.c2.tt) * 86400
    assert duration_s == pytest.approx(ref_duration, abs=duration_tol), name

    t_mid = timescale.tt_jd((contacts.c2.tt + contacts.c3.tt) / 2)
    topos = wgs84.latlon(lat, lon, elevation_m=elevation)
    earth, sun = ephemeris["earth"], ephemeris["sun"]
    alt, _, _ = (earth + topos).at(t_mid).observe(sun).apparent().altaz()

    assert alt.degrees == pytest.approx(ref_alt, abs=alt_tol), name


def test_bilbao_is_a_northern_edge_site(eclipse):
    """Bilbao's totality is short (~32s) -- a real sensitivity check, not
    just a duration number: a small position error would flip it to no
    totality at all, which is exactly why the review brief flags it as
    an edge site worth tracking."""
    bilbao = Location(lat_deg=43.26, lon_deg=-2.94, elevation_m=0)
    contacts = eclipse.contact_times(bilbao)
    assert contacts.is_total_or_annular
    duration_s = (contacts.c3.tt - contacts.c2.tt) * 86400
    assert 0 < duration_s < 60


def test_outside_the_path_has_no_totality(eclipse):
    """A site well outside the umbral path (e.g. central France) should
    see no C2/C3 -- exercises the partial-only / no-eclipse code path."""
    paris = Location(lat_deg=48.85, lon_deg=2.35, elevation_m=35)
    contacts = eclipse.contact_times(paris)
    assert not contacts.is_total_or_annular
