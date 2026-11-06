"""Phase 2-3 experiments: E2 tipping point, E3 policy grid, E4 contagion, E5 sensitivity, benchmark check."""
from __future__ import annotations

import itertools
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from .agents import TYPES
from .config import ROOT, with_overrides
from .metrics import path_metrics, summarize
from .simulate import simulate

SCARE = {"name": "scare", "exposure": 0.08, "realized_share": 0.0, "resolution_day": 2, "blackout_days": 1}
LOSS10 = {"name": "loss10", "exposure": 0.10, "realized_share": 1.0, "resolution_day": None}
FAST_CAP = 0.05   # "fast rails" processing capacity, share of supply per day (assumption)
RAILS = {"calibrated": None, "fast": FAST_CAP, "instant": 0.20}   # instant = near-24/7 redemption at scale (assumption)


def _run(cfg, shock, size=1.0, form="sqrt", cap=None, policy=None, n_paths=300, seed=None, issuer="A", **ov):
    o = {"bill_market": {"impact": {"functional_form": form}}}
    if cap is not None:
        o["issuers"] = {issuer: {"redemption": {"processing_cap_share_per_day": cap}}}
    c = with_overrides(cfg, o)
    c = with_overrides(c, ov) if ov else c
    r = simulate(c, shock, n_paths=n_paths, seed=seed, issuer=issuer, size_multiplier=size, policy=policy)
    return r, summarize(path_metrics(r, c))


# ---------------------------------------------------------------- E2
def run_e2(cfg, out_dir, sizes=(1, 2, 3, 5, 10), n_paths=300):
    rows = []
    for shock, form, capname in itertools.product([SCARE, LOSS10], ["sqrt", "linear"], list(RAILS)):
        cap = RAILS[capname]
        for size in sizes:
            t0 = time.time()
            r, s = _run(cfg, shock, size=size, form=form, cap=cap, n_paths=n_paths)
            rows.append({"scenario": shock["name"], "impact": form, "rails": capname, "size": size,
                         "supply_bn": r["s0"], **{k: s[k] for k in s.index}})
            print(f"E2 {shock['name']:6s} {form:6s} {capname:10s} x{size:<3d} {time.time()-t0:4.1f}s  peakY {s['peak_Y_bp_med']:7.1f}bp  sold {s['bills_sold_med']:7.1f}  inv/K {s['peak_inv_over_K_med']:5.2f}  R30 {s['R_end_med']:.2f}")
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "tables" / "E2_tipping_point.csv", index=False)
    # crossing sizes: first size at which the median peak impact exceeds each threshold (log-linear interpolation)
    cross = []
    for (sc, form, rails), g in df.groupby(["scenario", "impact", "rails"]):
        g = g.sort_values("size")
        row = {"scenario": sc, "impact": form, "rails": rails}
        for thr in cfg["metrics"]["yield_thresholds_bp"]:
            y, x = g["peak_Y_bp_med"].values, g["size"].values
            above = np.where(y > thr)[0]
            if len(above) == 0:
                row[f"size_{thr}bp"] = f">{x[-1]}x"
            elif above[0] == 0:
                row[f"size_{thr}bp"] = f"<{x[0]}x"
            else:
                i = above[0]
                lx = np.interp(np.log(thr), np.log([y[i - 1], y[i]]), np.log([x[i - 1], x[i]]))
                row[f"size_{thr}bp"] = f"{np.exp(lx):.1f}x"
        cross.append(row)
    cross = pd.DataFrame(cross)
    cross.to_csv(out_dir / "tables" / "E2_crossings.csv", index=False)
    lines = ["# E2 tipping point — Issuer A, sector size multiples, 300 paths", "",
             "Sector size at which the median peak 3M bill-yield impact first exceeds 10 / 25 / 50 bp "
             "(log-linear interpolation between simulated sizes 1, 2, 3, 5, 10). 'rails' = redemption processing capacity: "
             f"calibrated {cfg['issuers']['A']['redemption']['processing_cap_share_per_day']:.1%}/day, fast {FAST_CAP:.0%}/day or instant {RAILS['instant']:.0%}/day.", "",
             "| Scenario | Impact form | Rails | >10 bp | >25 bp | >50 bp |", "|---|---|---|---|---|---|"]
    for _, r_ in cross.iterrows():
        lines.append(f"| {r_['scenario']} | {r_['impact']} | {r_['rails']} | {r_['size_10bp']} | {r_['size_25bp']} | {r_['size_50bp']} |")
    lines += ["", "Median peak impact (bp) by size:", "", "| Scenario | Impact | Rails | " + " | ".join(f"{s}x" for s in sizes) + " |",
              "|---|---|---|" + "---|" * len(sizes)]
    for (sc, form, rails), g in df.groupby(["scenario", "impact", "rails"]):
        g = g.sort_values("size")
        lines.append(f"| {sc} | {form} | {rails} | " + " | ".join(f"{v:.0f}" for v in g["peak_Y_bp_med"]) + " |")
    lines += ["", "Median bills sold outright ($bn) and peak dealer inventory / K, instant rails, loss10:", ""]
    g = df[(df.scenario == "loss10") & (df.rails == "instant") & (df.impact == "sqrt")].sort_values("size")
    lines.append("| Size | " + " | ".join(f"{s}x" for s in g["size"]) + " |")
    lines.append("|---|" + "---|" * len(g))
    lines.append("| Bills sold, $bn | " + " | ".join(f"{v:.0f}" for v in g["bills_sold_med"]) + " |")
    lines.append("| Dealer inventory / K | " + " | ".join(f"{v:.2f}" for v in g["peak_inv_over_K_med"]) + " |")
    lines.append("| P(suspension) | " + " | ".join(f"{v:.0%}" for v in g["susp_any"]) + " |")
    (out_dir / "tables" / "E2_tipping_point.md").write_text("\n".join(lines), encoding="utf-8")
    return df, cross


