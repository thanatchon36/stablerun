"""Per-path metrics and cross-path summaries."""
from __future__ import annotations

import numpy as np
import pandas as pd


def path_metrics(r: dict, cfg: dict) -> pd.DataFrame:
    m = cfg["metrics"]
    R, Y = r["R"], r["Y"]
    first10 = np.argmax(R >= 0.10, axis=1).astype(float)
    first10[~(R >= 0.10).any(axis=1)] = np.nan
    df = pd.DataFrame({
        "min_price": r["price"].min(axis=1),
        "R_day7": R[:, min(7, r["T"])],
        "R_day14": R[:, min(14, r["T"])],
        "R_end": R[:, -1],
        "day_R10": first10,
        "peak_Y_bp": Y.max(axis=1),
        "Y_day7_bp": Y[:, min(7, r["T"])],
        "Y_end_bp": Y[:, -1],
        "bills_sold": r["sold"].sum(axis=1),
        "matured": r["matured"].sum(axis=1),
        "withdrawn": r["withdrawn"].sum(axis=1),
        "net_demand_withdrawn": r["C"].max(axis=1),
        "other_sold": r["other_sold"].sum(axis=1),
        "peak_inv_over_K": r["inv"].max(axis=1) / r["capacity_K"],
        "peak_queue_days": r["queue"].max(axis=1) / r["cap"],
        "susp_days": r["suspended"].sum(axis=1),
        "fs_loss": r["fs_loss"][:, -1],
        "impairment_loss": r["impairment_loss"],
        "nav_end": r["nav"][:, -1],
    })
    df["run"] = df["R_end"] >= m["run_threshold"]
    df["severe_run"] = df["R_end"] >= m["severe_run_threshold"]
    for thr in m["yield_thresholds_bp"]:
        df[f"Y_gt_{thr}bp"] = df["peak_Y_bp"] > thr
    return df


def summarize(df: pd.DataFrame) -> pd.Series:
    out = {}
    for c in ["min_price", "R_day7", "R_end", "peak_Y_bp", "bills_sold", "matured", "withdrawn",
              "net_demand_withdrawn", "other_sold",
              "peak_inv_over_K", "peak_queue_days", "fs_loss", "nav_end"]:
        out[f"{c}_med"] = df[c].median()
        out[f"{c}_p5"] = df[c].quantile(0.05)
        out[f"{c}_p95"] = df[c].quantile(0.95)
    out["day_R10_med"] = df["day_R10"].median()
    out["susp_any"] = (df["susp_days"] > 0).mean()
    out["run_prob"] = df["run"].mean()
    out["severe_run_prob"] = df["severe_run"].mean()
    for c in [c for c in df.columns if c.startswith("Y_gt_")]:
        out[f"P_{c}"] = df[c].mean()
    return pd.Series(out)
