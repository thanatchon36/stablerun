"""Phase 2 calibration: fit behavioural and processing parameters to two episodes (all targets VERIFY).

Episodes:
  usdc_2023 (Issuer B): 8% of reserves exposed, resolved on business day 2, no processing on day 1 (weekend)
  usdt_2022 (Issuer A): 4% feared exposure, resolved after 10 business days of successful redemptions
Two-stage grid: shared behavioural parameters (eta, threshold scale, w1) x issuer-specific processing cap
and arbitrage capital. Loss = sum of squared standardised target errors.
"""
from __future__ import annotations

import itertools
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ROOT, with_overrides
from .simulate import simulate

EPISODES = {
    "usdc_2023": {"issuer": "B",
                  "shock": {"name": "usdc_2023", "exposure": 0.08, "realized_share": 0.0, "resolution_day": 2, "blackout_days": 1},
                  "targets": {"min_price": (0.875, 0.01), "R_day5": (0.135, 0.015), "R_day22": (0.25, 0.03)}},
    "usdt_2022": {"issuer": "A",
                  "shock": {"name": "usdt_2022", "exposure": 0.04, "realized_share": 0.0, "resolution_day": 10, "blackout_days": 0},
                  "targets": {"min_price": (0.96, 0.015), "R_day10": (0.12, 0.015)}},
}
SHARED_GRID = {"eta": [0.1, 0.2, 0.3, 0.5], "thr_scale": [1.0, 1.5], "w1": [0.5], "psi": [0.5, 0.75, 1.0], "exp_A": [0.02, 0.04]}
ISSUER_GRID = {"B": {"cap": [0.02, 0.03, 0.05], "arb": [0.01, 0.02, 0.03]},
               "A": {"cap": [0.012, 0.02, 0.028], "arb": [0.005, 0.011]}}
TYPES = ["retail", "exchange_mm", "defi", "institutional", "arbitrageur"]


def overrides(cfg, eta, thr_scale, w1, psi=1.0, issuer=None, cap=None, arb=None, n_agents=None):
    thr = {t: {"mean": round(cfg["holders"]["thresholds"][t]["mean"] * thr_scale, 4)} for t in TYPES}
    o = {"secondary_market": {"liquidity_depth_eta": eta},
         "holders": {"thresholds": thr, "run_signal_weights": {"w1_depeg": w1}, "exposure_loss_probability": psi}}
    if n_agents:
        o["holders"]["n_agents"] = n_agents
    if issuer:
        o["issuers"] = {issuer: {"redemption": {"processing_cap_share_per_day": cap, "arbitrage_capital_share_per_day": arb}}}
    return o


def episode_stats(r):
    R = r["R"]
    return {"min_price": float(np.median(r["price"].min(axis=1))), "R_day5": float(np.median(R[:, 5])),
            "R_day10": float(np.median(R[:, 10])), "R_day22": float(np.median(R[:, 22])), "R_end": float(np.median(R[:, -1]))}


def loss(stats, targets):
    return sum(((stats[k] - m) / tol) ** 2 for k, (m, tol) in targets.items())


def run_grid(cfg, n_paths=40, n_agents=4000, seed=11, verbose=True):
    rows = []
    for eta, ts, w1, psi, exp_a in itertools.product(*SHARED_GRID.values()):
        row = {"eta": eta, "thr_scale": ts, "w1": w1, "psi": psi, "exp_A": exp_a, "total_loss": 0.0}
        for ep, spec in EPISODES.items():
            iss = spec["issuer"]
            shock = dict(spec["shock"], exposure=exp_a) if ep == "usdt_2022" else spec["shock"]
            best = None
            for cap, arb in itertools.product(ISSUER_GRID[iss]["cap"], ISSUER_GRID[iss]["arb"]):
                c = with_overrides(cfg, overrides(cfg, eta, ts, w1, psi, iss, cap, arb, n_agents))
                st = episode_stats(simulate(c, shock, n_paths=n_paths, seed=seed, issuer=iss))
                L = loss(st, spec["targets"])
                if best is None or L < best[0]:
                    best = (L, cap, arb, st)
            row.update({f"{ep}_loss": best[0], f"cap_{iss}": best[1], f"arb_{iss}": best[2]})
            row.update({f"{ep}_{k}": v for k, v in best[3].items() if k in spec["targets"]})
            row["total_loss"] += best[0]
        rows.append(row)
        if verbose:
            print(f"eta {eta:.2f} thr {ts:.2f} psi {psi:.2f} expA {exp_a:.2f}  loss {row['total_loss']:7.2f}  usdc {row['usdc_2023_loss']:6.2f}  usdt {row['usdt_2022_loss']:6.2f}")
    return pd.DataFrame(rows).sort_values("total_loss").reset_index(drop=True)