# ---------------------------------------------------------------- E3
E3_CONFIGS = [("scare_1x_calibrated", SCARE, 1.0, None), ("loss10_5x_fast", LOSS10, 5.0, FAST_CAP)]


def run_e3(cfg, out_dir, n_paths=200, only=None, backstops=None):
    pg = cfg["policy_grid"]
    configs = [c for c in E3_CONFIGS if only is None or c[0] == only]
    bss = pg["fed_backstop"] if backstops is None else backstops
    rows = []
    for cname, shock, size, cap in configs:
        t0 = time.time()
        for cb, fee, mat, bs in itertools.product(pg["cash_buffer"], pg["redemption_fee"], pg["maturity_cap_days"], bss):
            pol = {"cash_buffer": cb, "redemption_fee": fee, "maturity_cap_days": mat, "fed_backstop": bs}
            r, s = _run(cfg, shock, size=size, cap=cap, policy=pol, n_paths=n_paths)
            rows.append({"config": cname, "cash_buffer": cb, "fee": fee, "maturity_cap": "none" if mat is None else mat,
                         "backstop": bs, **{k: s[k] for k in ["peak_Y_bp_med", "peak_Y_bp_p95", "R_end_med", "R_day7_med", "min_price_med",
                                                           "run_prob", "susp_any", "bills_sold_med", "fs_loss_med", "peak_inv_over_K_med", "P_Y_gt_25bp"]}})
        # extra lever: redemption at NAV instead of par
        for nav in ([False, True] if (backstops is None or False in bss) else []):
            r, s = _run(cfg, shock, size=size, cap=cap, policy={"redeem_at_nav": nav}, n_paths=n_paths)
            rows.append({"config": cname, "cash_buffer": "nav" if nav else "par", "fee": 0.0, "maturity_cap": 93, "backstop": False,
                         **{k: s[k] for k in ["peak_Y_bp_med", "peak_Y_bp_p95", "R_end_med", "R_day7_med", "min_price_med",
                                              "run_prob", "susp_any", "bills_sold_med", "fs_loss_med", "peak_inv_over_K_med", "P_Y_gt_25bp"]}})
        print(f"E3 {cname} done in {time.time()-t0:.0f}s")
    df = pd.DataFrame(rows)
    path = out_dir / "tables" / "E3_policy_grid.csv"
    if path.exists():
        df = pd.concat([pd.read_csv(path), df], ignore_index=True).drop_duplicates(["config", "cash_buffer", "fee", "maturity_cap", "backstop"], keep="last")
    df.to_csv(path, index=False)
    return df


