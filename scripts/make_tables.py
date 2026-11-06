"""Build the LaTeX tables in paper/tables from results/tables and the config, so that every table in the paper
is regenerated from the results by one command.

House style: booktabs rules and no vertical rules; @{} at the outer column edges; numbers right-aligned; column
headings on two lines are bottom-aligned so that the rule sits under the last line; row groups are introduced by
an italic subheading and separated by \\addlinespace; a label that applies to several rows is printed once.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
T, OUT = ROOT / "results" / "tables", ROOT / "paper" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

TIMES = "$\\times$"
TYPES = ["retail", "exchange_mm", "defi", "institutional", "arbitrageur"]
RESERVES = ["cash_deposits", "reverse_repo", "mmf_shares", "tbills_le_1m", "tbills_1_3m", "other"]


def write(name: str, lines: list[str]) -> None:
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def pct(v: float, decimals: int = 1) -> str:
    return f"{100 * float(v):.{decimals}f}\\%"


def head(*lines: str, align: str = "r") -> str:
    """A column heading on one or more lines, bottom-aligned."""
    if len(lines) == 1:
        return lines[0]
    return "\\begin{tabular}[b]{@{}" + align + "@{}}" + "\\\\".join(lines) + "\\end{tabular}"


def group(title: str, ncols: int) -> str:
    return f"\\multicolumn{{{ncols}}}{{@{{}}l}}{{\\itshape {title}}} \\\\"


def row(*cells: str) -> str:
    return " & ".join(cells) + " \\\\"


def tabular(spec: str, header: list[str], body: list[str]) -> list[str]:
    return [f"\\begin{{tabular}}{{{spec}}}", "\\toprule", *header, "\\midrule", *body, "\\bottomrule", "\\end{tabular}"]


# ---------------------------------------------------------------------------------------------------------------
# E1 baseline, Issuer A and B
E1_GROUPS = [
    ("Run", [("Minimum token price", "min_price_med", lambda v: f"{v:.3f}"),
             ("Redeemed by day 7", "R_day7_med", pct),
             ("Redeemed by day 30", "R_end_med", pct),
             ("P(redemptions $\\geq$ 20\\%)", "run_prob", lambda v: pct(v, 0)),
             ("P(redemptions $\\geq$ 50\\%)", "severe_run_prob", lambda v: pct(v, 0)),
             ("P(any suspension day)", "susp_any", lambda v: pct(v, 0))]),
    ("Treasury-bill market", [("Peak three-month yield impact, bp", "peak_Y_bp_med", lambda v: f"{v:.1f}"),
                              ("Peak impact, bp, 95th percentile", "peak_Y_bp_p95", lambda v: f"{v:.1f}"),
                              ("Bills sold outright, \\$bn", "bills_sold_med", lambda v: f"{v:.1f}"),
                              ("Maturing bills not rolled, \\$bn", "withdrawn_med", lambda v: f"{v:.1f}"),
                              ("Peak net bill demand withdrawn, \\$bn", "net_demand_withdrawn_med", lambda v: f"{v:.1f}")]),
    ("Issuer", [("Other assets sold, \\$bn", "other_sold_med", lambda v: f"{v:.1f}"),
                ("Fire-sale and haircut loss, \\$bn", "fs_loss_med", lambda v: f"{v:.2f}"),
                ("Net asset value on day 30", "nav_end_med", lambda v: f"{v:.3f}")]),
]
E1_COLS = [("control", "No shock"), ("loss05", "5\\% loss"), ("loss10", "10\\% loss"), ("loss20", "20\\% loss"),
           ("scare08", head("8\\% exposure,", "resolved day 2"))]
for iss in ["A", "B"]:
    s = pd.read_csv(T / f"E1_{iss}_summary.csv", index_col=0)
    body = []
    for gi, (title, items) in enumerate(E1_GROUPS):
        if gi:
            body.append("\\addlinespace")
        body.append(group(title, 1 + len(E1_COLS)))
        for lab, key, fmt in items:
            body.append(row("\\quad " + lab, *(fmt(float(s.loc[c, key])) for c, _ in E1_COLS)))
    write(f"e1_{iss}.tex", tabular("@{}l" + "r" * len(E1_COLS) + "@{}", [row("", *(h for _, h in E1_COLS))], body))

# ---------------------------------------------------------------------------------------------------------------
# Calibration validation
v = pd.read_csv(T / "calibration_validation.csv")
EPISODE = {"usdc_2023": "USDC, March 2023 (Issuer B)", "usdt_2022": "USDT, May 2022 (Issuer A)"}
TARGET = {"min_price": "Minimum price", "R_day5": "Redeemed by day 5", "R_day10": "Redeemed by day 10",
          "R_day22": "Redeemed by day 22"}
body = []
for ei, (ep, g) in enumerate(v.groupby("episode", sort=False)):
    if ei:
        body.append("\\addlinespace")
    for ri, (_, r) in enumerate(g.iterrows()):
        if r["target"] == "min_price":
            obs, mod = f"${r['observed']:.3f} \\pm {r['tolerance']:.3f}$", f"{r['model']:.3f}"
        else:
            obs, mod = f"${100 * r['observed']:.1f} \\pm {100 * r['tolerance']:.1f}\\%$", pct(r["model"])
        z = round(float(r["z"]), 1) + 0.0  # no "-0.0"
        body.append(row(EPISODE[ep] if ri == 0 else "", TARGET[r["target"]], obs, mod, f"${z:+.1f}$" if z else "0.0"))
write("validation.tex", tabular("@{}llrrr@{}", [row("Episode", "Target", "Observed", "Model", "$z$")], body))

# ---------------------------------------------------------------------------------------------------------------
# E2 peaks and crossings
e2, cr = pd.read_csv(T / "E2_tipping_point.csv"), pd.read_csv(T / "E2_crossings.csv")
sizes = sorted(e2["size"].unique())
SCENARIOS = [("scare", "Liquidity run"), ("loss10", "Solvency run")]
FORMS = [("sqrt", "Square root"), ("linear", "Linear")]
RAILS = [("calibrated", "Calibrated"), ("fast", "Fast"), ("instant", "Instant")]


def crossing(text: str) -> str:
    text = str(text).rstrip("x")
    return f"${text}\\times$" if text[0] in "<>" else f"{text}{TIMES}"


body = []
for si, (sc, scn) in enumerate(SCENARIOS):
    if si:
        body.append("\\addlinespace")
    for fi, (form, formn) in enumerate(FORMS):
        for ri, (rails, railsn) in enumerate(RAILS):
            g = e2[(e2.scenario == sc) & (e2.impact == form) & (e2.rails == rails)].sort_values("size")
            c = cr[(cr.scenario == sc) & (cr.impact == form) & (cr.rails == rails)].iloc[0]
            body.append(row(scn if fi == ri == 0 else "", formn if ri == 0 else "", railsn,
                            *(f"{p:.0f}" for p in g["peak_Y_bp_med"]),
                            *(crossing(c[k]) for k in ["size_10bp", "size_25bp", "size_50bp"])))
n = len(sizes)
header = [row("", "", "", f"\\multicolumn{{{n}}}{{c}}{{{head('Peak impact, bp,', 'at issuer size', align='c')}}}",
              f"\\multicolumn{{3}}{{c@{{}}}}{{{head('Size at which', 'impact first exceeds', align='c')}}}"),
          f"\\cmidrule(lr){{4-{3 + n}}}\\cmidrule(l){{{4 + n}-{6 + n}}}",
          row("Scenario", "Price impact", "Rails", *(f"{int(s)}{TIMES}" for s in sizes), "10 bp", "25 bp", "50 bp")]
write("e2.tex", tabular("@{}lll" + "r" * n + "rrr@{}", header, body))

# ---------------------------------------------------------------------------------------------------------------
# E3 main effects: one label column, four metrics per configuration
e3 = pd.read_csv(T / "E3_policy_grid.csv")
e3["maturity_cap"] = e3["maturity_cap"].astype(str).str.replace(".0", "", regex=False)
CONFIGS = ["scare_1x_calibrated", "loss10_5x_fast"]
METRICS = [("peak_Y_bp_med", lambda v: f"{v:.1f}"), ("R_end_med", pct), ("min_price_med", lambda v: f"{v:.3f}"),
           ("bills_sold_med", lambda v: f"{v:.0f}")]
LEVERS = [("cash_buffer", "Minimum cash buffer, share of reserves", [(0.0, "0\\%"), (0.1, "10\\%"), (0.2, "20\\%"), (0.3, "30\\%")]),
          ("fee", "Redemption fee", [(0.0, "0\\%"), (0.005, "0.5\\%"), (0.01, "1\\%"), (0.02, "2\\%")]),
          ("maturity_cap", "Maturity cap", [("93", "93 days"), ("180", "180 days"), ("none", "None")]),
          ("backstop", "Fed backstop", [(False, "Off"), (True, "On")])]
grid = e3[~e3.cash_buffer.astype(str).isin(["par", "nav"])].copy()
grid["cash_buffer"] = grid["cash_buffer"].astype(float)
body = []
for key, title, levels in LEVERS:
    body += [group(title, 9)]
    for lvl, name in levels:
        cells = []
        for cname in CONFIGS:
            h = grid[(grid.config == cname) & (grid[key] == lvl)]
            assert len(h) == 96 // len(levels), (key, lvl, cname, len(h))  # the other three levers, in full
            cells += [fmt(h[m].mean()) for m, fmt in METRICS]
        body.append(row("\\quad " + name, *cells))
    body.append("\\addlinespace")
basis = e3[e3.cash_buffer.astype(str).isin(["par", "nav"])]
body.append(group("Redemption basis (single runs, no other policy)", 9))
for b, name in [("par", "Par"), ("nav", "Net asset value")]:
    cells = []
    for cname in CONFIGS:
        h = basis[(basis.config == cname) & (basis.cash_buffer == b)].iloc[0]
        cells += [fmt(h[m]) for m, fmt in METRICS]
    body.append(row("\\quad " + name, *cells))
metric_heads = [head("Impact,", "bp"), head("Redeemed", "by day 30"), head("Minimum", "price"), head("Bills sold,", "\\$bn")]
header = [row("", "\\multicolumn{4}{c}{Liquidity run, today's size, calibrated rails}",
              f"\\multicolumn{{4}}{{c@{{}}}}{{Solvency run, 5{TIMES} today's size, fast rails}}"),
          "\\cmidrule(lr){2-5}\\cmidrule(l){6-9}",
          row("", *metric_heads, *metric_heads)]
write("e3.tex", tabular("@{}l" + "r" * 8 + "@{}", header, body))

# ---------------------------------------------------------------------------------------------------------------
# E4 contagion
e4 = pd.read_csv(T / "E4_contagion.csv")
body = []
for si, (sc, scn) in enumerate(SCENARIOS):
    g = e4[e4.scenario_A == sc].sort_values("beta")
    if si:
        body.append("\\addlinespace")
    for ri, (_, r) in enumerate(g.iterrows()):
        body.append(row(scn if ri == 0 else "", f"{r['beta']:.1f}", pct(r["B_R_day7"]), pct(r["B_R_end"]),
                        f"{r['B_min_price']:.3f}", pct(r["B_run_prob"], 0), f"{r['combined_persistent_Y']:.1f}"))
header = [row("", "", "\\multicolumn{4}{c}{Issuer B}", ""), "\\cmidrule(lr){3-6}",
          row("Shock to Issuer A", "$\\beta$", head("Redeemed", "by day 7"), head("Redeemed", "by day 30"),
              head("Minimum", "price"), "P(run)", head("Combined", "impact, bp"))]
write("e4.tex", tabular("@{}lrrrrrr@{}", header, body))

# ---------------------------------------------------------------------------------------------------------------
# Analytic benchmark
b = pd.read_csv(T / "benchmark_check.csv")
body = [row(pct(r["exposure"], 0), pct(r["abm_exit_share"]), pct(r["closed_form_exit_share"])) for _, r in b.iterrows()]
write("benchmark.tex", tabular("@{}rrr@{}", [row("Loss share of reserves", "Simulation", "Closed form")], body))

# ---------------------------------------------------------------------------------------------------------------
# Parameter table (appendix) from the config
c = yaml.safe_load(open(ROOT / "config" / "params_default.yaml", encoding="utf-8"))
A, B, M, H, S = c["issuers"]["A"], c["issuers"]["B"], c["bill_market"], c["holders"], c["secondary_market"]
slash = " / ".join
PARAM_GROUPS = [
    ("Issuers", [
        ("Supply, A / B, \\$bn", f"{A['supply']:.0f} / {B['supply']:.0f}", "attestations, 2026 [verify]"),
        ("Reserves of A: cash / repo / MMF / bills $\\leq$1M / bills 1--3M / other",
         slash(pct(A["reserves"][k]) for k in RESERVES), "attestation [verify]"),
        ("Reserves of B: cash / repo / MMF / bills $\\leq$1M / bills 1--3M / other",
         slash(pct(B["reserves"][k]) for k in RESERVES), "reserve report, look-through [verify]"),
        ("Other-asset fire-sale haircut", pct(A["other_asset_haircut"], 0), "assumption"),
        ("Bill ladder, tb1 / tb3, days", f"{A['ladder_days']['tb1']} / {A['ladder_days']['tb3']}", "assumption"),
        ("Processing capacity, A / B, \\% of supply per day",
         slash(pct(x["redemption"]["processing_cap_share_per_day"]) for x in (A, B)), "calibrated"),
        ("Arbitrage capital, A / B, \\% of supply per day",
         slash(pct(x["redemption"]["arbitrage_capital_share_per_day"]) for x in (A, B)), "calibrated"),
        ("Redemption fee, A / B", slash(pct(x["redemption"]["fee"]) for x in (A, B)), "issuer terms [verify]"),
        ("Cash hoarding horizon, days", f"{A['cash_hoard_days']}", "assumption"),
    ]),
    ("Treasury-bill market", [
        ("Impact anchor flow, \\$bn", f"{M['impact']['reference_flow']}", "Ahmed--Aldasoro [verify]"),
        ("Persistent / temporary sell impact at the anchor, bp per \\$bn",
         f"{M['impact']['sell_permanent_bp_per_bn']} / {M['impact']['sell_temporary_bp_per_bn']}", "Ahmed--Aldasoro outflow range [verify]"),
        ("Buy impact, bp per \\$bn", f"{M['impact']['buy_bp_per_bn']}", "asymmetry [verify]"),
        ("Temporary impact decay per day", f"{M['impact']['temporary_decay_per_day']}", "assumption"),
        ("Impact shape", {"sqrt": "square root", "linear": "linear"}[M["impact"]["functional_form"]] + "; linear below the anchor", "square-root law"),
        ("Dealer capacity $K$, \\$bn / convexity $\\gamma$ / absorption per day",
         f"{M['dealers']['capacity_K']:.0f} / {M['dealers']['convexity_gamma']} / {M['dealers']['absorption_per_day']}", "assumption"),
        ("MMF reinvestment share $\\rho$ / lag, days", f"{M['reinvestment']['share_rho']} / {M['reinvestment']['lag_days']}", "assumption"),
        ("Duration of bills sold, tb1 / tb3, years", f"{M['duration_years']['tb1']} / {M['duration_years']['tb3']}", "bucket midpoints"),
    ]),
    ("Holders", [
        ("Agents $N$", f"{H['n_agents']:,}", "design"),
        ("Type shares of supply: retail / exchange / DeFi / institutional / arbitrageur",
         slash(pct(H["type_shares"][t], 0) for t in TYPES), "assumption"),
        ("Attention probability per day, by type", slash(f"{H['attention'][t]:.2f}" for t in TYPES), "assumption"),
        ("Exit threshold mean, by type", slash(f"{H['thresholds'][t]['mean']:.2f}" for t in TYPES), "calibrated (scale 1.0)"),
        ("Exit threshold s.d., by type", slash(f"{H['thresholds'][t]['sd']:.2f}" for t in TYPES), "assumption"),
        ("Signal weights $w_1$, $w_2$, $w_3$, $w_4$",
         ", ".join(str(H["run_signal_weights"][k]) for k in ["w1_depeg", "w2_private", "w3_herding", "w4_suspension"]), "calibrated / assumption"),
        ("Private-signal s.d. / common-shock s.d.", f"{H['signal_noise_sigma']} / {H['aggregate_noise_sigma']}", "assumption"),
        ("Herding memory / re-entry hysteresis", f"{H['herding_memory']} / {H['reentry_hysteresis']}", "assumption"),
        ("Loss probability $\\psi$", f"{H['exposure_loss_probability']}", "calibrated"),
        ("Belief spillover $\\beta$ (E4)", "0, 0.3, 0.6", "assumption"),
    ]),
    ("Secondary market", [
        ("Liquidity depth $\\eta$ / arbitrage cost / arbitrage horizon, days",
         f"{S['liquidity_depth_eta']} / {S['arbitrage_cost']} / {S['arbitrage_horizon_days']}", "calibrated / assumption"),
        ("Suspension discount / price floor", f"{S['suspension_discount']} / {S['price_floor']}", "assumption"),
    ]),
]
body = []
for gi, (title, items) in enumerate(PARAM_GROUPS):
    if gi:
        body.append("\\addlinespace")
    body.append(group(title, 3))
    body += [row("\\hangindent=1em\\hangafter=0 " + a, b_, c_) for a, b_, c_ in items]  # indented, wrapped lines too
P = ">{\\raggedright\\arraybackslash}p"
write("params.tex", tabular(f"@{{}}{P}{{6.9cm}}{P}{{4.6cm}}{P}{{3.9cm}}@{{}}", [row("Parameter", "Value", "Source")], body))
print("tables:", sorted(p.name for p in OUT.iterdir()))
