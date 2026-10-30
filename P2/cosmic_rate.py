"""Expected cosmic-muon coincidence rates for a 3-scintillator cosmic bench (P2 Micromegas, CEA Saclay).

Geometry (all lengths in cm, z up, bar long axis along x):
  top1   z = 0           60 x 20 cm
  top2   z = -GAP        directly under top1, same footprint
  bottom z = -DIST       same footprint, same orientation, centred under the stack

Method: forward Monte Carlo. Muons are generated on the plane of top1, uniform in position over
the bar, with directions drawn from the flux through a horizontal surface, I(theta) cos(theta)
(azimuth uniform). Every generated muon therefore crosses top1, and the top1 rate is exactly
A * integral(I cos dOmega). Each coincidence rate is that rate times the fraction of muons that
also cross the other bars (straight lines, bars treated as thin sheets, efficiency 100%).

I(theta) = integral over E of the Guan et al. (arXiv:1509.06176) modified-Gaisser sea-level
muon spectrum, which keeps its shape at large zenith angles.

Usage:  python cosmic_rate.py [--n 20000000] [--emin 0.2] [--alt 160] [--out DIR]
"""
import argparse
import os

import numpy as np

# Guan et al. 2015 parametrisation of the effective cos(theta*)
_trapz = getattr(np, "trapezoid", None) or np.trapz
P = (0.102573, -0.068287, 0.958633, 0.0407253, 0.817285)

# Altitude scaling. Muon intensity at ~GeV energies grows roughly 1 %/100 m near sea level
# (less atmosphere to decay/absorb in). Only a few percent at Saclay; shown as an uncertainty.
ALT_GAIN_PER_M = 1.0e-4


def cos_star(c):
    p1, p2, p3, p4, p5 = P
    return np.sqrt((c**2 + p1**2 + p2 * c**p3 + p4 * c**p5) / (1 + p1**2 + p2 + p4))


def dI_dE(E, c):
    """Differential vertical-ish intensity, cm^-2 s^-1 sr^-1 GeV^-1 (E in GeV, c = cos theta)."""
    cs = cos_star(c)
    Ec = E * cs
    return (0.14 * (E * (1 + 3.64 / (E * cs**1.29))) ** -2.7
            * (1 / (1 + 1.1 * Ec / 115) + 0.054 / (1 + 1.1 * Ec / 850)))


def intensity(theta, emin, emax=1000.0, nE=4000):
    """I(theta) = integral dI/dE dE, cm^-2 s^-1 sr^-1, for E > emin (GeV)."""
    E = np.geomspace(emin, emax, nE)
    c = np.cos(theta)[:, None]
    f = dI_dE(E[None, :], c) * E[None, :]  # d(lnE) integration
    return _trapz(f, np.log(E), axis=1)


def build_sampler(emin, ntheta=2000):
    th = np.linspace(0, np.pi / 2, ntheta)
    I = intensity(th, emin)
    w = I * np.cos(th) * np.sin(th)  # flux through horizontal plane per dtheta
    cdf = np.concatenate([[0], np.cumsum(0.5 * (w[1:] + w[:-1]) * np.diff(th))])
    total_flux_per_az = cdf[-1]  # per radian of azimuth
    return th, I, cdf / cdf[-1], 2 * np.pi * total_flux_per_az  # last = integral I cos dOmega, cm^-2 s^-1


def simulate(n, geom, th, cdf, rng, chunk=5_000_000):
    """Return counts (n_total, n_top12, n_top12_bot, n_bot_given_top1) for muons crossing top1."""
    hx, hy = geom["half_x"], geom["half_y"]
    zs = {"top2": -geom["gap"], "bot": -geom["dist"]}
    cnt = dict(top1=0, t12=0, t123=0, t1b=0)
    done = 0
    while done < n:
        m = min(chunk, n - done)
        theta = np.interp(rng.random(m), cdf, th)
        phi = rng.random(m) * 2 * np.pi
        x0 = (rng.random(m) * 2 - 1) * hx
        y0 = (rng.random(m) * 2 - 1) * hy
        tx, ty = np.tan(theta) * np.cos(phi), np.tan(theta) * np.sin(phi)

        def hit(z):
            x, y = x0 + tx * z, y0 + ty * z
            return (np.abs(x) <= hx) & (np.abs(y) <= hy)

        h2, hb = hit(zs["top2"]), hit(zs["bot"])
        cnt["top1"] += m
        cnt["t12"] += int(h2.sum())
        cnt["t123"] += int((h2 & hb).sum())
        cnt["t1b"] += int(hb.sum())
        done += m
    return cnt


