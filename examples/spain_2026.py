"""End-to-end example: 2026-08-12 total solar eclipse, Spain.

Prints contact times/duration/altitude for a few representative sites,
the central line across Spain, and (if matplotlib is installed) saves
a quick plot of the central line and umbral N/S limits.

Usage:
    python examples/spain_2026.py path/to/de440s.bsp
"""

from __future__ import annotations

import sys
from pathlib import Path

from skyfield.api import load
from skyfield.toposlib import wgs84

from eclipse_calc import BesselianEclipse, Location, load_ephemeris

SITES = [
    ("A Coruna", 43.36, -8.41, 0),
    ("Zaragoza", 41.65, -0.89, 0),
    ("Bilbao", 43.26, -2.94, 0),
    ("Valencia", 39.47, -0.38, 0),
    ("Palma de Mallorca", 39.57, 2.65, 0),
    ("Calamocha", 40.92, -1.30, 884),
]


def main() -> None:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} path/to/de440s.bsp", file=sys.stderr)
        raise SystemExit(1)

    eph = load_ephemeris(Path(sys.argv[1]))
    ts = load.timescale()
    t0 = ts.tt(2026, 8, 12, 18, 0, 0)  # T0 = 2026-08-12 18.000 TD
    eclipse = BesselianEclipse(t0, eph)

    earth, sun = eph["earth"], eph["sun"]

    print(f"{'Site':<20} {'C2':>8} {'C3':>8} {'Duration':>9} {'Sun alt':>8}")
    for name, lat, lon, elevation in SITES:
        location = Location(lat_deg=lat, lon_deg=lon, elevation_m=elevation)
        contacts = eclipse.contact_times(location)

        if not contacts.is_total_or_annular:
            print(f"{name:<20} {'--':>8} {'--':>8} {'no totality':>9}")
            continue

        duration_s = (contacts.c3.tt - contacts.c2.tt) * 86400
        t_mid = ts.tt_jd((contacts.c2.tt + contacts.c3.tt) / 2)
        topos = wgs84.latlon(lat, lon, elevation_m=elevation)
        alt, _, _ = (earth + topos).at(t_mid).observe(sun).apparent().altaz()

        print(
            f"{name:<20} {contacts.c2.utc_strftime('%H:%M:%S'):>8} "
            f"{contacts.c3.utc_strftime('%H:%M:%S'):>8} {duration_s:8.1f}s {alt.degrees:7.2f}deg"
        )

    print()
    print("Central line across Spain:")
    for hour, minute in [(18, 18), (18, 22), (18, 26), (18, 30)]:
        t = ts.utc(2026, 8, 12, hour, minute, 0)
        central = eclipse.central_line(t)
        print(
            f"  {hour:02d}:{minute:02d} UT  lat={central.lat.iloc[0]:8.4f}  "
            f"lon={central.lon.iloc[0]:9.4f}  width={central.width.iloc[0] * 6378:.0f}km"
        )

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib not installed -- skipping plot; pip install eclipse-calc[examples])")
        return

    times = ts.utc(2026, 8, 12, 18, range(16, 33), 0)
    central = eclipse.central_line(times)
    limits = eclipse.shadow_limits(times, umbra=True)

    fig, ax = plt.subplots()
    ax.plot(central.lon, central.lat, "k-", label="central line")
    ax.plot(limits.N_lon, limits.N_lat, "C0--", label="N limit")
    ax.plot(limits.S_lon, limits.S_lat, "C1--", label="S limit")
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_aspect(1.3)
    ax.legend()
    ax.set_title("2026-08-12 umbral path over Spain")

    out_path = Path(__file__).parent / "spain_2026_path.png"
    fig.savefig(out_path, dpi=150)
    print(f"\nSaved plot to {out_path}")


if __name__ == "__main__":
    main()