def write_e3_markdown(cfg, out_dir):
    pg = cfg["policy_grid"]
    df = pd.read_csv(out_dir / "tables" / "E3_policy_grid.csv")
    df["maturity_cap"] = df["maturity_cap"].astype(str).str.replace(".0", "", regex=False)
    lines = ["# E3 policy grid — main effects (200 paths per cell)", ""]
    for cname, _, _, _ in E3_CONFIGS:
        g = df[(df.config == cname) & (df.cash_buffer.astype(str).isin([str(x) for x in pg["cash_buffer"]]))].copy()
        g["cash_buffer"] = g["cash_buffer"].astype(float)
        base = g[(g.cash_buffer == 0.0) & (g.fee == 0.0) & (g.maturity_cap == "93") & (~g.backstop)].iloc[0]
        lines += [f"## {cname}", "", f"No-policy cell: peak impact {base['peak_Y_bp_med']:.1f} bp, redeemed day 30 {base['R_end_med']:.1%}, "
                  f"min price {base['min_price_med']:.3f}, P(suspension) {base['susp_any']:.0%}.", "",
                  "| Lever | Level | Peak impact, bp | Redeemed day 30 | Min price | P(susp) | Bills sold, $bn |", "|---|---|---|---|---|---|---|"]
        for lever in ["cash_buffer", "fee", "maturity_cap", "backstop"]:
            for lvl, h in g.groupby(lever, sort=False):
                lines.append(f"| {lever} | {lvl} | {h['peak_Y_bp_med'].mean():.1f} | {h['R_end_med'].mean():.1%} | "
                             f"{h['min_price_med'].mean():.3f} | {h['susp_any'].mean():.0%} | {h['bills_sold_med'].mean():.1f} |")
        nav = df[(df.config == cname) & (df.cash_buffer.isin(["par", "nav"]))]
        for _, r_ in nav.iterrows():
            lines.append(f"| redemption basis | {r_['cash_buffer']} | {r_['peak_Y_bp_med']:.1f} | {r_['R_end_med']:.1%} | {r_['min_price_med']:.3f} | {r_['susp_any']:.0%} | {r_['bills_sold_med']:.1f} |")
        lines.append("")
    (out_dir / "tables" / "E3_policy_grid.md").write_text("\n".join(lines), encoding="utf-8")
    return df


