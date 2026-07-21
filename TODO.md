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

## Baily's beads simulation

Given local circumstances at an observer (contact geometry; note
`eclipse_calc` doesn't compute position angle of contact yet either --
see `docs/API.md`) and the lunar limb profile above, compute which limb
valleys let sunlight through as "beads" during 2nd/3rd contact: their
position angles, individual appearance/disappearance times and duration,
and the diamond-ring effect as the last/first bead.

Depends on lunar limb calculations above.
