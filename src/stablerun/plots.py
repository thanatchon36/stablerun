"""Figure F1 (baseline dynamics) and the fan-chart helper shared by other figures."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from . import style
from .style import INK, INK_2, PALETTE, end_labels, panel_title

style.apply()

SCENARIO_COLORS = {"control": PALETTE["black"], "loss05": PALETTE["sky"], "loss10": PALETTE["blue"],
                   "loss20": PALETTE["vermillion"], "scare08": PALETTE["green"]}
SCENARIO_LABELS = {"control": "No shock", "loss05": "5% loss", "loss10": "10% loss",
                   "loss20": "20% loss", "scare08": "8% exposure, resolved day 2"}
SCENARIO_SHORT = {"control": "No shock", "loss05": "5% loss", "loss10": "10% loss",
                  "loss20": "20% loss", "scare08": "Resolved day 2"}
# Cash sources in waterfall order, with one colour each so that Issuer A and B figures match.
SOURCES = [("cash0", "Initial cash", PALETTE["grey"]), ("repo_used", "Reverse repo", PALETTE["sky"]),
           ("mmf_used", "MMF shares", PALETTE["yellow"]), ("runoff", "Maturing bills (run-off)", PALETTE["green"]),
           ("tb1_sold", "Bills sold, $\\leq$1M", PALETTE["blue"]), ("tb3_sold", "Bills sold, 1–3M", PALETTE["purple"]),
           ("other_sold", "Other assets (after haircut)", PALETTE["vermillion"])]


def fan(ax, t, arr, color, label=None, band=(5, 95), iqr=True, ls="-", lw=1.6):
    """Median line with a light 5-95% band and a darker interquartile band."""
    ax.plot(t, np.median(arr, axis=0), color=color, lw=lw, label=label, ls=ls, zorder=3)
    lo, hi = np.percentile(arr, band, axis=0)
    ax.fill_between(t, lo, hi, color=color, alpha=0.10, lw=0, zorder=2)
    if iqr:
        q1, q3 = np.percentile(arr, [25, 75], axis=0)
        ax.fill_between(t, q1, q3, color=color, alpha=0.22, lw=0, zorder=2)


def _join_losses(texts: list[str]) -> str:
    """Labels of coinciding lines: '5% loss', '10% loss', '20% loss' -> '5%, 10%, 20% loss';
    'No shock', 'Resolved day 2' -> 'No shock, resolved day 2'."""
    if len(texts) > 1 and all(t.endswith(" loss") for t in texts):
        return ", ".join(t[:-5] for t in texts) + " loss"
    return ", ".join(t if i == 0 or not t[:1].isalpha() else t[0].lower() + t[1:] for i, t in enumerate(texts))


def _label_ends(ax, results: dict, key: str, scale: float, T: int) -> None:
    items = [(scale * float(np.median(r[key][:, -1])), SCENARIO_SHORT.get(n, n), SCENARIO_COLORS.get(n, PALETTE["grey"]))
             for n, r in results.items()]
    lo, hi = ax.get_ylim()
    end_labels(ax, items, x=T, merge_tol=0.04 * (hi - lo), min_gap=0.08 * (hi - lo), joiner=_join_losses)


def figure_f1(results: dict, out_stem: str | Path, stack_scenario: str = "loss10") -> Path:
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.4))
    (a, b), (c, d) = axes
    T = max(r["T"] for r in results.values())
    for name, r in results.items():
        t = np.arange(r["T"] + 1)
        col = SCENARIO_COLORS.get(name, PALETTE["grey"])
        fan(a, t, r["price"], col)
        fan(b, t, 100 * r["R"], col)
        fan(c, t, r["Y"], col)
    for ax in (a, b, c, d):
        ax.set_xlim(0, T)
        ax.set_xticks(range(0, T + 1, 5))
    for ax in (c, d):
        ax.set_xlabel("Business day")

    a.axhline(1.0, color=INK_2, lw=0.6, ls=(0, (1, 2)), zorder=1)
    panel_title(a, "a", "Secondary price of the token")
    a.set(ylabel="USD per token", ylim=(0.5, 1.03))
    _label_ends(a, results, "price", 1.0, T)

    panel_title(b, "b", "Cumulative redemptions")
    b.set(ylabel="% of initial supply")
    _label_ends(b, results, "R", 100.0, T)
    panel_title(c, "c", "Three-month bill-yield impact")
    c.set(ylabel="bp above the no-run path")
    _label_ends(c, results, "Y", 1.0, T)

    r = results[stack_scenario]
    t = np.arange(r["T"] + 1)
    cum = {k: np.cumsum(r[k].mean(axis=0)) for k in ["cash_used", "repo_used", "mmf_used", "tb1_sold", "tb3_sold", "other_sold"]}
    cum["cash0"] = np.minimum(cum["cash_used"], r["cash0"])
    cum["runoff"] = cum["cash_used"] - cum["cash0"]
    total = sum(cum[k][-1] for k, _, _ in SOURCES)
    keep = [(k, lab, col) for k, lab, col in SOURCES if cum[k][-1] > 0.005 * total]  # sources actually used
    d.stackplot(t, [cum[k] for k, _, _ in keep], labels=[lab for _, lab, _ in keep],
                colors=[col for _, _, col in keep], alpha=0.85, lw=0)
    paid = np.cumsum(r["paid"].mean(axis=0))
    d.plot(t, paid, color=INK, lw=1.0, ls="--", label="Redemptions paid")
    panel_title(d, "d", f"Cash sources, {SCENARIO_SHORT.get(stack_scenario, stack_scenario)} (mean path)")
    d.set(ylabel="USD bn, cumulative")
    d.set_ylim(0, max(total, float(paid[-1])) * (1.05 + 0.08 * len(keep)))  # room for the legend above the stack
    d.legend(loc="upper left", fontsize=7.5, handlelength=1.4)
    fig.tight_layout(w_pad=3.0, h_pad=1.6)
    return style.save(fig, out_stem)