# ---------------------------------------------------------------- E4
def run_e4(cfg, out_dir, n_paths=300):
    rows, series = [], {}
    for shock in [SCARE, LOSS10]:
        rA, sA = _run(cfg, shock, n_paths=n_paths)
        pA = np.median(rA["price"], axis=0)
        cA = np.median(rA["C"], axis=0)
        for beta in [0.0, 0.3, 0.6]:
            spill = beta * (1.0 - pA)
            shockB = {"name": f"contagion_{shock['name']}", "exposure": 0.0, "realized_share": 1.0, "resolution_day": None, "spillover_signal": spill}
            rB, sB = _run(cfg, shockB, n_paths=n_paths, issuer="B")
            cB = np.median(rB["C"], axis=0)
            imp = cfg["bill_market"]["impact"]
            from .billmarket import impact_g
            comb = imp["sell_permanent_bp_per_bn"] * impact_g(cA + cB, imp["functional_form"], imp["reference_flow"])
            rows.append({"scenario_A": shock["name"], "beta": beta, "B_R_end": sB["R_end_med"], "B_R_day7": sB["R_day7_med"],
                         "B_min_price": sB["min_price_med"], "B_run_prob": sB["run_prob"], "A_peak_Y": sA["peak_Y_bp_med"],
                         "B_peak_Y": sB["peak_Y_bp_med"], "combined_persistent_Y": float(comb.max())})
            series[(shock["name"], beta)] = (pA, np.median(rB["price"], axis=0), np.median(rB["R"], axis=0))
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "tables" / "E4_contagion.csv", index=False)
    lines = ["# E4 contagion — Issuer A shock, belief spillover to Issuer B (300 paths)", "",
             "Issuer B's holders add beta x (1 - price_A) to their expected-loss belief. Combined impact = persistent component on the sum of both issuers' net demand withdrawn.", "",
             "| A scenario | beta | B redeemed day 7 | B redeemed day 30 | B min price | P(B run) | A peak impact, bp | Combined persistent impact, bp |", "|---|---|---|---|---|---|---|---|"]
    for _, r_ in df.iterrows():
        lines.append(f"| {r_['scenario_A']} | {r_['beta']} | {r_['B_R_day7']:.1%} | {r_['B_R_end']:.1%} | {r_['B_min_price']:.3f} | {r_['B_run_prob']:.0%} | {r_['A_peak_Y']:.1f} | {r_['combined_persistent_Y']:.1f} |")
    (out_dir / "tables" / "E4_contagion.md").write_text("\n".join(lines), encoding="utf-8")
    return df, series


# ---------------------------------------------------------------- E5
SENS = [  # (label, low overrides, high overrides)
    ("Liquidity depth eta", {"secondary_market": {"liquidity_depth_eta": 0.05}}, {"secondary_market": {"liquidity_depth_eta": 0.2}}),
    ("Exit thresholds (x0.75 / x1.5)", "thr0.75", "thr1.5"),
    ("Depeg weight w1", {"holders": {"run_signal_weights": {"w1_depeg": 0.25}}}, {"holders": {"run_signal_weights": {"w1_depeg": 1.0}}}),
    ("Herding weight w3", {"holders": {"run_signal_weights": {"w3_herding": 0.15}}}, {"holders": {"run_signal_weights": {"w3_herding": 0.6}}}),
    ("Signal noise sd", {"holders": {"signal_noise_sigma": 0.01}}, {"holders": {"signal_noise_sigma": 0.04}}),
    ("Attention (x0.5 / x1.5)", "att0.5", "att1.5"),
    ("MMF reinvestment rho", {"bill_market": {"reinvestment": {"share_rho": 0.0}}}, {"bill_market": {"reinvestment": {"share_rho": 1.0}}}),
    ("Run-off weight", {"bill_market": {"impact": {"runoff_weight": 0.5}}}, {"bill_market": {"impact": {"runoff_weight": 1.0}}}),
    ("Persistent impact coefficient", {"bill_market": {"impact": {"sell_permanent_bp_per_bn": 1.0}}}, {"bill_market": {"impact": {"sell_permanent_bp_per_bn": 3.0}}}),
    ("Dealer capacity K", {"bill_market": {"dealers": {"capacity_K": 75.0}}}, {"bill_market": {"dealers": {"capacity_K": 300.0}}}),
    ("Processing cap (x0.5 / x2.5)", "cap0.5", "cap2.5"),
    ("Arbitrage capital (x0.5 / x2)", "arb0.5", "arb2"),
    ("Loss probability psi", {"holders": {"exposure_loss_probability": 0.5}}, {"holders": {"exposure_loss_probability": 1.0}}),
    ("Agents N (5k / 20k)", {"holders": {"n_agents": 5000}}, {"holders": {"n_agents": 20000}}),
    ("Cash hoarding (2 / 10 days)", {"issuers": {"A": {"cash_hoard_days": 2}}}, {"issuers": {"A": {"cash_hoard_days": 10}}}),
]


