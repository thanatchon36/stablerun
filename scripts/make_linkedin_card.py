#!/usr/bin/env python3
"""The 1200x675 image that goes with the LinkedIn post: headline, three numbers and the tipping-point chart,
all drawn from results/tables so that the card never disagrees with the paper. Writes docs/assets/linkedin_card.png.

Light, paper-like card: off-white surface, near-black type, one navy accent for the headline numbers, and the
paper's own Okabe-Ito blue and vermillion for the two series (validated with the dataviz palette checker).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from stablerun import style  # noqa: E402

style.apply()
BG, PANEL, RULE = "#fbfaf7", "#ffffff", "#d9d5cc"
INK, INK_2, MUTED, GRID = "#1a1a1a", "#4a4a4a", "#7a7a7a", "#e6e3dc"
NAVY, BLUE, VERMILLION = "#12233f", "#0072B2", "#D55E00"

T = ROOT / "results" / "tables"
e1 = pd.read_csv(T / "E1_A_summary.csv", index_col=0)
e2 = pd.read_csv(T / "E2_tipping_point.csv")
cr = pd.read_csv(T / "E2_crossings.csv")


def crossing(sc, thr):
    return cr[(cr.scenario == sc) & (cr.impact == "sqrt") & (cr.rails == "calibrated")].iloc[0][f"size_{thr}bp"].rstrip("x")


peak = e1.loc["loss10", "peak_Y_bp_med"]
bills = e1.loc[["loss05", "loss10", "loss20", "scare08"], "bills_sold_med"].max()
x25 = f"{crossing('loss10', 25)}–{crossing('scare', 25)}×"
x50 = f"{crossing('loss10', 50)}–{crossing('scare', 50)}×"

fig = plt.figure(figsize=(12, 6.75), facecolor=BG)
# top rule and kicker
fig.add_artist(Line2D([0.045, 0.955], [0.945, 0.945], transform=fig.transFigure, color=NAVY, lw=2.5))
fig.text(0.045, 0.905, "WORKING PAPER  ·  NOVEMBER 2026", color=MUTED, fontsize=10, va="top")
fig.text(0.955, 0.905, "github.com/thanatchon36/stablerun", color=MUTED, fontsize=10, va="top", ha="right")
fig.text(0.045, 0.83, "When Stablecoins Run", color=NAVY, fontsize=36, weight="bold", va="top")
fig.text(0.045, 0.725, "An agent-based stress test of fire-sale spillovers\nfrom stablecoin redemptions to the Treasury bill market",
         color=INK_2, fontsize=14, va="top", linespacing=1.3)

# three headline numbers, separated by thin rules
tiles = [(f"≈{peak:.0f} bp", "peak three-month bill-yield impact of a run on an\nissuer the size of today's largest"),
         (f"${bills:.0f} bn", "of bills sold outright: the market loses a buyer at\nauction, not a seller in a fire sale"),
         (x25, f"today's size at which the 25 bp mark is crossed;\nthe 50 bp mark at {x50}")]
y0, step = 0.575, 0.155
for i, (num, text) in enumerate(tiles):
    y = y0 - i * step
    fig.add_artist(Line2D([0.045, 0.50], [y, y], transform=fig.transFigure, color=RULE, lw=0.8))
    fig.text(0.045, y - 0.075, num, color=NAVY, fontsize=28, weight="bold", va="center", ha="left")
    fig.text(0.205, y - 0.075, text, color=INK_2, fontsize=11.5, va="center", ha="left", linespacing=1.3)

# the chart
ax = fig.add_axes([0.60, 0.18, 0.355, 0.56], facecolor=BG)
series = [("loss10", VERMILLION, "Solvency run: 10% of reserves lost"), ("scare", BLUE, "Liquidity run: 8% exposure, resolved day 2")]
for i, (sc, col, label) in enumerate(series):
    g = e2[(e2.scenario == sc) & (e2.impact == "sqrt") & (e2.rails == "calibrated")].sort_values("size")
    ax.fill_between(g["size"], g["peak_Y_bp_p5"], g["peak_Y_bp_p95"], color=col, alpha=0.12, lw=0)
    ax.plot(g["size"], g["peak_Y_bp_med"], color=col, lw=2.2, marker="o", ms=6, mec=BG, mew=1.2, zorder=3)
    ax.plot([], [], color=col, lw=2.2, label=label)
ax.legend(loc="upper left", fontsize=10, frameon=False, handlelength=1.6, borderaxespad=0.2, labelcolor=INK_2)
for thr in (25, 50):
    ax.axhline(thr, color=MUTED, lw=0.8, ls=(0, (2, 3)), zorder=1)
    ax.text(0.95, thr * 1.03, f"{thr} bp", color=MUTED, fontsize=9, va="bottom", ha="left")
ax.set(xscale="log", yscale="log", xlim=(0.9, 11), ylim=(12, 90))
ax.set_xticks([1, 2, 3, 5, 10], ["1×", "2×", "3×", "5×", "10×"])
ax.set_yticks([15, 25, 50, 80])
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
ax.minorticks_off()
ax.grid(True, axis="y", color=GRID, lw=0.6)
ax.tick_params(colors=INK_2, labelsize=10, length=0)
for name, s in ax.spines.items():
    s.set_color(RULE)
    s.set_visible(name in ("left", "bottom"))
ax.set_xlabel("Issuer size relative to today", color=INK_2, fontsize=11)
ax.set_ylabel("Peak three-month bill-yield impact, bp", color=INK_2, fontsize=11)
ax.set_title("Peak yield impact against issuer size\nsquare-root price impact, calibrated rails; bands 5–95%",
             color=INK, fontsize=12, loc="left", linespacing=1.3, pad=10)

# footer
fig.add_artist(Line2D([0.045, 0.955], [0.095, 0.095], transform=fig.transFigure, color=RULE, lw=0.8))
fig.text(0.045, 0.055, "Calibrated to USDC (March 2023) and USDT (May 2022). Paper, code and every table and figure reproducible in one command.",
         color=INK_2, fontsize=10.5, va="center")
fig.text(0.955, 0.055, "Thanatchon Chongmankhong", color=NAVY, fontsize=11, weight="bold", va="center", ha="right")

out = ROOT / "docs" / "assets" / "linkedin_card.png"
matplotlib.rcParams["savefig.bbox"] = None  # the house style crops tight; the card keeps its full 16:9 canvas
fig.savefig(out, dpi=200, facecolor=BG)
print(out)
