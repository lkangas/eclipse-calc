# TODO / Roadmap

Planned features not yet implemented. See `docs/API.md`'s "Known
limitations" section for what's already present but incomplete vs. what's
simply missing (this file is the latter).

## Eclipse occurrence and search

Nothing in the package finds an eclipse. `BesselianEclipse` is anchored
at a `t0` the caller must already know, so every entry point sits
downstream of a date supplied by hand: the ephemeris is never asked
*whether* an eclipse happens, only what its geometry is once it's been
told that one does. There is no way to sweep a span of years and get
back the eclipses in it.

The geocentric occurrence tests of Explanatory Supplement 3rd ed.
Sec. 11.2 close that gap, and need nothing the package doesn't already
have -- an ephemeris, apparent Sun/Moon places, and `constants`:

- **Least angular separation at syzygy.** `sigma = beta_m cos I'`, with
  `tan I' = lambda/(lambda - 1) * tan I` and `lambda` the ratio of the
  Moon's to the Sun's motion in ecliptic longitude (Eqs. 11.1,
  11.7-11.9). Taking `I` as the local slope `d(beta)/d(lon)` at the
  syzygy, rather than the mean 5.145 deg, keeps it self-consistent with
  how `beta_m` itself is obtained and absorbs perturbation and
  nodal-regression effects.
- **Solar conditions.** Partial if `sigma < s_s + s_m + pi_m - pi_s`
  (11.21); central if `sigma < |s_s - s_m + pi_m - pi_s|` (11.23);
  total vs. annular by comparing `s_m` against `s_s`. Hybrids are not
  decidable from occurrence alone -- the book says as much, and the
  central-line machinery already here is what settles them.
- **Lunar conditions.** Earth shadow-cone semidiameters `f1`, `f2` from
  the reduced parallax `pi_1 = 0.998340 * pi_m` and the 1.02
  atmospheric enlargement (11.10-11.12), then penumbral/partial/total
  by the same `sigma` comparison (11.13-11.15).

Needs: a syzygy search (new/full moons in geocentric ecliptic
longitude), plus geocentric semidiameters and horizontal parallaxes --
themselves a documented gap (see `docs/API.md`).

This fits the existing conventions without straining them: a
`DataFrame` indexed by UTC datetime, one row per syzygy, scalar or
vector `Time` accepted, nothing downloaded. Two things worth getting
right:

- **Sweep in one vectorized pass.** A per-syzygy loop costs several
  ephemeris evaluations each, and a catalogue-length span runs to tens
  of thousands of syzygies. Skyfield takes a vector `Time`; the whole
  span should be a handful of calls, which is also what the
  `DataFrame`-per-call shape wants.
- **One set of radii.** Take the lunar semidiameter from
  `constants.k1` and the solar from `ds` rather than introducing
  separate kilometre radii. `k1` matches Sec. 11.1.2's single-`k`
  convention; an independent 1737.4 km Moon differs by ~0.04% in
  `s_m`, which only shows up on borderline classifications, but there
  is no reason to carry two conventions.

Validate against a published catalogue of eclipse dates and types
rather than against geometry from within the package -- the existing
tests are all anchored on a single event, and occurrence is the first
thing here that can be checked across hundreds of them.

Independent of the limb work below; nothing in that chain blocks this.

Open question: the package describes itself as solar eclipse geometry,
but the lunar conditions above share nearly all of the same machinery,
and dropping them would leave the module half-written for the sake of
the title.

## Eclipse seasons

Falls out of occurrence once the quantities above exist, and is the
natural way to answer "when could the next one be" rather than "was
this one an eclipse". Two things that are easy to conflate and are
worth separating in the API:

- a **node crossing** is the Moon crossing the ecliptic (`beta_m = 0`),
  about 27 times a year;
- a **season centre** is the *Sun* passing one of the Moon's slowly
  regressing nodes, about twice a year, and it is what an eclipse
  season is centred on.

The window half-width around a centre follows from the same limits as
the occurrence tests, converted through the Sun's rate of motion in
longitude -- using the Moon's rate answers a different question and
gives a window roughly 13x too narrow.

Depends on eclipse occurrence above.

## Lunar limb calculations

The Moon's limb is not a smooth circle -- it's mountains and valleys, and
the true profile matters for three things:

- **Contact-time corrections.** 2nd/3rd contact times can shift by up to
  ~2 seconds from the mean-limb prediction depending on which part of the
  limb is involved (see Explanatory Supplement 3rd ed. Sec. 11.1.2, and
  Herald 1983, JBAA 93, 241-246). Currently averaged out / not implemented.
- **Baily's beads** (below), which the limb profile physically causes.
- **The shape of the shadow outline itself** (below) -- currently a smooth
  circle/ellipse, not the true irregular footprint.

Needs: a lunar limb-profile data source (e.g. Watts' 1963 charts, or a
profile derived from modern LOLA/Kaguya topography) giving limb radius as
a function of position angle and libration, combined with the existing
Besselian/local-circumstance geometry.

Note: the Explanatory Supplement itself only *flags* this gap (Sec. 11.1.2,
11.2.4.1, 11.3.6.2) -- each mention is one line pointing to Herald (1983)
for the actual method; ES carries no limb-profile data or correction
formulas of its own. "Baily's beads" isn't named anywhere in the chapter.

Candidate sources, classical to modern:
- Watts, C. B. (1963). "The Marginal Zone of the Moon." Astron. Papers
  Amer. Ephem. 17, 1-951. The original limb survey (~0.20" precision).
- Van Flandern, T. C. (1970). "Some Notes on the Use of the Watts
  Limb-Correction Charts." AJ 75(6), 744-746.
- Morrison, L. V., & Appleby, G. M. (1981). "Analysis of Lunar
  Occultations -- III. Systematic Corrections to Watts' Limb-Profiles for
  the Moon." MNRAS 196(4), 1013-1020. Corrects the Watts datum for
  ellipticity and center-of-mass offset (up to 0.4" error otherwise).
- Herald, D. (1983). "Correcting Predictions of Solar Eclipse Contact
  Times for the Effects of Lunar Limb Irregularities." JBAA 93, 241-246.
  Applies the above specifically to solar-eclipse contact times.
- Araki, H., et al. (2009). "Lunar Global Shape and Polar Topography
  Derived from Kaguya-LALT Laser Altimetry." Science 323(5916), 897-900.
  ~1.5 km sampling, ~1 m height accuracy -- the modern topography source.
- Smith, D. E., et al. (2010). "The Lunar Orbiter Laser Altimeter (LOLA)
  Investigation on the Lunar Reconnaissance Orbiter Mission." Space Sci.
  Rev. 150, 209-241. Current gold-standard lunar topography.
- Jubier, X. (2017). "Syzygy Information: Lunar Limb Profiles at Total
  Eclipses of the Decade." DPS poster/abstract #417.17. Uses Kaguya+LOLA
  to predict Baily's beads (not just contact-time corrections) to ~0.2 s
  -- the closest real-world precedent for the simulation item below.

Reported accuracy (NASA, eclipse.gsfc.nasa.gov/SEhelp/limb.html): no
correction => 2-3 s contact-time error; Watts+Morrison/Appleby => better
than 0.5 s; Kaguya/LOLA-based => ~0.2 s.

## Baily's beads simulation

Given local circumstances at an observer (contact geometry; note
`eclipse_calc` doesn't compute position angle of contact yet either --
see `docs/API.md`) and the lunar limb profile above, compute which limb
valleys let sunlight through as "beads" during 2nd/3rd contact: their
position angles, individual appearance/disappearance times and duration,
and the diamond-ring effect as the last/first bead.

Depends on lunar limb calculations above.

## Limb-corrected shadow outline

`shadow.shadow_outlines` currently sweeps position angle Q at a *constant*
shadow-cone radius (`L_i = l_i - zeta*tan(f_i)`, per ES Eq. 11.104) for
each instant -- the Moon is treated as a perfect circle, so whatever
irregularity the outline has today comes only from the ellipsoid
projection, not the Moon's actual shape. With the limb profile from
"Lunar limb calculations" above, the radius used at each Q should instead
be corrected for the limb height in that direction (rotated for
libration/parallactic orientation as seen from the shadow axis), giving
the umbral/penumbral footprint its true irregular, near-polygonal shape --
most visible for narrow/grazing paths and near the ends of a track, where
the smooth-limb approximation is worst.

Depends on lunar limb calculations above; same data source, applied to
`shadow.shadow_outlines` instead of contact times / local circumstances.
