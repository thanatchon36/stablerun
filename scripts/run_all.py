#!/usr/bin/env python3
"""Reproduce everything.

  python scripts/run_all.py --experiment all          # E1 (A and B), E2, E3, E4, E5, benchmark, figures, tables (~25 min on 1 CPU)
  python scripts/run_all.py --experiment E1 --issuer B
  python scripts/run_all.py --experiment validate     # re-run the two calibration episodes: validation table and Figure F4
  python scripts/run_all.py --experiment calibrate    # re-fit and patch config/params_default.yaml in place
  (cd paper && latexmk -pdf main.tex)                 # build the paper
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stablerun.config import load_config, with_overrides  # noqa: E402

CHOICES = ["E1", "E2", "E3", "E4", "E5", "benchmark", "validate", "figures", "tables", "calibrate", "all"]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--experiment", default="E1", choices=CHOICES)
    p.add_argument("--paths", type=int, default=None)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--issuer", default="A")
    p.add_argument("--config", default=None)
    p.add_argument("--impact", default=None, choices=[None, "sqrt", "linear"])
    p.add_argument("--out", default=None)
    a = p.parse_args()
    cfg = load_config(a.config)
    if a.impact:
        cfg = with_overrides(cfg, {"bill_market": {"impact": {"functional_form": a.impact}}})
    out = Path(a.out) if a.out else ROOT / "results"
    steps = [a.experiment] if a.experiment != "all" else ["E1", "E2", "E3", "E4", "E5", "benchmark", "validate", "figures", "tables"]
    for step in steps:
        if step == "calibrate":
            from stablerun.calibrate import run_calibration
            run_calibration(cfg, out)
        elif step == "E1":
            from stablerun.experiments import run_e1
            for iss in ([a.issuer] if a.experiment == "E1" else ["A", "B"]):
                run_e1(cfg, n_paths=a.paths, seed=a.seed, issuer=iss, out_dir=out)
        elif step == "E2":
            from stablerun.experiments2 import run_e2
            run_e2(cfg, out, n_paths=a.paths or 300)
        elif step == "E3":
            from stablerun.experiments2 import run_e3, write_e3_markdown
            (out / "tables" / "E3_policy_grid.csv").unlink(missing_ok=True)
            for cname in ["loss10_5x_fast", "scare_1x_calibrated"]:
                for bs in [False, True]:
                    run_e3(cfg, out, n_paths=a.paths or 200, only=cname, backstops=[bs])
            write_e3_markdown(cfg, out)
        elif step == "E4":
            from stablerun.experiments2 import run_e4
            run_e4(cfg, out, n_paths=a.paths or 300)
        elif step == "E5":
            from stablerun.experiments2 import run_e5
            (out / "tables" / "E5_sensitivity.csv").unlink(missing_ok=True)
            run_e5(cfg, out, n_paths=a.paths or 200)
        elif step == "benchmark":
            from stablerun.experiments2 import run_benchmark
            run_benchmark(cfg, out)
        elif step == "validate":
            from stablerun.calibrate import run_validation
            run_validation(cfg, out, n_paths_final=a.paths or 300)
        elif step == "figures":
            import pandas as pd
            from stablerun.plots2 import figure_f2, figure_f3, figure_f5, figure_f6
            T, F = out / "tables", out / "figures"
            figure_f2(pd.read_csv(T / "E2_tipping_point.csv"), F / "F2_tipping_point")
            figure_f3(pd.read_csv(T / "E3_policy_grid.csv"), F / "F3_policy_heatmaps")
            figure_f5(pd.read_csv(T / "E5_sensitivity.csv"), F / "F5_sensitivity_tornado")
            figure_f6(pd.read_csv(T / "benchmark_check.csv"), F / "F6_benchmark_check", cfg=cfg)
        elif step == "tables":
            subprocess.run([sys.executable, str(ROOT / "scripts" / "make_tables.py")], check=True)
            for f in (out / "figures").glob("*.pdf"):
                (ROOT / "paper" / "figures").mkdir(parents=True, exist_ok=True)
                (ROOT / "paper" / "figures" / f.name).write_bytes(f.read_bytes())


if __name__ == "__main__":
    main()
