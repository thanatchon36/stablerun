"""Figure F1 (baseline dynamics) and the fan-chart helper shared by other figures."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import style
from .style import PALETTE

style.apply()

SCENARIO_COLORS = {"control": PALETTE["black"], "loss05": PALETTE["sky"], "loss10": PALETTE["blue"],
                   "loss20": PALETTE["vermillion"], "scare08": PALETTE["green"]}
SCENARIO_LABELS = {"control": "No shock", "loss05": "5% loss", "loss10": "10% loss",
                   "loss20": "20% loss", "scare08": "8% exposure, resolved day 2"}


def fan(ax, t, arr, color, label=None, band=(5, 95), iqr=True, ls="-", lw=1.6):
    """Median line with a light 5-95% band and a darker interquartile band."""
    ax.plot(t, np.median(arr, axis=0), color=color, lw=lw, label=label, ls=ls, zorder=3)
    lo, hi = np.percentile(arr, band, axis=0)
    ax.fill_between(t, lo, hi, color=color, alpha=0.10, lw=0, zorder=2)
    if iqr:
        q1, q3 = np.percentile(arr, [25, 75], axis=0)
        ax.fill_between(t, q1, q3, color=color, alpha=0.22, lw=0, zorder=2)


def figure_f1(results: dict, out_stem: str | Path, stack_scenario: str = "loss10") -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.0))
    (a, b), (c, d) = axes
    for name, r in results.items():
        t = np.arange(r["T"] + 1)
        col, lab = SCENARIO_COLORS.get(name, "grey"), SCENARIO_LABELS.get(name, name)
        fan(a, t, r["price"], col, lab)
        fan(b, t, 100 * r["R"], col, lab)
        fan(c, t, r["Y"], col, lab)
    a.axhline(1.0, color=PALETTE["grey"], lw=0.6, ls=":", zorder=1)
    a.set(title="(a) Secondary price of the token", ylabel="USD per token", xlabel="Business day", ylim=(0.5, 1.03))
    a.legend(loc="lower center", fontsize=6.6, ncol=2, handlelength=1.6, columnspacing=1.0)
    b.set(title="(b) Cumulative redemptions", ylabel="% of initial supply", xlabel="Business day")
    c.set(title="(c) Three-month bill yield impact", ylabel="bp above the no-run path", xlabel="Business day")

    r = results[stack_scenario]
    t = np.arange(r["T"] + 1)
    cum = {k: np.cumsum(r[k].mean(axis=0)) for k in ["cash_used", "repo_used", "mmf_used", "tb1_sold", "tb3_sold", "other_sold"]}
    from_initial_cash = np.minimum(cum["cash_used"], r["cash0"])
    from_runoff = cum["cash_used"] - from_initial_cash
    sources = [(from_initial_cash, "Initial cash", PALETTE["black"]), (cum["repo_used"], "Reverse repo", PALETTE["sky"]),
               (cum["mmf_used"], "MMF shares", PALETTE["yellow"]), (from_runoff, "Maturing bills (run-off)", PALETTE["green"]),
               (cum["tb1_sold"], "Bills sold, $\\leq$1M", PALETTE["blue"]), (cum["tb3_sold"], "Bills sold, 1--3M", PALETTE["purple"]),
               (cum["other_sold"], "Other assets (haircut)", PALETTE["vermillion"])]
    d.stackplot(t, [s[0] for s in sources], labels=[s[1] for s in sources], colors=[s[2] for s in sources], alpha=0.9, lw=0)
    d.plot(t, np.cumsum(r["paid"].mean(axis=0)), color="white", lw=1.0, ls="--", label="Redemptions paid")
    d.set(title=f"(d) Cash sources, {SCENARIO_LABELS.get(stack_scenario, stack_scenario)} (mean path)",
          ylabel="USD bn, cumulative", xlabel="Business day")
    d.legend(loc="upper left", fontsize=6.3, ncol=2, handlelength=1.4, columnspacing=0.8)
    fig.tight_layout(w_pad=1.5, h_pad=1.2)
    return style.save(fig, out_stem)
