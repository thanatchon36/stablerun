"""Configuration loading, overrides and policy hooks.

Every run is fully described by (default YAML, overrides dict, policy dict, seed).
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "params_default.yaml"

# Maturity-cap policies map to a bill ladder: (tb1 ladder days, tb3 ladder days, share of bills in tb1).
# tb3 is the "beyond one month" bucket; a longer cap stretches it and thins the short bucket.
LADDER_BY_CAP = {93: (21, 42, 0.50), 180: (21, 84, 0.25), None: (21, 168, 0.15)}


def load_config(path: str | Path | None = None) -> dict:
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def deep_update(base: dict, updates: dict) -> dict:
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_update(base[k], v)
        else:
            base[k] = v
    return base


def with_overrides(cfg: dict, overrides: dict | None = None) -> dict:
    cfg = copy.deepcopy(cfg)
    if overrides:
        deep_update(cfg, overrides)
    return cfg


def apply_policy(cfg: dict, issuer: str, policy: dict | None) -> dict:
    """Return a copy of cfg with a policy applied to one issuer.

    policy keys (all optional):
      cash_buffer        minimum share of reserves held as cash, funded from bills (longest bucket first), then other
      redemption_fee     fee charged on redemptions (share)
      maturity_cap_days  93 | 180 | None  -> bill ladder from LADDER_BY_CAP
      fed_backstop       bool; from backstop.start_day the price-impact multiplier is scaled and the dealer
                         capacity penalty switched off (MMLF analogue)
    """
    cfg = copy.deepcopy(cfg)
    policy = policy or {}
    icfg = cfg["issuers"][issuer]
    res = icfg["reserves"]

    if "maturity_cap_days" in policy:
        d1, d3, share_tb1 = LADDER_BY_CAP[policy["maturity_cap_days"]]
        icfg["ladder_days"] = {"tb1": d1, "tb3": d3}
        bills = res["tbills_le_1m"] + res["tbills_1_3m"]
        res["tbills_le_1m"] = bills * share_tb1
        res["tbills_1_3m"] = bills * (1.0 - share_tb1)

    if "cash_buffer" in policy:
        need = max(float(policy["cash_buffer"]) - res["cash_deposits"], 0.0)
        for bucket in ("tbills_1_3m", "tbills_le_1m", "other"):
            take = min(res[bucket], need)
            res[bucket] -= take
            res["cash_deposits"] += take
            need -= take

    if "redemption_fee" in policy:
        icfg["redemption"]["fee"] = float(policy["redemption_fee"])

    if "processing_cap_share_per_day" in policy:
        icfg["redemption"]["processing_cap_share_per_day"] = float(policy["processing_cap_share_per_day"])

    cfg["_policy"] = {"fed_backstop": bool(policy.get("fed_backstop", False)),
                      "redeem_at_nav": bool(policy.get("redeem_at_nav", False))}
    return cfg
