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
    from .plots import fan
    from .style import INK_2, PALETTE, panel_title
    fig, axes = plt.subplots(2, 2, figsize=(6.5, 5.0), sharex=True)
    for j, (ep, r) in enumerate(results.items()):
        spec = EPISODES[ep]
        t = np.arange(r["T"] + 1)
        a, b = axes[0, j], axes[1, j]
        a.axhline(1.0, color=INK_2, lw=0.6, ls=(0, (1, 2)), zorder=1)
        fan(a, t, r["price"], PALETTE["blue"], "Model (median, IQR, 5–95% band)")
        lo, hi = (0.87, 0.88) if ep == "usdc_2023" else (0.95, 0.97)
        a.axhspan(lo, hi, color=PALETTE["vermillion"], alpha=0.25, lw=0, label="Observed trough range")
        name = "USDC, March 2023 (Issuer B)" if ep == "usdc_2023" else "USDT, May 2022 (Issuer A)"
        panel_title(a, "ab"[j], f"{name}: token price")
        a.set(ylabel="USD per token", ylim=(0.8, 1.02), xlim=(0, r["T"]), xticks=range(0, r["T"] + 1, 5))
        fan(b, t, 100 * r["R"], PALETTE["blue"])
        days = sorted(int(k[5:]) for k in spec["targets"] if k.startswith("R_day"))
        for d in days:
            m, tol = spec["targets"][f"R_day{d}"]
            b.errorbar([d], [100 * m], yerr=100 * tol, fmt="o", color=PALETTE["vermillion"], ms=4.5, mec="white", mew=0.6,
                       capsize=3, lw=1.2, zorder=4, label="Observed redemptions (± tolerance)" if d == days[0] else None)
        panel_title(b, "cd"[j], "Cumulative redemptions")
        b.set(ylabel="% of initial supply", xlabel="Business day", ylim=(0, 30))
    handles, labels = axes[0, 0].get_legend_handles_labels()
    h2, l2 = axes[1, 0].get_legend_handles_labels()
    fig.legend(handles + h2, labels + l2, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0), fontsize=7.8,
               handlelength=1.8, columnspacing=1.6)
    fig.tight_layout(rect=[0, 0.05, 1, 1], w_pad=2.0, h_pad=1.4)
    style.save(fig, out_stem)


def run_validation(cfg, out_dir=None, n_paths_final=300, exp_A=None):
    """Run the two calibration episodes with the current (calibrated) config: writes calibration_validation.csv
    and Figure F4. The feared USDT exposure comes from the best row of calibration_grid.csv unless given."""
    out_dir = Path(out_dir) if out_dir else ROOT / "results"
    if exp_A is None:
        grid_path = out_dir / "tables" / "calibration_grid.csv"
        exp_A = float(pd.read_csv(grid_path)["exp_A"].iloc[0]) if grid_path.exists() else EPISODES["usdt_2022"]["shock"]["exposure"]
    episodes = {ep: dict(spec, shock=dict(spec["shock"])) for ep, spec in EPISODES.items()}
    episodes["usdt_2022"]["shock"]["exposure"] = exp_A
    results, rows = {}, []
    for ep, spec in episodes.items():
        r = simulate(cfg, spec["shock"], n_paths=n_paths_final, seed=cfg["meta"]["seed"], issuer=spec["issuer"])
        results[ep] = r
        st = episode_stats(r)
        for k, (m, tol) in spec["targets"].items():
            rows.append({"episode": ep, "target": k, "observed": m, "tolerance": tol, "model": round(st[k], 4),
                         "z": round((st[k] - m) / tol, 2)})
    val = pd.DataFrame(rows)
    val.to_csv(out_dir / "tables" / "calibration_validation.csv", index=False)
    validation_figure(results, out_dir / "figures" / "F4_validation")
    return val, results


def run_calibration(cfg, out_dir=None, n_paths_final=300):
    out_dir = Path(out_dir) if out_dir else ROOT / "results"
    grid = run_grid(cfg)
    grid.to_csv(out_dir / "tables" / "calibration_grid.csv", index=False)
    best = grid.iloc[0].to_dict()
    patch_config(ROOT / "config" / "params_default.yaml", cfg, best)
    from .config import load_config
    cal = load_config()
    val, _ = run_validation(cal, out_dir, n_paths_final, exp_A=best["exp_A"])
    lines = ["# Phase 2 calibration", "", "Best shared parameters (grid, 40 paths x 4,000 agents): "
             f"eta = {best['eta']}, threshold scale = {best['thr_scale']}, w1 = {best['w1']}, psi = {best['psi']}, USDT-2022 feared exposure = {best['exp_A']}; "
             f"Issuer A cap/arb = {best['cap_A']}/{best['arb_A']}, Issuer B cap/arb = {best['cap_B']}/{best['arb_B']} (shares of supply per day).",
             "", "Validation at 300 paths x 10,000 agents (z = (model - observed)/tolerance; all observed values VERIFY):", "",
             "| Episode | Target | Observed | Model | z |", "|---|---|---|---|---|"]
    for _, r_ in val.iterrows():
        lines.append(f"| {r_['episode']} | {r_['target']} | {r_['observed']} ± {r_['tolerance']} | {r_['model']} | {r_['z']} |")
    (out_dir / "tables" / "calibration.md").write_text("\n".join(lines), encoding="utf-8")
    return grid, val, cal
