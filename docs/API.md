# eclipse-calc API reference

Besselian solar eclipse geometry, computed directly from JPL ephemeris via
[Skyfield](https://rhodesmill.org/skyfield/) — not from a pre-published
polynomial table. See the [README](../README.md) for installation and a
quick-start example; this document is the complete API reference.

## Contents

- [Architecture](#architecture)
- [Quick reference](#quick-reference)
- [`eclipse_calc.types`](#eclipse_calctypes) — `Location`, `ContactTimes`
- [`eclipse_calc.ephemeris`](#eclipse_calcephemeris) — `load_ephemeris`
- [`eclipse_calc.polynomial`](#eclipse_calcpolynomial) — `BesselianEclipse` (the main entry point)
- [`eclipse_calc.elements`](#eclipse_calcelements) — `bessels_at`
- [`eclipse_calc.ellipsoid`](#eclipse_calcellipsoid) — `aux1_elements`, `ksieta_to_latlon`
- [`eclipse_calc.observer`](#eclipse_calcobserver) — `local_elements`
- [`eclipse_calc.contacts`](#eclipse_calccontacts) — `eclipsed`, `find_maximum_time`, `find_contact_times`
- [`eclipse_calc.central_line`](#eclipse_calccentral_line) — `central_elements`, `bessel_derivs`, `central_duration_width`
- [`eclipse_calc.shadow`](#eclipse_calcshadow) — `shadow_outlines`, `shadow_limits`
- [`eclipse_calc.terminator`](#eclipse_calcterminator) — `solve_gamma`, `rise_set_curves`, `shadow_contact_times`, `terminator_events`
- [DataFrame column reference](#dataframe-column-reference)
- [Known limitations](#known-limitations)

---

## Architecture

The package has two layers:

- **Layer 1** (`elements`, `ellipsoid`, `observer`, `contacts`, `central_line`,
  `shadow`, `terminator`) is stateless functions operating on a Besselian
  elements `pandas.DataFrame`. Nothing here caches anything — every call
  re-evaluates from whatever `DataFrame` you pass in. Use this layer directly
  if you want a single, uncached, ephemeris-direct evaluation (e.g. a
  one-off high-precision check).
- **Layer 2** (`polynomial.BesselianEclipse`) is a stateful facade anchored
  at one epoch `t0`: it samples Layer 1's `bessels_at` at a handful of
  points around `t0`, fits a degree-3 polynomial per element, and serves
  every further query from that cheap cached polynomial rather than
  re-querying the ephemeris each time. **This is what almost everyone
  should use** — it's dramatically faster for the repeated evaluations
  that contact-time search, shadow-outline sweeps, and interactive UIs all
  need, and it's accurate to ~1e-8 relative to the direct evaluation at
  the anchor time.

Most `DataFrame`-returning functions accept a scalar or array-like Skyfield
`Time` and always return a `DataFrame` (one row for scalar input) indexed by
UTC datetime.

## Quick reference

| Want to... | Use |
|---|---|
| Load an ephemeris kernel | `load_ephemeris(path)` |
| Get contact times (C1-C4) for a site | `BesselianEclipse.contact_times(location)` |
| Get time of maximum eclipse for a site | `BesselianEclipse.maximum_time(location)` |
| Check if a site is in shadow at time *t* | `BesselianEclipse.is_eclipsed(t, location, kind)` |
| Get the central line (+ duration/width) | `BesselianEclipse.central_line(t)` |
| Get the umbral/penumbral footprint polygon | `BesselianEclipse.shadow_outline(t, umbra=...)` |
| Get N/S limit-line points | `BesselianEclipse.shadow_limits(t, umbra=...)` |
| Get whole-path start/end times | `BesselianEclipse.terminator_events()` |
| Do a one-off uncached evaluation | `eclipse_calc.elements.bessels_at(t, eph)` |

---

## `eclipse_calc.types`

### `Location`

```python
class Location(NamedTuple):
    lat_deg: float
    lon_deg: float
    elevation_m: float
```

An observer's position on the Earth's surface. A plain `(lat, lon, elev)`
tuple works anywhere a `Location` is expected (it's a `NamedTuple`).

### `ContactTimes`

```python
class ContactTimes(NamedTuple):
    c1: Optional[Time]
    c2: Optional[Time]
    c3: Optional[Time]
    c4: Optional[Time]

    @property
    def is_total_or_annular(self) -> bool
```

The four eclipse contact times for one observer:

| Field | Meaning |
|---|---|
| `c1` | First contact — partial eclipse begins |
| `c2` | Second contact — totality/annularity begins |
| `c3` | Third contact — totality/annularity ends |
| `c4` | Fourth contact — partial eclipse ends |

`c2`/`c3` are `None` when the observer only sees a partial eclipse (outside
the umbral path). All four are `None` when the observer sees no eclipse at
all. `is_total_or_annular` is `True` iff both `c2` and `c3` are set.

---

## `eclipse_calc.ephemeris`

### `load_ephemeris(source)`

```python
def load_ephemeris(source: str | Path | SpiceKernel) -> SpiceKernel
```

Resolves an ephemeris kernel from a path, or passes an already-loaded
Skyfield `SpiceKernel` through unchanged.

- **`source`** — path to a local `.bsp` file, or a `SpiceKernel`.
- **Returns** — the loaded `SpiceKernel`.
- **Raises** `FileNotFoundError` (with a suggested fix) if the path doesn't exist.

**Never downloads anything.** `.bsp` kernels run from tens of MB to several
GB, so this package treats them as an explicit, caller-supplied dependency
rather than fetching one automatically. If you don't have one:

```python
from skyfield.api import Loader
path = Loader('.').download('de440s.bsp')
```

`EphemerisSource` (`str | Path | SpiceKernel`) is the type alias used
throughout the package for "something `load_ephemeris` accepts."

---

## `eclipse_calc.polynomial`

### `BesselianEclipse` — the main entry point

```python
class BesselianEclipse:
    def __init__(
        self,
        t0: Time,
        ephemeris: EphemerisSource,
        hour_span_coarse: np.ndarray = np.linspace(-3, 3, 5),
        degree: int = 3,
    )
```

Besselian eclipse elements, cached as a polynomial fit around `t0`.

- **`t0`** — the anchor epoch (a Skyfield `Time`, e.g.
  `ts.tt(2026, 8, 12, 18)`). Pick something near the event's greatest
  eclipse; all further queries are evaluated relative to this.
- **`ephemeris`** — anything `load_ephemeris` accepts.
- **`hour_span_coarse`** — hour offsets from `t0` to sample the ephemeris
  at when fitting the polynomial. Default `±3` hours across 5 points.
  Evaluating far outside this range is a polynomial *extrapolation* and
  accuracy degrades — widen this if you need to query, e.g.,
  `terminator_events()`'s whole-path times and they fall near the edge of
  the default range.
- **`degree`** — polynomial degree per element. Default 3, matching the
  standard NASA-style Besselian element table shape.

At construction, this internally calls `elements.bessels_at` at the 5
(by default) sample points and fits everything — no further ephemeris
access happens after `__init__` returns.

#### `elements_at(t, location=None, derivatives=True)`

```python
def elements_at(self, t: Time, location: Location | None = None, derivatives: bool = True) -> pd.DataFrame
```

Evaluate the cached polynomial at Time(s) `t`. This is the method
everything else in the class is built on; call it directly if you want
raw elements without going through a higher-level method.

- **`t`** — scalar or array-like Time.
- **`location`** — if given, appends observer-plane local elements
  (`L1`, `L2`, `ksi`, `eta`, `zeta`, ...) via `observer.local_elements`.
- **`derivatives`** — if `True` (default), appends `d_<col>` columns
  (each element's time-derivative, units `<quantity>/second`).
- **Returns** — a `DataFrame`; see the [column reference](#dataframe-column-reference).

#### `maximum_time(location) -> Time`

Time of maximum eclipse for `location`.

#### `contact_times(location) -> ContactTimes`

The four contact times for `location`. Internally finds `maximum_time`
first, then searches around it.

#### `is_eclipsed(t, location, kind) -> pd.Series`

Whether `location` is inside the shadow at Time(s) `t`.
`kind` is `"partial"`, `"total"`, or `"annular"`.

#### `central_line(t) -> pd.DataFrame`

Central-line lat/lon, duration, and width at Time(s) `t`. See
[`central_line`](#eclipse_calccentral_line) for the underlying formula.

#### `shadow_outline(t, *, umbra=True, points=60) -> pd.DataFrame`

The shadow footprint polygon (umbral or penumbral) at Time(s) `t`. See
[`shadow.shadow_outlines`](#eclipse_calcshadow).

#### `shadow_limits(t, *, umbra=True) -> pd.DataFrame`

North/south limit-line points (umbral or penumbral) at Time(s) `t`. See
[`shadow.shadow_limits`](#eclipse_calcshadow) — **read the `umbra=False`
caveat there before relying on penumbral limits.**

#### `shadow_contact_times(shadow, radius_days=4/24)`

Whole-path contact times for the shadow's outer/inner edge. See
[`terminator.shadow_contact_times`](#eclipse_calcterminator).

#### `terminator_events() -> pd.DataFrame`

The whole-path contact events (penumbral, umbral, central) that occur. See
[`terminator.terminator_events`](#eclipse_calcterminator).

---

## `eclipse_calc.elements`

### `bessels_at(t, eph)`

```python
def bessels_at(t: Time, eph: SpiceKernel) -> pd.DataFrame
```

General Besselian elements at Time(s) `t`, computed **directly from
ephemeris** (not a polynomial fit — this is what `BesselianEclipse` samples
internally, but you can call it yourself for an uncached, single-instant
evaluation).

- **`t`** — scalar or array-like Time.
- **`eph`** — a loaded `SpiceKernel`.
- **Returns** — a `DataFrame` with columns `x`, `y`, `mu0`, `d`, `l1`, `l2`,
  `tanf1`, `tanf2`, `gast` (see the [column reference](#dataframe-column-reference)).

> **Note on `mu0`:** this differs from published reference tables (e.g.
> NASA GSFC SEdata) by an amount proportional to the difference between
> Skyfield's internal ΔT and whatever ΔT those tables used (roughly 0.3°
> for the 2026-08-12 event — a ~69s ΔT difference at Earth's 15°/hour
> rotation rate). `x`/`y`/`d`/`l1`/`l2` are far less ΔT-sensitive (they
> track the Sun/Moon's slow orbital motion, not Earth's fast rotation) and
> agree with reference tables to 5-6 significant figures. This is a real,
> understood consequence of using Skyfield's own ΔT model rather than a
> fixed published constant — not a bug — and downstream results (which use
> `mu0` consistently alongside the other elements) have been validated
> against reference data to sub-km/sub-second accuracy despite it.

---

## `eclipse_calc.ellipsoid`

Earth-ellipsoid auxiliary quantities shared by the central-line,
shadow-outline, shadow-limit, and terminator calculations.

### `aux1_elements(B, append=True)`

```python
def aux1_elements(B: pd.DataFrame, append: bool = True) -> pd.DataFrame
```

Earth-flattening-dependent quantities that depend only on `d` (the shadow
axis declination). Adds `rho1`, `rho2`, `sind1`, `cosd1`, `sind1d2`,
`cosd1d2`. Every other function in the package that needs a lat/lon
conversion requires these columns to already be present — `elements_at`
always calls this for you.

- **`append`** — if `True` (default), returns `B` with the new columns
  added; if `False`, returns just the new columns as their own `DataFrame`.

### `ksieta_to_latlon(B, ksi, eta, *, append=True, terminator=False)`

```python
def ksieta_to_latlon(B: pd.DataFrame, ksi, eta, *, append: bool = True, terminator: bool = False) -> pd.DataFrame
```

Converts a fundamental-plane `(ksi, eta)` position to lat/lon (+ `zeta`).
This is the **one canonical ellipsoid-intersection conversion** used by
the central line, shadow outline, shadow limits, and terminator events
alike — `B` must already carry `aux1_elements`'s columns.

- **`ksi`, `eta`** — position in the fundamental plane (Earth radii). Can
  be scalars or Series aligned with `B`'s index.
- **`terminator`** — if `True`, `ksi`/`eta` are taken to already lie on the
  ellipsoid's day/night terminator (`zeta = 0`), skipping the
  ellipsoid-intersection solve — used internally by `terminator.py`.
- **Returns** — adds/returns `ksi`, `eta`, `eta1`, `zeta1`, `zeta`,
  `theta`, `lat`, `lon`. **Longitude is wrapped to `[-180, 180)`** (since
  the underlying `theta - mu0` difference isn't bounded to one revolution)
  — this matters for anything evaluated far from the polynomial's anchor
  time, which is exactly what whole-path terminator events do.

---

## `eclipse_calc.observer`

### `local_elements(B, location, *, append=True)`

```python
def local_elements(B: pd.DataFrame, location: Location, *, append: bool = True) -> pd.DataFrame
```

`ksi`/`eta`/`zeta` and the observer-plane shadow radii `L1`/`L2` for one
observer. `B` must already carry `aux1_elements`'s `rho1` column.

- **`location`** — the observer.
- **Returns** — adds/returns `L1`, `L2`, `ksi`, `eta`, `zeta`, `eta1`,
  `zeta1`, `rho` (see the [column reference](#dataframe-column-reference)
  for what each means).

You'll typically get this via `BesselianEclipse.elements_at(t, location=...)`
rather than calling it directly.

---

## `eclipse_calc.contacts`

Contact-time search: when an eclipse starts/ends for one observer.
Parametrized over an `elements_at` callable (matching
`BesselianEclipse.elements_at`'s signature) so the same search logic
serves both the cached-polynomial path and a raw, uncached
`elements.bessels_at`-based path.

`ElementsAt = Callable[..., pd.DataFrame]` — a callable `(t, location=...) -> DataFrame`.

### `eclipsed(local_elements, kind)`

```python
def eclipsed(local_elements: pd.DataFrame, kind: Literal["partial", "total", "annular"]) -> pd.Series
```

Whether the observer is inside the shadow, as a 0/1 series. `local_elements`
must include observer-plane columns (i.e. came from a call with `location`
set). `kind='partial'` tests the penumbral (`L1`) radius; `'total'`/
`'annular'` both test the umbral (`L2`) radius.

### `find_maximum_time(elements_at, t_guess, location)`

```python
def find_maximum_time(elements_at: ElementsAt, t_guess: Time, location: Location) -> Time
```

Time of maximum eclipse for `location`, searched within a day of `t_guess`.

### `find_contact_times(elements_at, t_max, location)`

```python
def find_contact_times(elements_at: ElementsAt, t_max: Time, location: Location) -> ContactTimes
```

The four contact times around `t_max` for `location`. `t_max` should come
from `find_maximum_time` (or `BesselianEclipse.maximum_time`).

---

## `eclipse_calc.central_line`

Central-line lat/lon, central duration, and path width (Mikhailov 1931,
*Explanatory Supplement* §11.99/11.101).

### `central_elements(B, *, append=True)`

```python
def central_elements(B: pd.DataFrame, *, append: bool = True) -> pd.DataFrame
```

Central-line lat/lon and on-axis shadow radii `L1`/`L2` — the central line
is simply the `ksi = eta = 0` point of the fundamental plane (the shadow
axis itself). `B` must already carry `aux1_elements`'s columns.

### `bessel_derivs(B)`

```python
def bessel_derivs(B: pd.DataFrame) -> pd.DataFrame
```

Numerically differentiates a dense, constant-time-step Besselian element
series (Savitzky-Golay filter), in units of `<quantity>/second`. `B`'s
index must have a constant time step. You only need this for the
uncached/raw-ephemeris path — `BesselianEclipse` uses its polynomial's
analytic derivative instead (see `polynomial.elements_at`'s `derivatives=`).

### `central_duration_width(B, derivs)`

```python
def central_duration_width(B: pd.DataFrame, derivs: pd.DataFrame) -> pd.DataFrame
```

Central eclipse duration and path width, along a precomputed central line.

- **`B`** — output of `central_elements`.
- **`derivs`** — same columns as the elements `B` was derived from (in
  particular `x`, `y`, `mu0`, `d`), holding each one's time-derivative in
  `<quantity>/second`. Can come from `bessel_derivs` (numerical) or a
  polynomial fit's analytic derivative — the formula is identical either
  way.
- **Returns** — `duration_s` (seconds) and `width` (Earth radii, same
  units as `L1`/`L2` — multiply by ~6378 for km).

---

## `eclipse_calc.shadow`

Umbral/penumbral shadow footprint outline, and north/south limit lines.
Both solve a tangency condition between the shadow cone and the WGS84
ellipsoid, iterating in the fundamental (ksi/eta) plane.

### `shadow_outlines(B, *, points=60, umbra=True)`

```python
def shadow_outlines(B: pd.DataFrame, *, points: int = 60, umbra: bool = True) -> pd.DataFrame
```

The shadow footprint polygon at each time in `B`. `B` must already carry
`aux1_elements`'s columns.

- **`points`** — number of position angles to sweep (the returned polygon
  has `points + 1` points, closing back on itself).
- **`umbra`** — `True` for the umbral (total/annular) shadow, `False` for
  the penumbral (partial) shadow.
- **Returns** — a `DataFrame` with a `(time, Q)` `MultiIndex` (`Q` in
  radians) and `Q_`-prefixed columns (`Q_lat`, `Q_lon`, etc. — see the
  [column reference](#dataframe-column-reference)). **Rows where the swept
  point falls outside the Earth's disk are `NaN`** — expected, not an
  error; skip them when plotting (most plotting libraries do this
  automatically for line plots).

### `shadow_limits(B, *, umbra=True, maxiter=10, zeta_tol=1e-8)`

```python
def shadow_limits(B: pd.DataFrame, *, umbra: bool = True, maxiter: int = 10, zeta_tol: float = 1e-8) -> pd.DataFrame
```

North and south limit-line points at each time in `B`. `B` must carry
`aux1_elements`'s columns **and** analytic derivative columns (`d_x`,
`d_y`, `d_mu0`, `d_d`, `d_l1`, `d_l2` — i.e. call with `derivatives=True`).

- **Returns** — a `DataFrame` indexed like `B`, with `N_`/`S_`-prefixed
  columns. **A prefix is simply absent for a given time** if that tangent
  point's iteration didn't converge, rather than reporting a value that
  isn't actually on the shadow ellipse (a warning is logged when this
  happens).

> **`umbra=True` is well-tested**: matches an independent reference table
> for the 2026-08-12 event to ~200-900m. **`umbra=False` (penumbral) is
> NOT independently validated** — its initial guess assumes the two
> tangent points sit ~180° apart in the fundamental plane, which holds for
> the umbral cone but can converge to a self-consistent-but-unphysical
> fixed point for the much wider penumbral cone. See [Known
> limitations](#known-limitations).

---

## `eclipse_calc.terminator`

Where the shadow cone crosses the Earth's day/night terminator, and the
whole-path contact times — relevant when an eclipse's path is itself
sunset/sunrise-limited, as the 2026-08-12 Spain event's is.

### `solve_gamma(B, *, umbra=False)`

```python
def solve_gamma(B: pd.DataFrame, *, umbra: bool = False) -> pd.DataFrame
```

Position angle(s) where the shadow-cone circle crosses the Earth's
day/night terminator, at each time in `B`. Returns `Y1`/`Y2` (radians) and
`rho_Y1`/`rho_Y2`. A time is simply absent from the result if the shadow
cone doesn't reach the terminator at all at that instant.

### `rise_set_curves(B, *, umbra=False, append=True)`

```python
def rise_set_curves(B: pd.DataFrame, *, umbra: bool = False, append: bool = True) -> pd.DataFrame
```

The two sunrise/sunset-limited path-edge curves, as lat/lon (columns
suffixed `1`/`2`, e.g. `lat1`/`lon1`, `lat2`/`lon2`). `B` must already
carry `aux1_elements`'s columns.

### `shadow_contact_times(elements_at, t0, shadow, radius_days=4/24)`

```python
def shadow_contact_times(elements_at: ElementsAt, t0: Time, shadow: Literal["umbra", "penumbra", "center"], radius_days: float = 4/24) -> tuple
```

Whole-path contact times for the shadow's outer/inner edge, searched
within `radius_days` of `t0`.

- **`shadow='center'`** — returns `(t1, t2)`: when the shadow axis itself
  first/last touches the Earth.
- **`shadow='umbra'`/`'penumbra'`** — returns `(t1, t2, t3, t4)`: `t1`/`t4`
  are when the outer edge of that shadow first/last touches the Earth;
  `t2`/`t3` are when the inner edge does (i.e. when the *whole* shadow
  is/stops being on the Earth). **Any entry may be `None`** if that
  crossing doesn't occur within `radius_days` — see `terminator_events`
  below for why `t2`/`t3` commonly don't exist for the penumbral case.

### `terminator_events(elements_at, t0)`

```python
def terminator_events(elements_at: ElementsAt, t0: Time) -> pd.DataFrame
```

The whole-path contact events that occur, as a `DataFrame` indexed by
event name with `time`, `lat`, `lon` columns. Possible event names: `P1`,
`P2`, `P3`, `P4` (penumbral outer/inner ×2), `U1`, `U2`, `U3`, `U4`
(umbral, same pattern), `CE1`, `CE2` (shadow axis first/last touching
Earth — these are what published "C1/C2 of the whole path" figures
usually mean).

**An event is simply absent from the result if it doesn't occur** within
the default 4-day search radius (widen `t0`'s enclosing
`BesselianEclipse`'s `hour_span_coarse` if you need this to reach further)
— this is expected, not an error. `P2`/`P3` (the penumbral shadow being
*entirely* on the Earth's disk at once) commonly don't exist for a
large-magnitude eclipse, whose penumbra can exceed Earth's diameter for
much of the event.

For the 2026-08-12 event, `CE1`/`CE2` have been validated against
independently published whole-path start/end figures to the *second* in
time and ~0.002° in position.

---

## DataFrame column reference

Most functions in this package append columns to a running `DataFrame`
rather than returning something bespoke each time. Here's what every
column means, grouped by where it first appears.

### From `elements.bessels_at` (always present)

| Column | Meaning | Units |
|---|---|---|
| `x`, `y` | Shadow-axis position in the fundamental plane | Earth radii |
| `mu0` | Hour angle of the shadow axis at the Greenwich meridian | degrees (see the ΔT-sensitivity note under [`bessels_at`](#eclipse_calcelements)) |
| `d` | Declination of the shadow axis | degrees |
| `l1`, `l2` | Penumbral/umbral shadow-cone radii at the fundamental plane | Earth radii |
| `tanf1`, `tanf2` | Penumbral/umbral cone half-angle tangents | dimensionless |
| `gast` | Greenwich apparent sidereal time | hours |

### From `d_<col>` derivative columns (when `derivatives=True`)

Same names as above, prefixed `d_` (e.g. `d_x`, `d_mu0`) — the
time-derivative of that quantity, in `<quantity>/second`.

### From `ellipsoid.aux1_elements`

| Column | Meaning |
|---|---|
| `rho1`, `rho2` | Ellipsoid radii at the shadow-axis declination |
| `sind1`, `cosd1`, `sind1d2`, `cosd1d2` | Auxiliary sine/cosine products for the ksi/eta ↔ lat/lon conversion |

### From `ellipsoid.ksieta_to_latlon` (and anything built on it: central line, shadow outline/limits, terminator)

| Column | Meaning |
|---|---|
| `ksi`, `eta` | Fundamental-plane position (Earth radii) — the input, echoed back |
| `eta1`, `zeta1` | Intermediate ellipsoid-intersection quantities |
| `zeta` | Height above the fundamental plane toward the observer (Earth radii) |
| `theta` | Local hour angle at the resulting point (degrees) |
| `lat`, `lon` | Latitude/longitude of the point (degrees; `lon` wrapped to `[-180, 180)`) |

In `shadow_outlines`, these are prefixed `Q_`. In `shadow_limits`, prefixed
`N_`/`S_`. In `terminator.rise_set_curves`, suffixed `1`/`2`.

### From `observer.local_elements` (when `location` is given)

| Column | Meaning |
|---|---|
| `L1`, `L2` | Penumbral/umbral shadow radii **in the observer's plane** (Earth radii) — compare against distance-to-shadow-axis to test eclipse/no-eclipse |
| `ksi`, `eta`, `zeta` | The *observer's* position in the fundamental plane |
| `eta1`, `zeta1` | Intermediate quantities, as above |
| `rho` | Observer's geocentric distance (Earth radii) |

### From `central_line.central_elements`

`L1`, `L2`, `ksi`, `eta`, `zeta`, `lat`, `lon` as above, evaluated *on the
shadow axis itself* (`ksi = eta = 0`).

### From `central_line.central_duration_width`

| Column | Meaning |
|---|---|
| `duration_s` | Central eclipse duration | seconds |
| `width` | Path width | Earth radii (× ~6378 for km) |

### From `terminator.solve_gamma`

| Column | Meaning |
|---|---|
| `Y1`, `Y2` | The two terminator-crossing position angles | radians |
| `rho_Y1`, `rho_Y2` | Distance from the fundamental plane's origin at each crossing | Earth radii |

---

## Known limitations

- **Magnitude, obscuration, position angle, parallactic angle, and
  Sun/Moon angular semi-diameters are not implemented.** Confirmed absent
  from the research code this package was extracted from; net-new work,
  not something lost in the port.
- **Penumbral `shadow_limits` (`umbra=False`) can fail to converge** for
  the wide penumbral cone — see the caveat under
  [`shadow.shadow_limits`](#eclipse_calcshadow). It degrades gracefully
  (drops the unconverged point, logs a warning) rather than returning a
  wrong-looking value, but a better initial-guess strategy for this case
  is a known, unimplemented follow-up.
- **`mu0` has an offset relative to published reference tables** (not the
  package's other elements) proportional to the difference between
  Skyfield's ΔT and whichever ΔT a given published table used — see the
  note under [`elements.bessels_at`](#eclipse_calcelements). This is
  expected behavior from using a live ΔT model, not a defect.
- **`BesselianEclipse`'s polynomial fit degrades outside its
  `hour_span_coarse` window.** Widen it if you need accurate results far
  from `t0` (e.g. a multi-day terminator-event search).
- **Lunar limb irregularities (and Baily's beads, which they cause) are
  not modeled** — the Moon is treated as a perfect circle. See
  [`TODO.md`](../TODO.md).
