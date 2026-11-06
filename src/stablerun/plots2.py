"""Figures F2 (tipping point), F3 (policy heatmaps), F5 (sensitivity tornado), F6 (benchmark check)."""
from __future__ import annotations

import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, PercentFormatter

from . import style
from .style import INK, INK_2, PALETTE, panel_title, text_colour_on

style.apply()

# F2 encoding: colour = processing rails, line style = price-impact form.
RAILS = [("calibrated", PALETTE["blue"], "Calibrated, 1.2% of supply per day"),
         ("fast", PALETTE["sky"], "Fast, 5% per day"),
         ("instant", PALETTE["green"], "Instant, 20% per day")]
FORMS = [("sqrt", "-", "Square root (baseline)"), ("linear", (0, (4, 2)), "Linear (upper bound)")]


def figure_f2(df: pd.DataFrame, stem, thresholds=(10, 25, 50)):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.9), sharey=True)
    for ax, sc, letter, title in [(axes[0], "scare", "a", "Liquidity run: 8% exposure, resolved day 2"),
                                  (axes[1], "loss10", "b", "Solvency run: 10% of reserves lost")]:
        for thr in thresholds:
            ax.axhline(thr, color=INK_2, lw=0.7, ls=(0, (1, 2.5)), zorder=1)
        for form, ls, _ in FORMS:
            for rails, col, _ in RAILS:
                g = df[(df.scenario == sc) & (df.impact == form) & (df.rails == rails)].sort_values("size")
                if g.empty:
                    continue
                ax.fill_between(g["size"], g["peak_Y_bp_p5"], g["peak_Y_bp_p95"], color=col, alpha=0.12, lw=0, zorder=2)
                ax.plot(g["size"], g["peak_Y_bp_med"], color=col, ls=ls, marker="o", ms=3.5, mec="white", mew=0.6,
                        lw=1.5, zorder=3)
        panel_title(ax, letter, title)
        ax.set(xscale="log", yscale="log", xlabel="Issuer size relative to today", xlim=(0.9, 11.5))
        ax.set_xticks([1, 2, 3, 5, 10], [f"{s}$\\times$" for s in [1, 2, 3, 5, 10]])
        ax.set_yticks([5, 10, 25, 50, 100, 200, 500, 1000])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, axis="both", which="major")
        ax.minorticks_off()
    axes[0].set_ylabel("Peak three-month bill-yield impact, bp")
    axes[0].set_ylim(4, 1000)
    rails_h = [Line2D([], [], color=col, marker="o", mec="white", mew=0.6, ms=3.5, lw=1.5) for _, col, _ in RAILS]
    form_h = [Line2D([], [], color=INK, ls=ls, lw=1.5) for _, ls, _ in FORMS]
    kw = dict(loc="upper left", alignment="left", title_fontproperties={"weight": "bold", "size": 8}, fontsize=7.8,
              handlelength=2.4, labelspacing=0.3)
    fig.legend(rails_h, [lab for *_, lab in RAILS], title="Processing rails (colour)", bbox_to_anchor=(0.07, 0.165), **kw)
    fig.legend(form_h, [lab for *_, lab in FORMS], title="Price impact (line style)", bbox_to_anchor=(0.56, 0.165), **kw)
    fig.tight_layout(rect=[0, 0.17, 1, 1], w_pad=1.5)
    return style.save(fig, stem)


def _ramp(name: str, lo: float = 0.08, hi: float = 0.9) -> LinearSegmentedColormap:
    """A muted single-hue ramp: the named colormap without its white and near-black ends."""
    base = matplotlib.colormaps[name]
    return LinearSegmentedColormap.from_list(f"{name}_muted", base(np.linspace(lo, hi, 256)))


def figure_f3(df: pd.DataFrame, stem, config="loss10_5x_fast"):
    """Top: peak impact (93-day cap) without/with backstop on a shared scale. Bottom: bills sold outright
    (no backstop) with the 93-day cap and with no cap."""
    g = df[(df.config == config) & (~df.cash_buffer.astype(str).isin(["par", "nav"]))].copy()
    g["cash_buffer"] = g["cash_buffer"].astype(float)
    g["fee"] = g["fee"].astype(float)
    g["maturity_cap"] = g["maturity_cap"].astype(str).str.replace(".0", "", regex=False)
    cap93, nocap, bs = g.maturity_cap == "93", g.maturity_cap == "none", g.backstop.astype(bool)
    rows = [("peak_Y_bp_med", _ramp("Oranges"), "Peak three-month yield impact, bp",
             [(cap93 & ~bs, "a", "Peak yield impact, no backstop"), (cap93 & bs, "b", "Peak yield impact, with Fed backstop")]),
            ("bills_sold_med", _ramp("Blues"), "Bills sold outright, $bn",
             [(cap93 & ~bs, "c", "Bills sold outright, 93-day maturity cap"), (nocap & ~bs, "d", "Bills sold outright, no maturity cap")])]
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.7), constrained_layout=True)
    for i, (metric, cmap, cbar_label, panels) in enumerate(rows):
        pivs = [g[mask].pivot(index="cash_buffer", columns="fee", values=metric).sort_index(ascending=False) for mask, _, _ in panels]
        norm = Normalize(min(p.values.min() for p in pivs), max(p.values.max() for p in pivs))
        for j, (piv, (_, letter, title)) in enumerate(zip(pivs, panels)):
            ax = axes[i, j]
            im = ax.imshow(piv.values, cmap=cmap, norm=norm, aspect="equal")
            ax.set_xticks(range(len(piv.columns)), [f"{c:.1%}" for c in piv.columns])
            ax.set_yticks(range(len(piv.index)), [f"{r:.0%}" for r in piv.index])
            ax.set_xticks(np.arange(-0.5, len(piv.columns)), minor=True)
            ax.set_yticks(np.arange(-0.5, len(piv.index)), minor=True)
            ax.grid(False)
            ax.grid(True, which="minor", axis="both", color="white", lw=1.6)
            ax.tick_params(which="both", length=0)
            for spine in ax.spines.values():
                spine.set_visible(False)
            for (r, c), v in np.ndenumerate(piv.values):
                ax.text(c, r, f"{v:.0f}", ha="center", va="center", fontsize=8, color=text_colour_on(cmap(norm(v))))
            panel_title(ax, letter, title)
            ax.set_xlabel("Redemption fee")
            if j == 0:
                ax.set_ylabel("Minimum cash buffer")
        cb = fig.colorbar(im, ax=axes[i, :].tolist(), shrink=0.82, pad=0.02, label=cbar_label)
        cb.outline.set_visible(False)
        cb.ax.tick_params(length=0)
    return style.save(fig, stem)


