"""
Toy Cherenkov-cone simulation for a PICOSEC-style solid radiator.

Geometry: a MIP crosses a MgF2 crystal of thickness T and the photocathode sits
directly on the exit face.  There is no drift space, so the cone is not imaged as
a thin ring -- photons emitted at depth z land at radius

    r = (T - z) * tan(theta_c(lambda))

With emission uniform along the track, r is uniform on [0, R_max] for a fixed
wavelength.  Chromatic dispersion in MgF2 is large over the CsI sensitivity band
(115-200 nm), so theta_c and hence R_max vary photon to photon.

Estimator under study (deliberately naive, no bias correction):

    centre_hat = mean(x_i), mean(y_i)
    R_hat      = mean(|p_i - centre_hat|)
    D_hat      = 4 * R_hat

The factor 4 (rather than 2) is the known geometric scaling for a filled disk,
where mean(r) = R_max / 2 -- it is a property of the cone shape, not of the
sample, so it is applied up front.  The finite-N bias that remains, from the
centroid being built out of the same N photons, is NOT corrected: that is the
thing being measured.
"""

import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(20260901)

# ----------------------------------------------------------------------------
# Radiator / photocathode
# ----------------------------------------------------------------------------
THICKNESS = 3.0      # mm, MgF2 crystal (standard PICOSEC).  Pure scale factor.
BETA = 1.0           # MIP
SIGMA_XY = 0.05      # mm, photoelectron transport smearing in the preamp gap
LAM_MIN, LAM_MAX = 115.0, 200.0   # nm, MgF2 cutoff -> CsI QE cutoff


def n_mgf2(lam_um):
    """Sellmeier index of MgF2 (Dodge 1984, ordinary ray), lam in microns."""
    l2 = lam_um ** 2
    return np.sqrt(1.0
                   + 0.48755108 * l2 / (l2 - 0.04338408 ** 2)
                   + 0.39875031 * l2 / (l2 - 0.09461442 ** 2)
                   + 2.3120353 * l2 / (l2 - 23.793604 ** 2))


def csi_qe(lam_nm):
    """Toy CsI quantum efficiency: 0 at 200 nm, ramping to 0.30 below 140 nm."""
    return np.clip((200.0 - lam_nm) / 60.0, 0.0, 1.0) * 0.30


# Frank-Tamm dN/dlambda ~ sin^2(theta_c) / lambda^2, folded with the QE.
_lam = np.linspace(LAM_MIN, LAM_MAX, 2000)
_n = n_mgf2(_lam / 1000.0)
_cos = 1.0 / (BETA * _n)
_sin2 = np.clip(1.0 - _cos ** 2, 0.0, None)
_w = csi_qe(_lam) * _sin2 / _lam ** 2
_cdf = np.cumsum(_w)
_cdf /= _cdf[-1]

THETA_MEAN = np.average(np.arccos(_cos), weights=_w)
TAN_MEAN = np.average(np.tan(np.arccos(_cos)), weights=_w)
R_MAX_MEAN = THICKNESS * TAN_MEAN          # mean outer radius of the cone
D_GEO = 2.0 * R_MAX_MEAN                   # geometric cone diameter at the pc


def sample_photons(shape):
    """Sample photon (x, y) impact points on the photocathode."""
    lam = np.interp(rng.random(shape), _cdf, _lam)
    tan_t = np.tan(np.arccos(1.0 / (BETA * n_mgf2(lam / 1000.0))))
    r = THICKNESS * rng.random(shape) * tan_t   # uniform emission depth
    phi = rng.uniform(0.0, 2 * np.pi, size=shape)
    x = r * np.cos(phi) + rng.normal(0.0, SIGMA_XY, size=shape)
    y = r * np.sin(phi) + rng.normal(0.0, SIGMA_XY, size=shape)
    return x, y


def estimate_diameter(x, y):
    """Diameter estimate from hits.  x, y have shape (trials, N).

    2 * mean(r) recovers R_max for a disk uniform in r, so a further factor 2
    converts it to a diameter.
    """
    cx = x.mean(axis=1, keepdims=True)
    cy = y.mean(axis=1, keepdims=True)
    return 4.0 * np.hypot(x - cx, y - cy).mean(axis=1)


# ----------------------------------------------------------------------------
# Scan the estimator vs number of detected photoelectrons
# ----------------------------------------------------------------------------
N_VALUES = np.unique(np.round(np.logspace(0, 4, 40)).astype(int))
TRIALS = 2000

