#!/usr/bin/env python3
"""Assemble the Hugging Face dataset (thanatchon36/stablerun) from results/tables.

Combines the per-path E1 Monte Carlo files into one table with issuer, scenario and path columns, stacks the
two E1 summaries, copies the other experiment tables and the parameter file, and adds the dataset card
(docs/hf_dataset_card.md). Writes to build/hf_dataset by default; upload with
    hf upload thanatchon36/stablerun build/hf_dataset . --repo-type dataset
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "results" / "tables"
SCENARIOS = ["control", "loss05", "loss10", "loss20", "scare08"]
COPY = ["E2_tipping_point", "E2_crossings", "E3_policy_grid", "E4_contagion", "E5_sensitivity",
        "benchmark_check", "calibration_grid", "calibration_validation"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / "hf_dataset"))
    out = Path(ap.parse_args().out)
    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)
    (out / "config").mkdir()

    paths, summaries = [], []
    for issuer in ["A", "B"]:
        for sc in SCENARIOS:
            df = pd.read_csv(T / f"E1_{issuer}_{sc}_paths.csv")
            df.insert(0, "path", range(len(df)))
            df.insert(0, "scenario", sc)
            df.insert(0, "issuer", issuer)
            paths.append(df)
        s = pd.read_csv(T / f"E1_{issuer}_summary.csv")
        s.insert(0, "issuer", issuer)
        summaries.append(s)
    e1 = pd.concat(paths, ignore_index=True)
    e1s = pd.concat(summaries, ignore_index=True)
    # the stacked paths must reproduce the published summaries exactly
    for (issuer, sc), g in e1.groupby(["issuer", "scenario"]):
        ref = e1s[(e1s.issuer == issuer) & (e1s.scenario == sc)].iloc[0]
        assert abs(g.peak_Y_bp.median() - ref.peak_Y_bp_med) < 1e-9, (issuer, sc)
        assert abs(g.R_end.median() - ref.R_end_med) < 1e-9, (issuer, sc)
    e1.to_csv(out / "data" / "e1_paths.csv", index=False)
    e1s.to_csv(out / "data" / "e1_summary.csv", index=False)
    for name in COPY:
        shutil.copy(T / f"{name}.csv", out / "data" / f"{name.lower()}.csv")
    shutil.copy(ROOT / "config" / "params_default.yaml", out / "config" / "params_default.yaml")
    shutil.copy(ROOT / "docs" / "hf_dataset_card.md", out / "README.md")
    print(f"{out}: {len(e1)} E1 paths, {len(COPY) + 2} tables")


if __name__ == "__main__":
    main()