def _pretty_parameter(label: str) -> str:
    label = re.sub(r"\bx(?=\d)", lambda m: "$\\times$", label)
    greek = {"rho": "$\\rho$", "psi": "$\\psi$", "eta": "$\\eta$", "w3": "$w_3$", "w1": "$w_1$", "K": "$K$", "N": "$N$"}
    return " ".join(greek.get(w, w) for w in label.split(" "))


def figure_f5(df: pd.DataFrame, stem):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 4.4))
    panels = [("loss10_5x_fast", "peak_Y_bp_med", "a", "Peak bill-yield impact", "solvency run, 5$\\times$ size, fast rails",
               "Peak three-month yield impact, bp", lambda v: f"{v:.0f} bp"),
              ("scare_1x_calibrated", "R_end_med", "b", "Redeemed by day 30", "liquidity run, today's size",
               "Share of supply redeemed by day 30", lambda v: f"{v:.0%}")]
    for ax, (cname, metric, letter, title, sub, xlabel, fmt) in zip(axes, panels):
        g = df[(df.config == cname) & (df.metric == metric)].copy()
        g["span"] = (g["high"] - g["low"]).abs()
        g = g.sort_values("span").reset_index(drop=True)
        base = float(g["base"].iloc[0])
        y = np.arange(len(g))
        ax.barh(y, g["low"] - base, left=base, color=PALETTE["sky"], height=0.66, zorder=3)
        ax.barh(y, g["high"] - base, left=base, color=PALETTE["vermillion"], height=0.66, zorder=3)
        none = g["span"] <= 1e-3 * max(abs(base), 1e-9)
        ax.plot(np.full(none.sum(), base), y[none.values], ls="none", marker="o", mfc="white", mec=INK_2, ms=4, mew=0.8, zorder=4)
        ax.axvline(base, color=INK, lw=0.8, zorder=2)
        ax.set_yticks(y, [_pretty_parameter(lab) for lab in g["parameter"]], fontsize=7.6)
        ax.set_ylim(-0.7, len(g) - 0.3)
        panel_title(ax, letter, title, sub=sub)
        ax.grid(True, axis="x")
        ax.grid(False, axis="y")
        ax.set_xlabel(f"{xlabel}\n(baseline {fmt(base)})")
        if metric == "R_end_med":
            ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    handles = [Patch(color=PALETTE["sky"]), Patch(color=PALETTE["vermillion"]),
               Line2D([], [], marker="o", mfc="white", mec=INK_2, ms=4, mew=0.8, lw=0)]
    fig.legend(handles, ["Low parameter value", "High parameter value", "No measurable effect"],
               loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0), fontsize=7.8, handlelength=1.6)
    fig.tight_layout(rect=[0, 0, 1, 0.95], w_pad=2.0)
    return style.save(fig, stem)


def figure_f6(df: pd.DataFrame, stem, cfg: dict | None = None):
    fig, ax = plt.subplots(figsize=(3.6, 2.9))
    if cfg is not None:  # the closed form on a fine grid; the CSV holds it only at the simulated points
        from scipy.stats import norm
        h = cfg["holders"]
        xs = np.linspace(0, float(df["exposure"].max()), 200)
        closed = sum(h["type_shares"][t] * norm.cdf((xs - h["thresholds"][t]["mean"])
                                                    / np.sqrt(h["signal_noise_sigma"] ** 2 + h["thresholds"][t]["sd"] ** 2))
                     for t in h["type_shares"])
        ax.plot(xs, closed, color=PALETTE["vermillion"], lw=1.6, label="Closed-form threshold aggregate", zorder=2)
    else:
        ax.plot(df["exposure"], df["closed_form_exit_share"], color=PALETTE["vermillion"], lw=1.6,
                label="Closed-form threshold aggregate", zorder=2)
    ax.plot(df["exposure"], df["abm_exit_share"], ls="none", marker="o", color=PALETTE["blue"], ms=4.5, mec="white",
            mew=0.7, label="Simulation, behavioural channels off", zorder=3)
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set(xlabel="Loss share of reserves", ylabel="Share of supply exiting", ylim=(0, 1.02))
    ax.legend(loc="lower right", fontsize=7.5)
    fig.tight_layout()
    return style.save(fig, stem)