mean_d = np.empty(N_VALUES.size)
lo_d = np.empty(N_VALUES.size)
hi_d = np.empty(N_VALUES.size)

for i, n in enumerate(N_VALUES):
    d_hat = estimate_diameter(*sample_photons((TRIALS, n)))
    mean_d[i] = d_hat.mean()
    lo_d[i], hi_d[i] = np.percentile(d_hat, [16, 84])

print(f"theta_c (QE-weighted mean) = {np.rad2deg(THETA_MEAN):.2f} deg")
print(f"cone outer radius <R_max>  = {R_MAX_MEAN:.3f} mm")
print(f"geometric cone diameter    = {D_GEO:.3f} mm")
print(f"asymptote of D_hat         = {mean_d[-1]:.3f} mm  "
      f"(= {mean_d[-1] / D_GEO:.3f} x the geometric diameter)\n")
for n, m in zip(N_VALUES, mean_d):
    print(f"N = {n:6d}   <D_hat> = {m:6.3f} mm   vs geometric D = {D_GEO:.3f} mm "
          f"({100 * (m - D_GEO) / D_GEO:+7.2f} %)")

# ----------------------------------------------------------------------------
# Per-event spread of the estimate at a few small N
# ----------------------------------------------------------------------------
N_SMALL = (2, 3, 4, 5, 6, 20)
EVENTS = 200_000
per_event = {n: estimate_diameter(*sample_photons((EVENTS, n))) for n in N_SMALL}

print("\nper-event estimate, small N:")
for n, d in per_event.items():
    q16, q50, q84 = np.percentile(d, [16, 50, 84])
    print(f"  N = {n:3d}   mean {d.mean():5.2f}   median {q50:5.2f}   "
          f"68% [{q16:5.2f}, {q84:5.2f}]   RMS/mean {d.std() / d.mean():5.2f}")

# ----------------------------------------------------------------------------
# High-stats sample for the shape panels
# ----------------------------------------------------------------------------
bx, by = sample_photons(2_000_000)
br = np.hypot(bx, by)

BLUE, ORANGE, GREY = "#2f6db5", "#d1743a", "#8a8f98"
RAMP = ["#c3d9ef", "#9dbfe2", "#77a5d4", "#5289c4", "#356ca8", "#1f4b7a"]

fig = plt.figure(figsize=(11.5, 12.4))
gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1.05], hspace=0.32, wspace=0.24)
axes = np.array([[fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])],
                 [fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])]])
ax_e = fig.add_subplot(gs[2, :])

# (a) radial PDF p(r)
ax = axes[0, 0]
counts, edges = np.histogram(br, bins=220, range=(0, 1.25 * THICKNESS * 1.4),
                             density=True)
ctr = 0.5 * (edges[:-1] + edges[1:])
ax.plot(ctr, counts, color=BLUE, lw=2, label="solid radiator (filled cone)")
ax.axvline(R_MAX_MEAN, color=GREY, lw=1, ls="--")
ax.annotate(f"$\\langle R_{{max}} \\rangle$ = {R_MAX_MEAN:.2f} mm",
            xy=(R_MAX_MEAN, 0.32 * counts.max()), xytext=(6, 0),
            textcoords="offset points", color=GREY, fontsize=9)
ax.plot(ctr, np.exp(-0.5 * ((ctr - R_MAX_MEAN) / 0.15) ** 2) * counts.max(),
        color=ORANGE, lw=1.6, ls=":", label="thin radiator (ring), for contrast")
ax.set_xlabel("distance from cone centre  r  [mm]")
ax.set_ylabel("p(r)   [1/mm]")
ax.set_title("(a) radial PDF: flat-ish in r, not a ring", fontsize=10)
ax.legend(frameon=False, fontsize=8.5, loc="upper right")

# (b) 2D surface density -- is it a Gaussian?
ax = axes[0, 1]
area = np.pi * (edges[1:] ** 2 - edges[:-1] ** 2)
dens = counts * (edges[1] - edges[0]) / area
ax.plot(ctr, dens, color=BLUE, lw=2, label="dN/dA  (simulated)")
ref = ctr > 0.15
ax.plot(ctr[ref], dens[ref][0] * ctr[ref][0] / ctr[ref], color=GREY, lw=1.4,
        ls="--", label=r"$\propto 1/r$")
