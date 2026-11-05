"""Regenerate the README figures in docs/figures/ from results/ (and, for fig4, the track cache).

Usage: python3 make_figures.py [--cache DIR]
  fig1_warp_accuracy.png   image-level injection (results/warp_study.json)
  fig2_window_repeatability.png   results/window_study.json
  fig3_vio_validation.png  per-trajectory ATE table (VIO_ATE below, copied from the README / ws1 logs)
  fig4_vertical_disparity.png   needs cache/ntnu_105_60_k6g6.npz and UWB_DATA (skipped if absent)
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np

ROOT = Path(__file__).parent
OUT = ROOT / "docs" / "figures"

GREY, BLUE, RED, GREEN = "#4d4d4d", "#0072B2", "#D55E00", "#009E73"
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10, "figure.facecolor": "white",
                     "axes.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 150})

# Verdict thresholds from README "Method" (|w_y| deg: err(8 m) = 10 %, err(3 m) = 10 %; same numbers as estimators.verdict).
W_Y_CHECK_DEG, W_Y_RECAL_DEG = 0.079, 0.21

# mean-ATE table rows (m) per NTNU 2023 trajectory 01..06, from ntnu_all.tsv rows
# dvl_none_off, wy_m010, wy_m027, wy_p010 (uw_ct_vio h05, ws1 2026-11-04); README table gives the means.
VIO_ATE = {
    "given": [0.206, 0.642, 0.418, 0.293, 0.438, 0.410],
    "tool": [0.474, 0.663, 0.422, 0.322, 0.339, 0.366],
    "oracle": [1.078, 0.930, 0.466, 0.502, 0.616, 0.394],
    "wrong": [0.465, 0.849, 0.413, 0.260, 0.612, 0.464],
}


# mean ATE (m) as printed in the README table (the mean of the rounded per-trajectory values differs in the last digit).
VIO_MEAN = {"given": 0.401, "tool": 0.431, "oracle": 0.664, "wrong": 0.510}


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"{p} {p.stat().st_size / 1024:.0f} KB")


def fig_warp() -> None:
    rows = json.loads((ROOT / "results" / "warp_study.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.9), sharex=True, sharey=True)
    lim = (-0.42, 0.42)
    for a, (ax, name) in enumerate(zip(axes, "xyz")):
        inj = np.array([r["inj"][a] for r in rows])
        sh = np.array([r["shift"][a] for r in rows])
        err = sh - inj
        ax.plot(lim, lim, color=GREY, lw=1.2, label="ideal (estimate = injection)")
        for r, i, s in zip(rows, inj, sh):
            air = r["case"] == "air"
            on_axis = abs(i) > 0.02 and not air
            mk = "o" if r["t0"] == 105 else "s"
            if air:
                ax.scatter(i, s, marker="*", s=110, color=GREEN, zorder=4, edgecolor="k", linewidth=0.4)
            elif on_axis:
                ax.scatter(i, s, marker=mk, s=38, color=BLUE, zorder=3)
            else:
                ax.scatter(i, s, marker=mk, s=38, facecolor="none", edgecolor=RED, zorder=3)
        ax.set_title(f"{name}: bias {err.mean():+.3f}, RMSE {np.sqrt(np.mean(err ** 2)):.3f} deg", fontsize=9)
        ax.set_xlabel(f"injected rotation about {name} (deg)")
        ax.set_xlim(lim)
        ax.set_ylim(lim)
        ax.set_aspect("equal")
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("estimated shift vs unwarped (deg)")
    h = [plt.Line2D([], [], color=GREY, lw=1.2),
         plt.Line2D([], [], marker="o", ls="", color=BLUE),
         plt.Line2D([], [], marker="o", ls="", mfc="none", mec=RED),
         plt.Line2D([], [], marker="*", ls="", color=GREEN, mec="k", ms=10),
         plt.Line2D([], [], marker="o", ls="", color="k", ms=5), plt.Line2D([], [], marker="s", ls="", color="k", ms=5)]
    fig.legend(h, ["ideal", "this axis injected", "other axis injected (leakage / offset)",
                   "real air-vs-water extrinsic (-0.275 deg about y)", "stretch 105 s", "stretch 170 s"],
               loc="lower center", ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, -0.14))
    fig.suptitle("Image-level injection: x and z are recovered to 0.02 deg, y with an offset of about -0.06 deg", y=1.02, fontsize=11.5)
    save(fig, "fig1_warp_accuracy.png")


def fig_window() -> None:
    rows = json.loads((ROOT / "results" / "window_study.json").read_text())
    z = [r for r in rows if r["case"] == "zero"]
    wins = sorted({r["win"] for r in z})
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(11, 4.0))
    rng = np.random.default_rng(0)
    sd = {k: [] for k in range(3)}
    for w in wins:
        v = np.array([r["fused"] for r in z if r["win"] == w])
        a0.scatter(w * np.exp(rng.uniform(-0.06, 0.06, len(v))), v[:, 1], s=14, color=BLUE, alpha=0.7, zorder=3)
        a0.hlines(v[:, 1].mean(), w * 0.88, w * 1.14, color=GREY, lw=2, zorder=4)
        for k in range(3):
            sd[k].append(v[:, k].std())
    a0.set_xscale("log")
    a0.set_xticks(wins, [str(w) for w in wins])
    a0.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    a0.set_xlabel("window length (s)")
    a0.set_ylabel("estimated w_y at zero injection (deg)")
    a0.set_title("Same rig, same calibration: w_y scatter shrinks with window", fontsize=10)
    a0.grid(alpha=0.25)
    a0.text(0.97, 0.03, "grey bar = mean; windows per length: " + ", ".join(
        f"{w} s: {sum(1 for r in z if r['win'] == w)}" for w in wins), transform=a0.transAxes, ha="right", va="bottom", fontsize=7.5)
    a0.set_ylim(-0.02, 0.45)
    for k, (name, c, m) in enumerate(zip("xyz", [GREY, BLUE, GREEN], ["^", "o", "s"])):
        a1.plot(wins, sd[k], marker=m, color=c, label=f"sd of w_{name}")
    a1.axhline(W_Y_CHECK_DEG, color=RED, ls="--", lw=1.2)
    a1.axhline(W_Y_RECAL_DEG, color=RED, ls="-", lw=1.2)
    a1.text(61, W_Y_CHECK_DEG * 1.07, "CHECK threshold |w_y| = 0.079 deg", color=RED, ha="right", va="bottom", fontsize=8.5)
    a1.text(61, W_Y_RECAL_DEG * 1.07, "RECALIBRATE threshold |w_y| = 0.21 deg", color=RED, ha="right", va="bottom", fontsize=8.5)
    a1.set_xscale("log")
    a1.set_yscale("log")
    a1.set_xticks(wins, [str(w) for w in wins])
    a1.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    a1.set_xlabel("window length (s)")
    a1.set_ylabel("repeatability sd across disjoint windows (deg)")
    a1.set_title("w_y needs >= 30 s to resolve the CHECK threshold", fontsize=10)
    a1.legend(loc="lower left", frameon=False)
    a1.grid(alpha=0.25, which="both")
    fig.suptitle("Window length: repeatability of the estimate on NTNU underwater 2023 traj_06 (3 stretches, 60 s each, cut into windows)",
                 y=1.01, fontsize=11)
    save(fig, "fig2_window_repeatability.png")


def fig_vio() -> None:
    labels = ["in-water calibration\nas given", "tool correction\n(-0.10 deg about y)",
              "mocap-oracle correction\n(-0.27 deg about y)", "wrong-sign control\n(+0.10 deg about y)"]
    colors = [BLUE, GREEN, GREY, RED]
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    rng = np.random.default_rng(1)
    for i, (k, c) in enumerate(zip(VIO_ATE, colors)):
        v = np.array(VIO_ATE[k])
        ax.bar(i, VIO_MEAN[k], width=0.62, color=c, alpha=0.55, zorder=2)
        ax.scatter(i + rng.uniform(-0.15, 0.15, len(v)), v, s=22, color="k", zorder=3)
        ax.text(i, v.max() + 0.04, f"mean {VIO_MEAN[k]:.3f} m", ha="center", va="bottom", fontsize=9.5, weight="bold", zorder=4)
    ax.axhline(VIO_MEAN["given"], color=BLUE, ls="--", lw=1)
    ax.set_xticks(range(4), labels, fontsize=9)
    ax.set_ylabel("ATE (m), uw_ct_vio h05")
    ax.set_ylim(0, 1.3)
    ax.grid(axis="y", alpha=0.25, zorder=0)
    ax.set_title("The given calibration is best: the tool's absolute reading is a bias", fontsize=11.5)
    ax.text(0.99, 0.97, "dots = 6 NTNU underwater 2023 trajectories (traj_01..06); dashed = given", transform=ax.transAxes,
            ha="right", va="top", fontsize=8.5)
    save(fig, "fig3_vio_validation.png")


def fig_field(cache: Path) -> bool:
    path = cache / "ntnu_105_60_k6g6.npz"
    if not path.exists() or "UWB_DATA" not in os.environ:
        print(f"fig4 skipped: need {path} and UWB_DATA")
        return False
    import calib
    import estimators
    from tracks import StretchData
    rig = calib.load_ntnu_water()
    prep = estimators.prepare(rig, StretchData.load(path))
    cases = [("as given (in-water)", np.zeros(3)), ("+0.3 deg about x injected", np.array([0.3, 0, 0])),
             ("+0.3 deg about z injected", np.array([0, 0, 0.3]))]
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.9), sharex=True, sharey=True, layout="constrained")
    xe, ye = np.linspace(-0.8, 0.8, 17), np.linspace(-0.6, 0.6, 13)
    for ax, (title, w) in zip(axes, cases):
        vl, vr = estimators._rect(prep, calib.inject(rig, w).R_lr)
        xl, yl, yr = vl[:, 0] / vl[:, 2], vl[:, 1] / vl[:, 2], vr[:, 1] / vr[:, 2]
        dy = rig.f_px * (yl - yr)
        sel = np.isfinite(dy) & (np.abs(dy) < 12)
        grid = np.full((len(ye) - 1, len(xe) - 1), np.nan)
        ix, iy = np.digitize(xl[sel], xe) - 1, np.digitize(yl[sel], ye) - 1
        for r in range(grid.shape[0]):
            for c in range(grid.shape[1]):
                m = (ix == c) & (iy == r)
                if m.sum() >= 30:
                    grid[r, c] = np.median(dy[sel][m])
        im = ax.pcolormesh(xe, ye, grid, cmap="PuOr", vmin=-4, vmax=4)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("x' = X/Z (rectified left ray)")
        ax.set_aspect("equal")
    axes[0].set_ylabel("y' = Y/Z")
    axes[0].invert_yaxis()
    cb = fig.colorbar(im, ax=axes, shrink=0.9, pad=0.02)
    cb.set_label("median vertical disparity dy (px)")
    fig.suptitle("Vertical disparity of real matches (NTNU underwater 2023 traj_06, 105-165 s): "
                 "x rotation adds a constant, z a gradient in x'", fontsize=10.5)
    save(fig, "fig4_vertical_disparity.png")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=ROOT / "cache")
    a = ap.parse_args()
    fig_warp()
    fig_window()
    fig_vio()
    fig_field(a.cache)
