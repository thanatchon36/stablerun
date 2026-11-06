"""Issuer reserves: impairment, bill ladder run-off and the liquidation waterfall (vectorised)."""
from __future__ import annotations

import numpy as np

KEYMAP = {"cash_deposits": "cash", "reverse_repo": "repo", "mmf_shares": "mmf",
          "tbills_le_1m": "tb1", "tbills_1_3m": "tb3", "other": "other"}
ASSETS = ["cash", "repo", "mmf", "tb1", "tb3", "other"]
LIQUID = ["cash", "repo", "mmf"]        # no price impact when used
BILLS = ["tb1", "tb3"]                  # sold shortest-first, with price impact
IMPAIR_ORDER = ["other", "cash", "mmf", "repo"]   # bills are never impaired


def initial_reserves(icfg: dict, s0: float, n_paths: int) -> dict:
    shares = icfg["reserves"]
    total = sum(shares.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"reserve shares sum to {total}, not 1")
    return {KEYMAP[k]: np.full(n_paths, float(v) * s0) for k, v in shares.items()}


def apply_impairment(res: dict, loss: np.ndarray) -> np.ndarray:
    """Remove `loss` (bn, per path) from the least liquid assets first. Returns the realised loss."""
    remaining = np.array(loss, dtype=float)
    realised = np.zeros_like(remaining)
    for a in IMPAIR_ORDER:
        take = np.minimum(res[a], remaining)
        res[a] -= take
        remaining -= take
        realised += take
    return realised


def runoff(res: dict, tb1_0: np.ndarray, tb3_0: np.ndarray, days_tb1: float, days_tb3: float) -> np.ndarray:
    """Uniform ladder: tb1 matures into cash, tb3 rolls into tb1. Returns cash from maturities."""
    mature = np.minimum(res["tb1"], tb1_0 / days_tb1)
    roll = np.minimum(res["tb3"], tb3_0 / days_tb3)
    res["tb1"] += roll - mature
    res["tb3"] -= roll
    res["cash"] += mature
    return mature


def waterfall(res: dict, need: np.ndarray, bill_discount: dict, other_haircut: float):
    """Raise `need` cash per path: cash -> repo -> MMF -> bills (tb1 then tb3, at a price
    concession) -> other (at a haircut). Returns (cash raised, face amounts used by asset, shortfall)."""
    need = np.asarray(need, dtype=float)
    raised = np.zeros_like(need)
    used = {}
    for a in LIQUID:
        take = np.clip(need - raised, 0.0, res[a])
        res[a] -= take
        raised += take
        used[a] = take
    for a in BILLS:
        disc = np.clip(bill_discount[a], 0.0, 0.99)
        remaining = np.maximum(need - raised, 0.0)
        face = np.minimum(res[a], remaining / (1.0 - disc))
        res[a] -= face
        raised += face * (1.0 - disc)
        used[a] = face
    remaining = np.maximum(need - raised, 0.0)
    face = np.minimum(res["other"], remaining / (1.0 - other_haircut))
    res["other"] -= face
    raised += face * (1.0 - other_haircut)
    used["other"] = face
    shortfall = np.maximum(need - raised, 0.0)
    return raised, used, shortfall


def mark_to_market(res: dict, bill_discount: dict) -> np.ndarray:
    """Asset value per path with bills marked at the current concession; other at book (post-impairment)."""
    v = res["cash"] + res["repo"] + res["mmf"] + res["other"]
    for a in BILLS:
        v = v + res[a] * (1.0 - np.clip(bill_discount[a], 0.0, 0.99))
    return v