def rates(emin, alt, geom, n, seed=1):
    th, I, cdf, flux = build_sampler(emin)
    rng = np.random.default_rng(seed)
    cnt = simulate(n, geom, th, cdf, rng)
    area = 4 * geom["half_x"] * geom["half_y"]
    r1 = flux * area * (1 + ALT_GAIN_PER_M * alt)  # Hz through top1

    def rate(k):
        p = cnt[k] / cnt["top1"]
        return r1 * p, r1 * np.sqrt(p * (1 - p) / cnt["top1"])

    return dict(single=(r1, 0.0), t12=rate("t12"), t123=rate("t123"), t1b=rate("t1b"),
                flux_h=flux, I_vert=I[0], I_theta=(th, I))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20_000_000)
    ap.add_argument("--emin", type=float, default=0.2, help="muon energy threshold, GeV")
    ap.add_argument("--alt", type=float, default=160.0, help="altitude, m")
    ap.add_argument("--gap", type=float, default=3.0, help="top1-top2 distance, cm")
    ap.add_argument("--dist", type=float, default=150.0, help="top1-bottom distance, cm")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "results"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    geom = dict(half_x=30.0, half_y=10.0, gap=a.gap, dist=a.dist)
    r = rates(a.emin, a.alt, geom, a.n)
    print(f"E > {a.emin} GeV, altitude {a.alt:.0f} m, gap {a.gap} cm, dist {a.dist} cm")
    print(f"vertical I = {r['I_vert']*1e4:.1f} m^-2 s^-1 sr^-1;  horizontal-plane flux = "
          f"{r['flux_h']*60:.3f} cm^-2 min^-1")
    for k, lab in [("single", "single bar"), ("t12", "top1 & top2"), ("t123", "top1 & top2 & bottom"),
                   ("t1b", "top1 & bottom")]:
        v, e = r[k]
        print(f"{lab:24s} {v:8.3f} +- {e:.3f} Hz   = {v*60:8.1f} /min = {v*3600:9.0f} /h")

    # sensitivity scans
    print("\nSensitivity of 3-fold rate (Hz):")
    base = dict(geom)
    for d in (100, 125, 150, 175, 200):
        g = dict(base, dist=float(d))
        print(f"  dist {d:3d} cm : {rates(a.emin, a.alt, g, a.n // 4)['t123'][0]:.3f}")
    for gp in (1, 3, 5, 10):
        g = dict(base, gap=float(gp))
        print(f"  gap  {gp:3d} cm : t12 {rates(a.emin, a.alt, g, a.n // 4)['t12'][0]:.2f}  "
              f"t123 {rates(a.emin, a.alt, g, a.n // 4)['t123'][0]:.3f}")
    for em in (0.05, 0.2, 0.5, 1.0):
        print(f"  Emin {em:4.2f} GeV : t12 {rates(em, a.alt, geom, a.n // 4)['t12'][0]:.2f}  "
              f"t123 {rates(em, a.alt, geom, a.n // 4)['t123'][0]:.3f}")
    # figure: angular distribution
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    th, I = r["I_theta"]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(np.degrees(th), I * 1e4, label=f"Guan, E > {a.emin} GeV")
    ax.plot(np.degrees(th), I[0] * 1e4 * np.cos(th) ** 2, "--", label=r"$I_0\cos^2\theta$")
    ax.set_xlabel("zenith angle (deg)")
    ax.set_ylabel(r"I($\theta$)  [m$^{-2}$ s$^{-1}$ sr$^{-1}$]")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(a.out, "angular_distribution.png"), dpi=150)


if __name__ == "__main__":
    main()