def patch_config(path: Path, cfg, best):
    """Write calibrated values into the YAML in place, keeping comments."""
    s = path.read_text(encoding="utf-8")
    def sub(pattern, repl, count=1):
        nonlocal s
        s, n = re.subn(pattern, repl, s, count=count, flags=re.M)
        assert n == count, pattern
    sub(r"^(  liquidity_depth_eta: )[0-9.]+(.*)$", rf"\g<1>{best['eta']}  # calibrated Phase 2 (was 0.2)")
    sub(r"^(    w1_depeg: )[0-9.]+(.*)$", rf"\g<1>{best['w1']}  # calibrated Phase 2")
    sub(r"^(  exposure_loss_probability: )[0-9.]+(.*)$", rf"\g<1>{best['psi']}\g<2>")
    for t in TYPES:
        m = round(cfg["holders"]["thresholds"][t]["mean"] * best["thr_scale"], 4)
        sub(rf"^(    {t}: \{{mean: )[0-9.]+(, sd: [0-9.]+\}}.*)$", rf"\g<1>{m}\g<2>")
    for iss in ["A", "B"]:
        block = s.index(f"\n  {iss}:")
        end = s.index("\n  B:") if iss == "A" else s.index("\nbill_market:")
        seg = s[block:end]
        seg = re.sub(r"(processing_cap_share_per_day: )[0-9.]+", rf"\g<1>{best[f'cap_{iss}']}", seg, count=1)
        seg = re.sub(r"(arbitrage_capital_share_per_day: )[0-9.]+", rf"\g<1>{best[f'arb_{iss}']}", seg, count=1)
        s = s[:block] + seg + s[end:]
    s = s.replace('version: "0.2-phase1"', 'version: "0.3-phase2-calibrated"')
    path.write_text(s, encoding="utf-8")


def validation_figure(results, out_stem):
    import matplotlib.pyplot as plt
    from . import style
    from .plots import PALETTE, fan
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 4.8))
    for j, (ep, r) in enumerate(results.items()):
        spec = EPISODES[ep]
        t = np.arange(r["T"] + 1)
        a, b = axes[0, j], axes[1, j]
        fan(a, t, r["price"], PALETTE["blue"], "Model (median, IQR, 5-95%)")
        lo, hi = (0.87, 0.88) if ep == "usdc_2023" else (0.95, 0.97)
        a.axhspan(lo, hi, color=PALETTE["vermillion"], alpha=0.25, lw=0, label="Observed trough range [verify]")
        name = "USDC, March 2023 (Issuer B)" if ep == "usdc_2023" else "USDT, May 2022 (Issuer A)"
        a.set(title=f"({'ab'[j]}) {name}: token price", ylabel="USD per token", ylim=(0.8, 1.02))
        fan(b, t, 100 * r["R"], PALETTE["blue"])
        for k, (m, tol) in spec["targets"].items():
            if k.startswith("R_day"):
                d = int(k[5:])
                b.errorbar([d], [100 * m], yerr=[[100 * tol], [100 * tol]], fmt="o", color=PALETTE["vermillion"],
                           capsize=3, label="Observed redemptions [verify]" if d == min(int(x[5:]) for x in spec["targets"] if x.startswith("R_day")) else None)
        b.set(title=f"({'cd'[j]}) Cumulative redemptions", ylabel="% of initial supply", xlabel="Business day")
        if j == 0:
            a.legend(fontsize=6.8, loc="lower right"); b.legend(fontsize=6.8, loc="lower right")
    fig.tight_layout(w_pad=1.5, h_pad=1.2)
    style.save(fig, out_stem)


def run_calibration(cfg, out_dir=None, n_paths_final=300):
    out_dir = Path(out_dir) if out_dir else ROOT / "results"
    grid = run_grid(cfg)
    grid.to_csv(out_dir / "tables" / "calibration_grid.csv", index=False)
    best = grid.iloc[0].to_dict()
    patch_config(ROOT / "config" / "params_default.yaml", cfg, best)
    from .config import load_config
    cal = load_config()
    results, rows = {}, []
    EPISODES["usdt_2022"]["shock"]["exposure"] = best["exp_A"]
    for ep, spec in EPISODES.items():
        r = simulate(cal, spec["shock"], n_paths=n_paths_final, seed=cal["meta"]["seed"], issuer=spec["issuer"])
        results[ep] = r
        st = episode_stats(r)
        for k, (m, tol) in spec["targets"].items():
            rows.append({"episode": ep, "target": k, "observed": m, "tolerance": tol, "model": round(st[k], 4),
                         "z": round((st[k] - m) / tol, 2)})
    val = pd.DataFrame(rows)
    val.to_csv(out_dir / "tables" / "calibration_validation.csv", index=False)
    validation_figure(results, out_dir / "figures" / "F4_validation")
    lines = ["# Phase 2 calibration", "", "Best shared parameters (grid, 40 paths x 4,000 agents): "
             f"eta = {best['eta']}, threshold scale = {best['thr_scale']}, w1 = {best['w1']}, psi = {best['psi']}, USDT-2022 feared exposure = {best['exp_A']}; "
             f"Issuer A cap/arb = {best['cap_A']}/{best['arb_A']}, Issuer B cap/arb = {best['cap_B']}/{best['arb_B']} (shares of supply per day).",
             "", "Validation at 300 paths x 10,000 agents (z = (model - observed)/tolerance; all observed values VERIFY):", "",
             "| Episode | Target | Observed | Model | z |", "|---|---|---|---|---|"]
    for _, r_ in val.iterrows():
        lines.append(f"| {r_['episode']} | {r_['target']} | {r_['observed']} ± {r_['tolerance']} | {r_['model']} | {r_['z']} |")
    (out_dir / "tables" / "calibration.md").write_text("\n".join(lines), encoding="utf-8")
    return grid, val, cal
