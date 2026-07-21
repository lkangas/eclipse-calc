# TODO / Roadmap

Planned features not yet implemented. See `docs/API.md`'s "Known
limitations" section for what's already present but incomplete vs. what's
simply missing (this file is the latter).

## Lunar limb calculations

The Moon's limb is not a smooth circle -- it's mountains and valleys, and
the true profile matters for two things:

- **Contact-time corrections.** 2nd/3rd contact times can shift by up to
  ~2 seconds from the mean-limb prediction depending on which part of the
  limb is involved (see Explanatory Supplement 3rd ed. Sec. 11.1.2, and
  Herald 1983, JBAA 93, 241-246). Currently averaged out / not implemented.
- **Baily's beads** (below), which the limb profile physically causes.

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
  Eclipses of the Decade." DPS abstract #417.17. Uses Kaguya+LOLA to
  predict Baily's beads (not just contact-time corrections) to ~0.2 s --
  the closest real-world precedent for the simulation item below.

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
