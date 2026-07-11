# eclipse-calc

Besselian solar eclipse geometry — contact times, central line, umbral/penumbral
shadow outline, north/south limit lines, and terminator-limited (sunrise/sunset)
path edges — computed directly from JPL ephemeris via [Skyfield](https://rhodesmill.org/skyfield/),
not from a pre-published polynomial table.

Extracted and cleaned up from an earlier research project built around the
2024-04-08 North American eclipse; validated against the 2026-08-12 total
solar eclipse (Spain) to sub-kilometer/sub-second accuracy.

## Install

```bash
pip install -e .
```

## Ephemeris

This package does **not** bundle an ephemeris kernel (`.bsp` files run from
tens of MB to several GB). Point `load_ephemeris()` at one you already have,
or download one via Skyfield's own loader:

```python
from skyfield.api import Loader
path = Loader('.').download('de440s.bsp')
```

## Quick start

```python
from skyfield.api import load
from eclipse_calc import BesselianEclipse, Location, load_ephemeris

eph = load_ephemeris('de440s.bsp')
ts = load.timescale()
t0 = ts.tt(2026, 8, 12, 18)  # anywhere near the event's greatest eclipse

eclipse = BesselianEclipse(t0, eph)

zaragoza = Location(lat_deg=41.65, lon_deg=-0.89, elevation_m=0)
contacts = eclipse.contact_times(zaragoza)
print(contacts)
```

See [`docs/API.md`](docs/API.md) for the full API reference (every public
function/class, what each `DataFrame` column means, and known limitations),
and [`examples/spain_2026.py`](examples/spain_2026.py) for a complete
end-to-end example.

## License

MIT — see [LICENSE](LICENSE).
