"""Figures F2 (tipping point), F3 (policy heatmaps), F5 (sensitivity tornado), F6 (benchmark check)."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import style
from .style import PALETTE

style.apply()


def figure_f2(df: pd.DataFrame, stem, thresholds=(10, 25, 50)):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.4), sharey=True)
    styles = {("sqrt", "calibrated"): (PALETTE["blue"], "-", "Square-root impact, calibrated rails (1.2%/day)"),
              ("sqrt", "fast"): (PALETTE["sky"], "-", "Square-root impact, fast rails (5%/day)"),
              ("sqrt", "instant"): (PALETTE["green"], "-", "Square-root impact, instant rails (20%/day)"),
              ("linear", "calibrated"): (PALETTE["vermillion"], "--", "Linear impact (upper bound), calibrated rails"),
              ("linear", "instant"): (PALETTE["orange"], "--", "Linear impact (upper bound), instant rails")}
    handles = []
    for ax, sc, title in [(axes[0], "scare", "(a) Liquidity run: 8% exposure, resolved day 2"),
                          (axes[1], "loss10", "(b) Solvency run: 10% of reserves lost")]:
        for (form, rails), (col, ls, lab) in styles.items():
            g = df[(df.scenario == sc) & (df.impact == form) & (df.rails == rails)].sort_values("size")
            if g.empty:
                continue
            h, = ax.plot(g["size"], g["peak_Y_bp_med"], color=col, ls=ls, marker="o", ms=3.5, mec="white", mew=0.6, lw=1.5, label=lab)
            ax.fill_between(g["size"], g["peak_Y_bp_p5"], g["peak_Y_bp_p95"], color=col, alpha=0.12, lw=0)
            if ax is axes[0]:
                handles.append(h)
        for thr in thresholds:
            ax.axhline(thr, color=PALETTE["grey"], lw=0.6, ls=":")
            ax.text(11.6, thr, f"{thr} bp", va="center", ha="right", fontsize=6.5, color=PALETTE["grey"],
                    bbox=dict(facecolor="white", edgecolor="none", pad=0.8))
        ax.set(xscale="log", yscale="log", xlabel="Issuer size relative to today", title=title,
               xticks=[1, 2, 3, 5, 10], xticklabels=["1$\\times$", "2$\\times$", "3$\\times$", "5$\\times$", "10$\\times$"], xlim=(0.9, 12))
        ax.set_yticks([5, 10, 25, 50, 100, 300, 600])
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.grid(True, axis="both", which="major")
        ax.minorticks_off()
    axes[0].set_ylabel("Peak three-month bill yield impact, bp")
    fig.legend(handles, [h.get_label() for h in handles], loc="lower center", ncol=2, fontsize=7, bbox_to_anchor=(0.5, -0.02))
    fig.tight_layout(rect=[0, 0.13, 1, 1], w_pad=1.5)
    return style.save(fig, stem)


def figure_f3(df: pd.DataFrame, stem, config="loss10_5x_fast"):
    """Top: peak impact (93-day cap) without/with backstop on a shared scale. Bottom: bills sold outright
    (no backstop) with the 93-day cap and with no cap."""
    g = df[(df.config == config) & (~df.cash_buffer.astype(str).isin(["par", "nav"]))].copy()
    g["cash_buffer"] = g["cash_buffer"].astype(float); g["fee"] = g["fee"].astype(float)
    g["maturity_cap"] = g["maturity_cap"].astype(str).str.replace(".0", "", regex=False)
    panels = [[("peak_Y_bp_med", "YlOrRd", "{:.0f}", g[(g.maturity_cap == "93") & (~g.backstop)], "(a) Peak bill yield impact, bp, no backstop"),
               ("peak_Y_bp_med", "YlOrRd", "{:.0f}", g[(g.maturity_cap == "93") & (g.backstop)], "(b) Peak bill yield impact, bp, with backstop")],
              [("bills_sold_med", "YlGnBu", "{:.0f}", g[(g.maturity_cap == "93") & (~g.backstop)], "(c) Bills sold outright, $bn, 93-day maturity cap"),
               ("bills_sold_med", "YlGnBu", "{:.0f}", g[(g.maturity_cap == "none") & (~g.backstop)], "(d) Bills sold outright, $bn, no maturity cap")]]
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.6), constrained_layout=True)
    for i, row in enumerate(panels):
        vmin = min(h[metric].min() for metric, _, _, h, _ in row); vmax = max(h[metric].max() for metric, _, _, h, _ in row)
        for j, (metric, cmap, fmt, h, title) in enumerate(row):
            piv = h.pivot(index="cash_buffer", columns="fee", values=metric).sort_index(ascending=False)
            ax = axes[i, j]
            im = ax.imshow(piv.values, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
            ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels([f"{c:.1%}" for c in piv.columns])
            ax.set_yticks(range(len(piv.index))); ax.set_yticklabels([f"{r:.0%}" for r in piv.index])
            ax.grid(False); ax.tick_params(length=0)
            for spine in ax.spines.values():
                spine.set_visible(False)
            thresh = vmin + 0.55 * (vmax - vmin)
            for (r, c), v in np.ndenumerate(piv.values):
                ax.text(c, r, fmt.format(v), ha="center", va="center", fontsize=7.5, color="white" if v > thresh else "#222222")
            ax.set_title(title, fontsize=8.3); ax.set_xlabel("Redemption fee")
            if j == 0:
                ax.set_ylabel("Minimum cash buffer")
        fig.colorbar(im, ax=axes[i, :].tolist(), shrink=0.85, pad=0.02,
                     format=matplotlib.ticker.FuncFormatter(lambda x, _, f=row[0][2]: f.format(x)))
    return style.save(fig, stem)


def figure_f5(df: pd.DataFrame, stem):
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 4.0))
    panels = [("loss10_5x_fast", "peak_Y_bp_med", "(a) Peak bill yield impact, bp\n(solvency run, 5$\\times$ size, fast rails)", "{:.0f}"),
              ("scare_1x_calibrated", "R_end_med", "(b) Redeemed by day 30\n(liquidity run, today's size)", "{:.0%}")]
    for ax, (cname, metric, title, fmt) in zip(axes, panels):
        g = df[(df.config == cname) & (df.metric == metric)].copy()
        g["span"] = (g["high"] - g["low"]).abs()
        g = g.sort_values("span").reset_index(drop=True)
        base = g["base"].iloc[0]
        y = np.arange(len(g))
        ax.barh(y, g["low"] - base, left=base, color=PALETTE["sky"], height=0.62, label="Low parameter value")
        ax.barh(y, g["high"] - base, left=base, color=PALETTE["vermillion"], height=0.62, label="High parameter value")
        ax.axvline(base, color="#222222", lw=0.8)
        import re
        pretty = {"rho": "$\\rho$", "psi": "$\\psi$", "eta": "$\\eta$", "w3": "$w_3$", "w1": "$w_1$", "K": "$K$", "N": "$N$"}
        labels = [re.sub(r"\bx(?=\d)", "$\\times$", lab) for lab in g["parameter"]]
        labels = [" ".join(pretty.get(w, w) for w in lab.split(" ")) for lab in labels]
        ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7)
        ax.set_title(title, fontsize=8.5)
        ax.grid(True, axis="x"); ax.grid(False, axis="y")
        ax.set_xlabel(f"Metric value (baseline {fmt.format(base)})")
        if metric == "R_end_med":
            ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    axes[0].legend(loc="lower right", fontsize=7)
    fig.tight_layout(w_pad=2.0)
    return style.save(fig, stem)


def figure_f6(df: pd.DataFrame, stem):
    fig, ax = plt.subplots(figsize=(3.6, 2.8))
    ax.plot(100 * df["exposure"], 100 * df["closed_form_exit_share"], color=PALETTE["vermillion"], lw=1.6, label="Closed-form threshold aggregate")
    ax.plot(100 * df["exposure"], 100 * df["abm_exit_share"], "o", color=PALETTE["blue"], ms=4, mec="white", mew=0.6, label="Simulation, behavioural channels off")
    ax.set(xlabel="Loss share of reserves, %", ylabel="Share of supply exiting, %")
    ax.legend(fontsize=6.8, loc="lower right")
    fig.tight_layout()
    return style.save(fig, stem)