def _sens_override(cfg, spec, issuer="A"):
    if isinstance(spec, dict):
        return spec
    kind, val = spec[:3], float(spec[3:])
    h = cfg["holders"]
    if kind == "thr":
        return {"holders": {"thresholds": {t: {"mean": h["thresholds"][t]["mean"] * val} for t in TYPES}}}
    if kind == "att":
        return {"holders": {"attention": {t: min(1.0, h["attention"][t] * val) for t in TYPES}}}
    r = cfg["issuers"][issuer]["redemption"]
    if kind == "cap":
        return {"issuers": {issuer: {"redemption": {"processing_cap_share_per_day": r["processing_cap_share_per_day"] * val}}}}
    if kind == "arb":
        return {"issuers": {issuer: {"redemption": {"arbitrage_capital_share_per_day": r["arbitrage_capital_share_per_day"] * val}}}}
    raise ValueError(spec)


E5_CONFIGS = [("loss10_5x_fast", LOSS10, 5.0, FAST_CAP, "peak_Y_bp_med"), ("scare_1x_calibrated", SCARE, 1.0, None, "R_end_med")]


def run_e5(cfg, out_dir, n_paths=200, only=None, params=None):
    rows = []
    for cname, shock, size, cap, metric in [c for c in E5_CONFIGS if only is None or c[0] == only]:
        _, base = _run(cfg, shock, size=size, cap=cap, n_paths=n_paths)
        for label, lo, hi in [x for x in SENS if params is None or x[0] in params]:
            out = {"config": cname, "metric": metric, "parameter": label, "base": base[metric]}
            for side, spec in [("low", lo), ("high", hi)]:
                c = with_overrides(cfg, _sens_override(cfg, spec))
                if cap is not None and not (isinstance(spec, str) and spec.startswith("cap")):
                    c = with_overrides(c, {"issuers": {"A": {"redemption": {"processing_cap_share_per_day": cap}}}})
                elif cap is not None and isinstance(spec, str) and spec.startswith("cap"):
                    c = with_overrides(c, {"issuers": {"A": {"redemption": {"processing_cap_share_per_day": cap * float(spec[3:])}}}})
                r = simulate(c, shock, n_paths=n_paths, seed=cfg["meta"]["seed"], issuer="A", size_multiplier=size)
                s = summarize(path_metrics(r, c))
                out[side] = s[metric]
                out[f"{side}_other"] = s["R_end_med" if metric == "peak_Y_bp_med" else "peak_Y_bp_med"]
            rows.append(out)
            print(f"E5 {cname} {label:32s} base {out['base']:7.2f} low {out['low']:7.2f} high {out['high']:7.2f}")
    df = pd.DataFrame(rows)
    path = out_dir / "tables" / "E5_sensitivity.csv"
    if path.exists():
        df = pd.concat([pd.read_csv(path), df], ignore_index=True).drop_duplicates(["config", "parameter"], keep="last")
    df.to_csv(path, index=False)
    return df


# ---------------------------------------------------------------- analytic benchmark check
def run_benchmark(cfg, out_dir, n_paths=100):
    """ABM with herding, depeg and suspension channels switched off and a fixed belief, versus the closed-form
    exit share sum_k share_k * Phi((x - theta_k) / sqrt(sigma^2 + sd_k^2))."""
    h = cfg["holders"]
    c = with_overrides(cfg, {"holders": {"run_signal_weights": {"w1_depeg": 0.0, "w3_herding": 0.0, "w4_suspension": 0.0},
                                         "aggregate_noise_sigma": 0.0}})
    rows = []
    for x in [0.0, 0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.20]:
        r = simulate(c, {"exposure": x, "realized_share": 1.0, "resolution_day": None, "fixed_belief": True}, n_paths=n_paths,
                     seed=cfg["meta"]["seed"], issuer="A")
        abm = float(np.median(r["exit_flow"].sum(axis=1)))
        closed = sum(h["type_shares"][t] * norm.cdf((x - h["thresholds"][t]["mean"]) / np.sqrt(h["signal_noise_sigma"] ** 2 + h["thresholds"][t]["sd"] ** 2))
                     for t in TYPES)
        rows.append({"exposure": x, "abm_exit_share": abm, "closed_form_exit_share": closed})
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "tables" / "benchmark_check.csv", index=False)
    return df
