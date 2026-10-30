# P2: cosmic-bench muon rates

**P2** is the parity-violating electron-scattering experiment at MESA (Mainz). The Micromegas
tracker wedges are built and tested at CEA Saclay (Irfu); the Geant4 model of a wedge lives in
`~/CLionProjects/p2-geant` (see the memory notes for that project). Saclay is putting the
detectors on a cosmic bench between three scintillators, and this directory estimates the
trigger rates they should see.

## Setup assumed

Three 20 x 60 cm scintillator bars, all parallel (long axes aligned), same footprint:

| Bar | Position |
|---|---|
| top 1 | z = 0 |
| top 2 | directly beneath top 1, 3 cm below (thin-sheet model) |
| bottom | 150 cm below top 1 |

Site: CEA Saclay, ~160 m above sea level, ~48.7 N.

## Method (`cosmic_rate.py`)

Monte Carlo with straight muon tracks. Muons are generated uniformly over the top-1 bar with
zenith angle drawn from the flux through a horizontal surface, I(theta) cos(theta), and uniform
azimuth. The coincidence rate is the top-1 rate times the fraction of tracks that also cross
the other bars. I(theta) is the energy integral of the Guan et al. (arXiv:1509.06176) modified
Gaisser sea-level spectrum, which holds up at large zenith angles (plain cos^2 is not needed).
A +1.6 % altitude factor (1 %/100 m) is applied.

```
python cosmic_rate.py                    # defaults below
python cosmic_rate.py --dist 120 --gap 5 --emin 0.5
```

Needs numpy and matplotlib only. Output: `results/run_default.txt` (rates and sensitivity scans),
`results/angular_distribution.png`.

## Result (E > 0.2 GeV, 100 % efficiency)

| Coincidence | Rate |
|---|---|
| one bar (singles, muons only) | 15.8 Hz (950 /min) |
| top 1 & top 2 | **14.3 Hz** (860 /min) |
| top 1 & top 2 & bottom | **0.51 Hz** (30 /min, 1800 /h) |

Statistical error is below 0.5 %. The systematic spread is much larger:

- **Bottom distance:** 3-fold rate is 1.05 Hz at 100 cm, 0.51 at 150 cm, 0.30 Hz at 200 cm
  (roughly 1/d^2).
- **Top-pair spacing:** moves the 2-fold from 15.3 Hz (1 cm) to 11.1 Hz (10 cm). The 3-fold does
  not change: for identical aligned bars, any line through top 1 and the bottom bar lies inside
  the footprint at every height between, so 3-fold = top 1 & bottom exactly.
- **Energy threshold** (roof, shielding, detectors in the path): 2-fold 15.1 / 14.3 / 12.9 / 11.0 Hz
  and 3-fold 0.55 / 0.51 / 0.45 / 0.37 Hz for E_min = 0.05 / 0.2 / 0.5 / 1 GeV.
  A building roof stops roughly 0.1-0.3 GeV worth of muons, so 0.2 GeV is the default.
- **Model normalisation:** the vertical intensity above 1 GeV comes out at 60 m^-2 s^-1 sr^-1,
  about 10-15 % under the usual ~70. Treat the absolute rates as good to ~15 %.

So expect **about 0.4-0.5 triple coincidences per second** (~1500-1800 per hour), and about
14 per second for the top pair, once efficiency is included.

## Not included

- Scintillator efficiency (typically 95-99 % per bar, multiply per bar: 3-fold scales as eff^3).
- Bar thickness, light-collection edge effects, detector material in the path (scattering and
  absorption), building overburden beyond the energy cut.
- East-west asymmetry (a few % at this latitude) and pressure/temperature variation (~1 %).
- Natural radioactivity and noise in the singles rates. Accidental rate for a coincidence window
  tau is about 2 tau r1 r2 (top pair) and is negligible for the 3-fold with tau of tens of ns.
- A bottom bar rotated 90 degrees relative to the top pair (not run; it would lower the 3-fold).

## Open questions for Saclay

1. Exact vertical distance between the top pair and the bottom bar (and measured from which face).
2. Bar thickness, and whether the bottom bar has the same orientation as the top pair.
3. Does any of the roof or other material sit above the bench?
