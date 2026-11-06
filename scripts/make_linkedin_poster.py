#!/usr/bin/env python3
"""Portrait LinkedIn poster (4:5, 2160 x 2700 px) for the working paper.

Every number is read from results/tables or recomputed with the paper's own configuration and seed, so the poster
cannot disagree with the paper. Writes docs/assets/linkedin_poster.png.

Design: a dark title band with gold accents for the three headline numbers, an ivory body in the paper's Pagella
type and Okabe-Ito series colours (vermillion = solvency run, blue = liquidity run; validated with the dataviz
palette checker on the ivory surface), and a dark footer with the links.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from PIL import Image  # noqa: E402

from stablerun import style  # noqa: E402
from stablerun.config import load_config  # noqa: E402
from stablerun.simulate import simulate  # noqa: E402

style.apply()
matplotlib.rcParams["savefig.bbox"] = None  # the house style crops tight; the poster keeps its full canvas

W, H = 10.8, 13.5                  # inches; 2160 x 2700 px at 200 dpi
NIGHT, GOLD = "#15171c", "#e2b04a"
IVORY, IVORY_2 = "#f6f1e7", "#c9c3b5"
PAPER, CARD = "#faf7f0", "#ffffff"
INK, INK_2, MUTED = "#17191e", "#464a52", "#7c7f87"
RULE, GRID = "#d9d3c6", "#e8e3d8"
BRONZE = "#8a6212"                 # accent type on the ivory body
VERM, BLUE = "#D55E00", "#0072B2"
L, R = 0.6, W - 0.6                # side margins

# ------------------------------------------------------------------ data
T = ROOT / "results" / "tables"
e1 = pd.read_csv(T / "E1_A_summary.csv", index_col=0)
e2 = pd.read_csv(T / "E2_tipping_point.csv")
cr = pd.read_csv(T / "E2_crossings.csv")
e3 = pd.read_csv(T / "E3_policy_grid.csv")
e4 = pd.read_csv(T / "E4_contagion.csv")
e5 = pd.read_csv(T / "E5_sensitivity.csv")
bench = pd.read_csv(T / "benchmark_check.csv")


def num(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def crossing(sc: str, thr: int) -> float:
    row = cr[(cr.scenario == sc) & (cr.impact == "sqrt") & (cr.rails == "calibrated")].iloc[0]
    return float(row[f"size_{thr}bp"].rstrip("x"))


peak = e1.loc["loss10", "peak_Y_bp_med"]
sold = e1.loc[["loss05", "loss10", "loss20", "scare08"], "bills_sold_med"].max()
assert sold < 0.5, sold
not_rolled = e1.loc["loss10", "withdrawn_med"]
c25 = (crossing("loss10", 25), crossing("scare", 25))
c50 = (crossing("loss10", 50), crossing("scare", 50))

# Monte Carlo paths behind the published results, with the per-cell counts that run_all.py uses
e1_paths = sum(len(pd.read_csv(T / f"E1_{i}_{s}_paths.csv", usecols=[0]))
               for i in "AB" for s in ["control", "loss05", "loss10", "loss20", "scare08"])
n_paths = (e1_paths + 300 * len(e2) + 200 * len(e3) + 300 * (len(e4) + e4.scenario_A.nunique())
           + 200 * (2 * len(e5) + e5.config.nunique()) + 100 * len(bench) + 300 * 2)
assert n_paths == 83_500, n_paths

# E3 main effects for the solvency run at five times today's size with fast rails (as in the paper's Table 6)
SOLV = "loss10_5x_fast"
basis = e3[e3.cash_buffer.isin(["par", "nav"]) & (e3.config == SOLV)].set_index("cash_buffer")
grid = e3[~e3.cash_buffer.isin(["par", "nav"]) & (e3.config == SOLV)].copy()
grid["cash_buffer"] = grid.cash_buffer.astype(float)


def main_effect(lever: str, level, col: str) -> float:
    return grid[grid[lever].astype(str) == str(level)][col].mean()


levers = [
    ("Cash buffers protect the Treasury market",
     f"30% in cash: impact {main_effect('cash_buffer', 0.0, 'peak_Y_bp_med'):.0f} → {main_effect('cash_buffer', 0.3, 'peak_Y_bp_med'):.0f} bp;"
     f" bills sold ${main_effect('cash_buffer', 0.0, 'bills_sold_med'):.0f} bn → ${main_effect('cash_buffer', 0.3, 'bills_sold_med'):.0f}"),
    ("Maturity caps turn sales into non-rollover",
     f"93-day cap: bills sold ${main_effect('maturity_cap', 'none', 'bills_sold_med'):.0f} bn → ${main_effect('maturity_cap', '93', 'bills_sold_med'):.0f} bn"),
    ("NAV redemption protects holders",
     f"Pay out at net asset value, not par: trough ${basis.loc['par', 'min_price_med']:.2f} → ${basis.loc['nav', 'min_price_med']:.2f}"),
    ("Fees barely matter",
     f"Up to 2%: impact {main_effect('fee', 0.0, 'peak_Y_bp_med'):.0f} → {main_effect('fee', 0.02, 'peak_Y_bp_med'):.0f} bp; redemptions unchanged"),
]

# one run, day by day: the paper's E1 solvency run on Issuer A, same configuration and seed as Figure 1
cfg = load_config()
shock = next(s for s in cfg["shocks"]["e1_scenarios"] if s["name"] == "loss10")
run = simulate(cfg, shock, issuer="A")
assert abs(np.median(run["price"].min(axis=1)) - e1.loc["loss10", "min_price_med"]) < 1e-9
cap_share = cfg["issuers"]["A"]["redemption"]["processing_cap_share_per_day"]

# ------------------------------------------------------------------ canvas in inches from the top-left corner
fig = plt.figure(figsize=(W, H), facecolor=PAPER)
cv = fig.add_axes([0, 0, 1, 1], zorder=0)
cv.set_xlim(0, W)
cv.set_ylim(H, 0)
cv.axis("off")


def text(x, y, s, size, color=INK, weight="normal", ha="left", va="top", **kw):
    return cv.text(x, y, s, fontsize=size, color=color, fontweight=weight, ha=ha, va=va, parse_math=False, **kw)


def lines(x, y0, s, size, color, pitch, **kw):
    """Multi-line text on a fixed baseline grid, so that tall glyphs such as $ do not change the line spacing."""
    for k, line in enumerate(s.split("\n")):
        text(x, y0 + k * pitch, line, size, color, va="baseline", **kw)


def caps(s: str) -> str:
    """Tracked capitals: thin spaces between letters."""
    return " ".join(s.upper())


def hline(y, x0=L, x1=R, color=RULE, lw=0.8, **kw):
    cv.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="butt", **kw)


def axes_in(x, y_top, w, h, **kw):
    return fig.add_axes([x / W, 1 - (y_top + h) / H, w / W, h / H], facecolor=PAPER, zorder=2, **kw)


def kicker(x, y, n, title):
    text(x, y, n, 13, BRONZE, "bold", va="baseline")
    text(x + 0.42, y, caps(title), 12.5, INK, "bold", va="baseline")


def tidy(ax, ylabel_fmt=None):
    for name, sp in ax.spines.items():
        sp.set_visible(name in ("left", "bottom"))
        sp.set_color(RULE)
    ax.tick_params(colors=INK_2, labelsize=10.5, length=0, pad=5)
    ax.grid(True, axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    if ylabel_fmt:
        ax.yaxis.set_major_formatter(FuncFormatter(ylabel_fmt))


# ------------------------------------------------------------------ title band
HERO = 4.75
cv.add_patch(Rectangle((0, 0), W, HERO, color=NIGHT, zorder=0))
text(L, 0.4, caps("Working paper") + "   ·   " + caps("November 2026"), 10.5, GOLD, va="center")
text(R, 0.4, caps("Thanatchon Chongmankhong"), 10.5, GOLD, ha="right", va="center")
hline(0.62, color=GOLD, lw=0.9, alpha=0.55)
text(L - 0.04, 0.86, "When Stablecoins Run", 62, IVORY, "bold")
text(L, 1.93, "An agent-based stress test of how a stablecoin run reaches the US Treasury bill market,\n"
              "calibrated to the USDC (March 2023) and USDT (May 2022) episodes", 15.5, IVORY_2, linespacing=1.4)
text(L, 2.83, f"10,000 holders   ·   {n_paths:,} Monte Carlo paths   ·   5 experiments   ·   open code, data and DOI",
     11.5, GOLD, va="center", style="italic")

heroes = [
    (f"{peak:.0f} bp", "peak rise in three-month bill yields\nwhen an issuer the size of today's\nlargest loses 10% of its reserves"),
    (f"${sold:.0f}", "of bills sold in a fire sale. Instead,\n"
                     f"${not_rolled:.0f} bn of maturing bills are simply\nnot rolled over at auction"),
    (f"{num(c25[0])}–{num(c25[1])}×", "today's size at which a run lifts bill\n"
                                       f"yields by 25 bp, and 50 bp at {num(c50[0])}–{num(c50[1])}×.\nUnder linear impact: already today"),
]
col_w = (R - L) / 3
for i, (big, cap) in enumerate(heroes):
    x = L + i * col_w + (0 if i == 0 else 0.3)
    if i:
        cv.plot([L + i * col_w, L + i * col_w], [3.2, 4.45], color=IVORY, lw=0.6, alpha=0.22)
    text(x, 3.66, big, 46, GOLD, "bold", va="baseline")
    lines(x, 3.98, cap, 12, IVORY, 0.225, alpha=0.92)

# ------------------------------------------------------------------ 01 inside the model
y = 5.22
kicker(L, y, "01", "Inside the model")
nodes = [("Holders", "10,000 agents react to\nprivate signals, the\ndepeg and each other"),
         ("Secondary market", "arbitrageurs buy\ntokens at a discount\nand redeem at par"),
         ("Redemption queue", f"processing capacity\ncaps payouts at {cap_share:.1%}\nof supply a day"),
         ("Issuer", "pays from cash, repo,\nfund shares, maturing\nbills, then sales"),
         ("T-bill market", "absorbs outright sales\nand withdrawn auction\ndemand: yields rise")]
gap = 0.26
bw = (R - L - gap * (len(nodes) - 1)) / len(nodes)
top, bh = 5.4, 0.98
for i, (name, cap) in enumerate(nodes):
    x = L + i * (bw + gap)
    last = i == len(nodes) - 1
    cv.add_patch(FancyBboxPatch((x, top), bw, bh, boxstyle="round,pad=0,rounding_size=0.09",
                                fc=NIGHT if last else CARD, ec=NIGHT if last else RULE, lw=0.9, zorder=1))
    text(x + 0.13, top + 0.13, name, 12, GOLD if last else INK, "bold", zorder=2)
    text(x + 0.13, top + 0.4, cap, 9.5, IVORY_2 if last else INK_2, linespacing=1.3, zorder=2)
    if not last:
        cv.add_patch(FancyArrowPatch((x + bw + 0.04, top + bh / 2), (x + bw + gap - 0.04, top + bh / 2),
                                     arrowstyle="-|>", mutation_scale=13, color=MUTED, lw=1.1, zorder=1))

# ------------------------------------------------------------------ 02 one run, day by day
y = 6.85
kicker(L, y, "02", "One run, day by day")
text(L, y + 0.13, "An issuer the size of today's largest loses 10% of its reserves. "
                  "Median of 1,000 paths with the 5–95% band.", 11, INK_2)
t = np.arange(run["price"].shape[1])
panels = [("Token price", run["price"], lambda v, _: f"${v:.2f}", (0.74, 1.02), [0.8, 0.9, 1.0], lambda v: f"${v:.2f}"),
          ("Supply redeemed", 100 * run["R"], lambda v, _: f"{v:.0f}%", (0, 42), [0, 10, 20, 30, 40], lambda v: f"{v:.0f}%"),
          ("Rise in 3-month bill yields, bp", run["Y"], lambda v, _: f"{v:.0f}", (0, 25), [0, 5, 10, 15, 20, 25],
           lambda v: f"{v:.0f} bp")]
pw, pg = 2.72, 0.62
for i, (title, arr, fmt, ylim, ticks, endfmt) in enumerate(panels):
    x = L + 0.5 + i * (pw + pg)
    ax = axes_in(x, 7.68, pw, 1.12)
    med = np.median(arr, axis=0)
    lo, hi = np.percentile(arr, [5, 95], axis=0)
    ax.fill_between(t, lo, hi, color=VERM, alpha=0.16, lw=0)
    ax.plot(t, med, color=VERM, lw=2.2, solid_capstyle="round")
    ax.plot(t[-1], med[-1], "o", color=VERM, ms=6.5, mec=PAPER, mew=1.4, zorder=4, clip_on=False)
    ax.set(xlim=(0, 30), ylim=ylim, yticks=ticks, xticks=[0, 10, 20, 30])
    tidy(ax, fmt)
    ax.set_xlabel("Business day", fontsize=10.5, color=INK_2, labelpad=3)
    ax.annotate(endfmt(med[-1]), (t[-1], med[-1]), xytext=(-6, 9), textcoords="offset points",
                ha="right", va="bottom", fontsize=13, fontweight="bold", color=INK)
    text(x - 0.5, 7.36, title, 12, INK, "bold")

# ------------------------------------------------------------------ 03 size is the problem
y = 9.56
kicker(L, y, "03", "Size is the problem")
ax = axes_in(L + 0.55, 10.06, 4.35, 1.95)
for sc, col, label in [("loss10", VERM, "Solvency run: 10% of reserves lost"),
                       ("scare", BLUE, "Liquidity run: scare resolved on day 2")]:
    g = e2[(e2.scenario == sc) & (e2.impact == "sqrt") & (e2.rails == "calibrated")].sort_values("size")
    ax.fill_between(g["size"], g["peak_Y_bp_p5"], g["peak_Y_bp_p95"], color=col, alpha=0.14, lw=0)
    ax.plot(g["size"], g["peak_Y_bp_med"], color=col, lw=2.2, marker="o", ms=5.5, mec=PAPER, mew=1.2, zorder=3)
    ax.plot([], [], color=col, lw=2.2, label=label)
for thr in (25, 50):
    ax.axhline(thr, color=INK_2, lw=0.8, ls=(0, (2, 3)), zorder=1)
    ax.text(1.015, thr, f"{thr} bp", color=INK_2, fontsize=10, ha="left", va="center",
            transform=ax.get_yaxis_transform(), clip_on=False)
for xs, thr in [(c25[0], 25), (c50[0], 50)]:
    ax.plot(xs, thr, "o", ms=8, mfc="none", mec=INK, mew=1.2, zorder=4)
    ax.annotate(f"{num(xs)}×", (xs, thr), xytext=(-7, 6), textcoords="offset points", ha="right", va="bottom",
                fontsize=11, fontweight="bold", color=INK)
ax.set(xscale="log", yscale="log", xlim=(0.92, 11), ylim=(12, 95))
ax.set_xticks([1, 2, 3, 5, 10], ["1×", "2×", "3×", "5×", "10×"])
ax.set_yticks([15, 25, 50, 80])
ax.minorticks_off()
tidy(ax, lambda v, _: f"{v:g}")
ax.set_xlabel("Issuer size relative to today's largest", fontsize=10.5, color=INK_2, labelpad=4)
ax.set_ylabel("Peak rise in 3-month bill yields, bp", fontsize=10.5, color=INK_2, labelpad=4)
ax.legend(loc="lower right", fontsize=10, frameon=False, handlelength=1.5, borderaxespad=0.3, labelcolor=INK_2)
text(L, 9.69, "Square-root price impact; circles mark where the solvency run crosses 25 and 50 bp.", 10, INK_2)

# ------------------------------------------------------------------ 04 what works
x0 = 6.15
kicker(x0, y, "04", "What works")
text(x0, 9.69, "Solvency run at 5× today's size, fast redemption rails.", 10, INK_2)
ry = 10.16
for name, effect in levers:
    hline(ry - 0.13, x0, R)
    text(x0, ry, name, 12, INK, "bold")
    text(x0, ry + 0.27, effect, 10.3, INK_2)
    ry += 0.6
hline(ry - 0.13, x0, R)

# ------------------------------------------------------------------ footer
F = 12.68
cv.add_patch(Rectangle((0, F), W, H - F, color=NIGHT, zorder=0))
text(L, F + 0.2, "Thanatchon Chongmankhong", 15, IVORY, "bold")
text(L, F + 0.5, "Working paper, November 2026. A stress-testing tool, not a forecast.", 10.5, IVORY_2)
links = [("CODE", "github.com/thanatchon36/stablerun"), ("DOI", "10.5281/zenodo.23996044"),
         ("DATA", "huggingface.co/datasets/thanatchon36/stablerun")]
for j, (k, v) in enumerate(links):
    yy = F + 0.17 + j * 0.17
    text(6.05, yy, caps(k), 8.5, GOLD, "bold", va="top")
    text(6.75, yy - 0.01, v, 10.5, IVORY, va="top")

out = ROOT / "docs" / "assets" / "linkedin_poster.png"
fig.savefig(out, dpi=200, facecolor=PAPER)
Image.open(out).convert("RGB").save(out, optimize=True)  # opaque RGB PNG for LinkedIn
print(out, f"{n_paths:,} paths")
