"""Experiment drivers. Each writes tables to results/tables and figures to results/figures."""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from .config import ROOT
from .metrics import path_metrics, summarize
from .plots import figure_f1
from .simulate import simulate


def run_e1(cfg: dict, n_paths: int | None = None, seed: int | None = None, issuer: str = "A",
           out_dir: str | Path | None = None, verbose: bool = True) -> dict:
    """E1 baseline: shock scenarios from cfg['shocks']['e1_scenarios'] on one issuer."""
    out_dir = Path(out_dir) if out_dir else ROOT / "results"
    (out_dir / "tables").mkdir(parents=True, exist_ok=True)
    (out_dir / "figures").mkdir(parents=True, exist_ok=True)
    results, rows, paths = {}, {}, {}
    for sc in cfg["shocks"]["e1_scenarios"]:
        t0 = time.time()
        r = simulate(cfg, sc, n_paths=n_paths, seed=seed, issuer=issuer)
        df = path_metrics(r, cfg)
        results[sc["name"]], paths[sc["name"]] = r, df
        rows[sc["name"]] = summarize(df)
        if verbose:
            print(f"E1 {sc['name']:8s} {r['n_paths']} paths {time.time() - t0:5.1f}s  "
                  f"R_end med {rows[sc['name']]['R_end_med']:.3f}  R7 {rows[sc['name']]['R_day7_med']:.3f}  minP med {rows[sc['name']]['min_price_med']:.3f}  "
                  f"peakY med {rows[sc['name']]['peak_Y_bp_med']:.1f}bp  run {rows[sc['name']]['run_prob']:.2f}")
    summary = pd.DataFrame(rows).T
    summary.index.name = "scenario"
    summary.to_csv(out_dir / "tables" / f"E1_{issuer}_summary.csv")
    for name, df in paths.items():
        df.to_csv(out_dir / "tables" / f"E1_{issuer}_{name}_paths.csv", index=False)
    write_e1_markdown(summary, out_dir / "tables" / f"E1_{issuer}_summary.md", cfg, issuer, n_paths or cfg["meta"]["monte_carlo_paths"])
    figure_f1(results, out_dir / "figures" / f"F1_{issuer}_baseline_dynamics")
    return {"results": results, "summary": summary, "paths": paths}


def write_e1_markdown(summary: pd.DataFrame, path: Path, cfg: dict, issuer: str, n_paths: int) -> None:
    cols = [("min_price_med", "Min price (med)", "{:.3f}"), ("R_day7_med", "Redeemed day 7", "{:.1%}"),
            ("R_end_med", "Redeemed day 30", "{:.1%}"), ("run_prob", "P(run >=20%)", "{:.0%}"),
            ("severe_run_prob", "P(run >=50%)", "{:.0%}"), ("peak_Y_bp_med", "Peak 3M bill impact, bp (med)", "{:.1f}"),
            ("peak_Y_bp_p95", "Peak impact, bp (p95)", "{:.1f}"), ("P_Y_gt_10bp", "P(impact >10bp)", "{:.0%}"),
            ("bills_sold_med", "Bills sold outright, $bn (med)", "{:.1f}"), ("withdrawn_med", "Maturing bills not rolled, $bn (med)", "{:.1f}"),
            ("net_demand_withdrawn_med", "Peak net bill demand withdrawn, $bn (med)", "{:.1f}"),
            ("other_sold_med", "Other assets sold, $bn (med)", "{:.1f}"), ("peak_inv_over_K_med", "Peak dealer inventory / K", "{:.2f}"),
            ("susp_any", "P(any suspension day)", "{:.0%}"), ("fs_loss_med", "Fire-sale + haircut loss, $bn (med)", "{:.2f}"),
            ("nav_end_med", "NAV day 30 (med)", "{:.3f}")]
    icfg = cfg["issuers"][issuer]
    scen = {sc["name"]: sc for sc in cfg["shocks"]["e1_scenarios"]}
    lines = [f"# E1 baseline — Issuer {issuer}, {n_paths} Monte Carlo paths, {cfg['meta']['horizon_days']} business days",
             "", f"Supply ${icfg['supply']:.0f}bn; impact form `{cfg['bill_market']['impact']['functional_form']}`; "
             f"processing cap {icfg['redemption']['processing_cap_share_per_day']:.1%} of supply per day; "
             f"arbitrage capital {icfg['redemption']['arbitrage_capital_share_per_day']:.1%} of supply per day. "
             "All inputs are Phase-1 defaults (uncalibrated); see config/params_default.yaml.", "",
             "Scenarios: " + "; ".join(
                 f"`{n}` = {sc['exposure']:.0%} of reserves at risk, {sc['realized_share']:.0%} of it lost"
                 + (f", resolved on day {sc['resolution_day']}" if sc.get("resolution_day") else "")
                 for n, sc in scen.items()), "",
             "| Metric | " + " | ".join(summary.index) + " |", "|---|" + "---|" * len(summary.index)]
    for key, label, fmt in cols:
        lines.append(f"| {label} | " + " | ".join(fmt.format(summary.loc[s, key]) for s in summary.index) + " |")
    lines += ["", "Medians across paths unless stated; p95 = 95th percentile. Run = cumulative redemptions "
              f">= {cfg['metrics']['run_threshold']:.0%} of initial supply by day {cfg['meta']['horizon_days']}."]
    path.write_text("\n".join(lines), encoding="utf-8")