sig = np.sqrt(0.5 * np.average(br ** 2))
ax.plot(ctr, dens[0] * np.exp(-0.5 * (ctr / sig) ** 2), color=ORANGE, lw=1.6,
        ls=":", label="2D Gaussian, matched RMS")
ax.set_yscale("log")
ax.set_ylim(dens[dens > 0].min() * 0.5, dens.max() * 3)
ax.set_xlabel("r  [mm]")
ax.set_ylabel("photon surface density  [1/mm$^2$]")
ax.set_title("(b) centrally peaked as 1/r with a hard edge", fontsize=10)
ax.legend(frameon=False, fontsize=8.5, loc="lower left")

# (c) example hit patterns
ax = axes[1, 0]
for n, col, alpha, lab in ((500, GREY, 0.25, "N = 500"), (20, BLUE, 1.0, "N = 20")):
    hx, hy = sample_photons((1, n))
    ax.scatter(hx[0], hy[0], s=14, alpha=alpha, color=col, edgecolors="none",
               label=lab)
    ax.plot(hx.mean(), hy.mean(), marker="+", ms=12, mew=2, color=col)
ax.add_patch(plt.Circle((0, 0), R_MAX_MEAN, fill=False, color=GREY, lw=1, ls="--"))
ax.set_aspect("equal")
ax.set_xlabel("x [mm]")
ax.set_ylabel("y [mm]")
ax.set_title("(c) hits on the photocathode, centroid marked (+)", fontsize=10)
ax.legend(frameon=False, fontsize=9, loc="upper right")

# (d) estimated diameter vs N
ax = axes[1, 1]
ax.axvspan(10, 25, color=GREY, alpha=0.12, lw=0)
ax.annotate("typical PICOSEC\nMIP yield", xy=(16, 0.7), xytext=(0, 0),
            textcoords="offset points", ha="center", color=GREY, fontsize=8.5)
ax.fill_between(N_VALUES, lo_d, hi_d, color=BLUE, alpha=0.18, lw=0,
                label="68% of trials")
ax.plot(N_VALUES, mean_d, color=BLUE, lw=2, marker="o", ms=4,
        label=r"$\langle \hat{D} \rangle$ (uncorrected)")
ax.axhline(D_GEO, color=ORANGE, lw=1.2, ls="--")
ax.annotate(f"geometric cone diameter = {D_GEO:.2f} mm",
            xy=(N_VALUES[-1], D_GEO), xytext=(-4, 5), textcoords="offset points",
            ha="right", color=ORANGE, fontsize=9)
ax.set_xscale("log")
ax.set_ylim(0, 1.25 * D_GEO)
ax.set_xlabel("number of detected photoelectrons  N")
ax.set_ylabel(r"estimated cone diameter  $\hat{D}$  [mm]")
ax.set_title(f"(d) naive estimator vs N ({TRIALS} trials/point)", fontsize=10)
ax.legend(frameon=False, fontsize=9, loc="lower right")

# (e) per-event distribution of the estimate at small N
bins = np.linspace(0, 2.0 * D_GEO, 200)
for col, n in zip(RAMP, N_SMALL):
    h, _ = np.histogram(per_event[n], bins=bins, density=True)
    ax_e.step(0.5 * (bins[:-1] + bins[1:]), h, where="mid", color=col, lw=1.8,
              label=f"N = {n}")
ax_e.axvline(D_GEO, color=ORANGE, lw=1.2, ls="--")
ax_e.annotate(f"geometric cone diameter = {D_GEO:.2f} mm", xy=(D_GEO, 0.98),
              xycoords=("data", "axes fraction"), xytext=(6, -4),
              textcoords="offset points", va="top", color=ORANGE, fontsize=9)
ax_e.set_xlim(0, 2.0 * D_GEO)
ax_e.set_xlabel(r"per-event estimate  $\hat{D}$  [mm]")
ax_e.set_ylabel("probability density  [1/mm]")
ax_e.set_title(f"(e) event-by-event spread of the estimate ({EVENTS:,} events per N)",
               fontsize=10)
ax_e.legend(frameon=False, fontsize=9, ncol=2, loc="upper right")

for ax in list(axes.ravel()) + [ax_e]:
    ax.grid(True, color="0.9", lw=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

fig.savefig("cherenkov_cone_sim.png", dpi=150)
print("\nwrote cherenkov_cone_sim.png")
plt.show()
